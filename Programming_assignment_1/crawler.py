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

# Initial setup
WEB_DRIVER_LOCATION = "./Programming_assignment_1/geckodriver.exe"
TIMEOUT = 5
NUM_OF_WORKERS = 5
WEB_PAGE_ADDRESSES = [
    "https://gov.si",
    "https://evem.gov.si",
    "https://e-uprava.gov.si",
    "https://e-prostor.gov.si"
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
        return True
    

# Get siteId
def getSiteId(url):
    domain = urlparse(url).netloc
    print(domain)
    with psycopg2.connect(database="postgres", user="postgres", password="SMRPO_skG", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM crawldb.site WHERE domain = %s", (domain,))
            row = cur.fetchone()
            if row:
                return row[0]
            else:
                return None


# Insert page information
def insert_page_info(url, htmlContent, httpStatusCode, accessedTime, siteId):
    with psycopg2.connect(database="postgres", user="postgres", password="SMRPO_skG", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO crawldb.page (site_id, url, html_content, http_status_code, accessed_time) VALUES (%s, %s, %s, %s, %s)", (siteId, url, htmlContent, httpStatusCode, accessedTime))
            conn.commit()


# Fetch and parse URL
def fetchAndParseUrl(queue, options):
    global visited_urls_count
    while not queue.empty():
        currentUrl = queue.get()
        with visitedUrlsLock:
            if currentUrl in visitedUrls:
                continue
            visitedUrls.add(currentUrl)
            
            if not isAllowedByRobots(currentUrl):
                print(f"URL {currentUrl} disallowed by robots.txt")
                continue

            print(f"Visiting: {currentUrl}")
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
                        with visitedUrlsLock:
                            if absoluteUrl not in visitedUrls:
                                queue.put(absoluteUrl)
                        print("Link:" + href)
                
                httpStatusCode = driver.execute_script("return document.readyState === 'complete' ? 200 : 400;")
                accessedTime = datetime.now()
                htmlContent = driver.page_source
                insert_page_info(currentUrl, htmlContent, httpStatusCode, accessedTime, siteId)

                visited_urls_count += 1
            except Exception as e:
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


startCrawling(NUM_OF_WORKERS)
