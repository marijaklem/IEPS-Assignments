import threading
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from urllib.parse import urljoin, urlparse
from threading import Thread, Lock
from queue import Queue
from urllib import robotparser
import psycopg2
import requests

# Initial setup
WEB_DRIVER_LOCATION = "geckodriver.exe"
TIMEOUT = 5
NUM_OF_WORKERS = 1
WEB_PAGE_ADDRESSES = [
    "https://gov.si",
    "https://evem.gov.si",
    "https://e-uprava.gov.si",
    "https://e-prostor.gov.si",
    "http://kds.si/"
]

# Firefox setup
firefox_options = FirefoxOptions()
# Uncomment the following line if you want to run headless
firefox_options.add_argument("--headless")
firefox_options.add_argument("user-agent=fri-wier-Skupina_G")
# Update the binary location based on your Firefox installation path
firefox_options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'

# Queue
urlsToVisit = Queue()
for url in WEB_PAGE_ADDRESSES:
    urlsToVisit.put(url)
visitedUrls = set()
visitedUrlsLock = Lock()
visited_urls_count = 0

lock = threading.Lock()


# Robots.txt
def isAllowedByRobots(url, userAgent="*"):
    parsedUrl = urlparse(url)
    robotsTxtUrl = f"{parsedUrl.scheme}://{parsedUrl.netloc}/robots.txt"

    try:
        rp = robotparser.RobotFileParser()
        rp.set_url(robotsTxtUrl)
        rp.read()
        return rp.can_fetch(userAgent, url)
    except Exception as e:
        print(f"Error fetching robots.txt: {e}")
        return False

# Get siteId
def getSiteId(url):
    domain = urlparse(url).netloc
    with psycopg2.connect(database="postgres", user="postgres", password="SMRPO_skG", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM crawldb.site WHERE domain = %s", (domain,))
            row = cur.fetchone()
            if row:
                return row[0]
            else:
                # Insert the site into the database
                cur.execute("INSERT INTO crawldb.site (domain) VALUES (%s) RETURNING id", (domain,))
                conn.commit()
                new_site_id = cur.fetchone()[0]
                return new_site_id


# Insert page information
def insertPageInfo(url, html_content, http_status_code, accessed_time, site_id):
    with psycopg2.connect(database="postgres", user="postgres", password="SMRPO_skG", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO crawldb.page (site_id, url, html_content, http_status_code, accessed_time, page_type_code, in_use) VALUES (%s, %s, %s, %s, %s, %s, %s)", (site_id, url, html_content, http_status_code, accessed_time, 'FRONTIER', False))
            conn.commit()


def updatePageInfo(url, html_content, http_status_code, content_type, accessed_time, site_id):
    with psycopg2.connect(database="postgres", user="postgres", password="SMRPO_skG", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE crawldb.page SET html_content = %s, http_status_code = %s, accessed_time = %s, site_id = %s, page_type_code = %s, in_use = %s WHERE url = %s", (html_content, http_status_code, accessed_time, site_id, content_type, False, url))
            conn.commit()


# Get first url in frontier
def getUrlFrontier():
    with psycopg2.connect(database="postgres", user="postgres", password="SMRPO_skG", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM crawldb.page WHERE page_type_code = %s AND in_use = %s ORDER BY accessed_time ASC FETCH FIRST ROW ONLY", ('FRONTIER', False))
                row = cur.fetchone()
                if row is not None:
                    cur.execute("UPDATE crawldb.page SET in_use = %s WHERE id = %s", (True, row[0]))
                conn.commit()
                return row

# Fix db when urls in_use True but is not finnished
def fixIfError():
    with psycopg2.connect(database="postgres", user="postgres", password="SMRPO_skG", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM crawldb.page WHERE page_type_code = %s AND in_use = %s FETCH FIRST ROW ONLY", ('FRONTIER', True))
                rows = cur.fetchall()

                if rows is not None:
                    for row in rows:
                        cur.execute("UPDATE crawldb.page SET in_use = %s WHERE id = %s", (False, row[0]))
                conn.commit()

# Fetch and parse URL
def fetchAndParseUrl(queue, options):
    global visited_urls_count
    fail_retries = 0

    while True: #not queue.empty():
        urlRow = getUrlFrontier()
        if urlRow is None:
            print("NO MORE AVAILABLE URLS", threading.current_thread().name)
            fail_retries += 1
            if fail_retries > 5:
                print("CLOSED THREAD!", threading.current_thread().name)
                break

            time.sleep(5)
            continue

        currentUrl = urlRow[3]
        #with visitedUrlsLock:
        #    if currentUrl in visitedUrls:
        #        continue
        #    visitedUrls.add(currentUrl)
            
        if not isAllowedByRobots(currentUrl):
            print(f"URL {currentUrl} disallowed by robots.txt")
            continue

        request = requests.get(currentUrl)
        print(request.status_code)
        print(request.headers)
        print(request.headers['content-type'])

        contentType = None
        if 'text/html' in request.headers['content-type'] :
            print("HTML")
            contentType = "HTML"

        if request.status_code != 200:
            siteId = getSiteId(currentUrl)
            updatePageInfo(currentUrl, None, request.status_code, contentType, datetime.now(), siteId)
            print(f"Request return invalid code", request.status_code)
            continue

        print(f"Visiting: {currentUrl}", threading.current_thread().name)
        service = FirefoxService(executable_path=WEB_DRIVER_LOCATION)

        driver = webdriver.Firefox(service=service, options=options)
        try:
            driver.get(currentUrl)
            time.sleep(TIMEOUT)
            pageLinks = driver.find_elements(By.TAG_NAME, "a")

            siteId = getSiteId(currentUrl)
            if siteId is None:
                print(f"Site ID not found for URL: {currentUrl}")
                driver.quit()
                continue

            for link in pageLinks:
                href = link.get_attribute("href")
                if href and href.startswith("http"):
                    absoluteUrl = urljoin(currentUrl, href)
                    #with visitedUrlsLock:
                    #    if absoluteUrl not in visitedUrls:
                            #queue.put(absoluteUrl)
                    try:
                        #print("#INSERT", threading.current_thread().name)
                        insertPageInfo(absoluteUrl, None, None,  datetime.now(), None)
                    except Exception as e:
                        print(f"Error inserting url ({absoluteUrl}): {e}", threading.current_thread().name)

                            #print("Link:", href)

            accessedTime = datetime.now()
            htmlContent = driver.page_source
            print(driver.execute_script(""))
            print("#UPDATE", threading.current_thread().name)
            updatePageInfo(currentUrl, htmlContent, request.status_code, contentType,accessedTime, siteId)

            visited_urls_count += 1
        except Exception as e:
            accessedTime = datetime.now()
            updatePageInfo(currentUrl, None, 500, contentType, accessedTime, None)
            print(f"Error visiting {currentUrl}: {e}")
        finally:
            driver.quit()
    print(f"Total URLs visited: {visited_urls_count}")


def startCrawling(numOfWorkers):
    threads = []

    for i in range(numOfWorkers):
        thread = Thread(target=fetchAndParseUrl, args=(
            urlsToVisit, firefox_options))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()


def drop_rows_from_table(table_name):
    with psycopg2.connect(database="postgres", user="postgres", password="SMRPO_skG", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM {}".format(table_name))
            conn.commit()


drop_rows_from_table("crawldb.page")
drop_rows_from_table("crawldb.site")

def insert():
    insertPageInfo(WEB_PAGE_ADDRESSES[0], None, None, datetime.now(), None)
    insertPageInfo(WEB_PAGE_ADDRESSES[1], None, None, datetime.now(), None)
    insertPageInfo(WEB_PAGE_ADDRESSES[2], None, None, datetime.now(), None)
    insertPageInfo(WEB_PAGE_ADDRESSES[3], None, None, datetime.now(), None)
    insertPageInfo(WEB_PAGE_ADDRESSES[4], None, None, datetime.now(), None)


insert()

# If error while working set not finished urls: in_use to false.
#fixIfError()

startCrawling(NUM_OF_WORKERS)
