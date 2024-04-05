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
from urllib.error import URLError
import psycopg2
import requests
import re
import hashlib
from urllib.parse import urlparse, urlunparse

# Initial setup
WEB_DRIVER_LOCATION = "geckodriver.exe"
# WEB_DRIVER_LOCATION = "./Programming_assignment_1/geckodriver.exe"
TIMEOUT = 5
NUM_OF_WORKERS = 10
WEB_PAGE_ADDRESSES = [
    "https://gov.si",
    "https://e-prostor.gov.si",
    "https://evem.gov.si",
    "https://e-uprava.gov.si",
]
DATABASE_NAME = 'test-restore'

# Firefox setup
firefox_options = FirefoxOptions()
# Uncomment the following line if you want to run headless
firefox_options.add_argument("--headless")
firefox_options.add_argument("user-agent=fri-wier-Skupina_G")
# Update the binary location based on your Firefox installation path
firefox_options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe'
firefox_options.accept_insecure_certs = True

# Queue
urlsToVisit = Queue()
for url in WEB_PAGE_ADDRESSES:
    urlsToVisit.put(url)
visitedUrls = set()
visitedUrlsLock = Lock()
visited_urls_count = 0

lock = threading.Lock()


def canonicalizeUrl(url):
    parsed_url = urlparse(url)
    canonicalized_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        '',  # query
        '',  # fragment
        ''
    ))
    return canonicalized_url

# Robots.txt
def isAllowedByRobots(url, userAgent="*"):
    parsedUrl = urlparse(url)
    robotsTxtUrl = f"{parsedUrl.scheme}://{parsedUrl.netloc}/robots.txt"

    try:
        rp = robotparser.RobotFileParser()
        rp.set_url(robotsTxtUrl)
        rp.read()
        return rp.can_fetch(userAgent, url)
    except URLError as e:  # Catch URLError for timeout
        print(f"Timeout error occurred while fetching robots.txt for {url}: {e}")
        return False
    except Exception as e:
        print(f"Error fetching robots.txt: {e}")
        return False

# Fetch for robots_content for site
def fetchAndStoreRobots(url):
    parsedUrl = urlparse(url)
    robotsTxtUrl = f"{parsedUrl.scheme}://{parsedUrl.netloc}/robots.txt"
    try:
        response = requests.get(robotsTxtUrl)
        if response.status_code == 200:
            robots_content = response.text
            updateSiteRecord(url, robots_content=robots_content)
    except Exception as e:
        print(f"Error fetching robots.txt for {url}: {e}")

# Fetch for sitemap_content for site
def fetchAndStoreSitemap(url):
    parsedUrl = urlparse(url)
    sitemapUrl = f"{parsedUrl.scheme}://{parsedUrl.netloc}/sitemap.xml"
    try:
        response = requests.get(sitemapUrl)
        if response.status_code == 200:
            sitemap_content = response.text
            updateSiteRecord(url, sitemap_content=sitemap_content)
    except Exception as e:
        print(f"Error fetching sitemap.xml for {url}: {e}")

# Update Site
def updateSiteRecord(url, **kwargs):
    domain = urlparse(url).netloc
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            set_clause = ", ".join([f"{column} = %s" for column in kwargs.keys()])
            values = list(kwargs.values())
            query = f"UPDATE crawldb.site SET {set_clause} WHERE domain = %s"
            values.append(domain)
            cur.execute(query, values)
            conn.commit()

# Get siteId
def getSiteId(url):
    domain = urlparse(url).netloc
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
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

# Get pageId
def getPageId(url):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM crawldb.page WHERE url = %s", (url,))
            row = cur.fetchone()
            if row:
                return row[0]
            else:
                print(f"URL {url} not found in the database.")
                return None
            
# Calculate pageHash
def calculate_page_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def is_duplicate(content_hash):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            query = "SELECT COUNT(*) FROM crawldb.page WHERE hash_page = %s"
            try:
                cur.execute(query, (content_hash,))
                count = cur.fetchone()[0]
                return count > 0
            except Exception as e:
                print(f"An error occurred: {e}")
                return False

# Insert page information
def insertPageInfo(url, html_content, http_status_code, accessed_time, site_id, hash_page):
    #try:
        with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO crawldb.page (site_id, url, html_content, http_status_code, accessed_time, page_type_code, in_use, hash_page) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (site_id, url, html_content, http_status_code, accessed_time, 'FRONTIER', False, hash_page))
                conn.commit()
    #except Exception as e:
    #    return


#
def insertImageInfo(src, page_id, filename, content_type, accessed_time):
    try:
        with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO crawldb.image (page_id, filename, content_type, data, accessed_time) VALUES (%s, %s, %s, %s, %s)", (page_id, filename, content_type, src, accessed_time))
                conn.commit()
    except Exception as e:
        return


def insertPageDataInfo(src, page_id, data_type_code):
    print("Inser page data", src, page_id, data_type_code)
    try:
        with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO crawldb.page_data (page_id, data_type_code, data) VALUES (%s, %s, %s)", (page_id, data_type_code, src))
                conn.commit()
    except Exception as e:
        return

def updatePageInfo(url, html_content, http_status_code, content_type, accessed_time, site_id, hash_page):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE crawldb.page SET html_content = %s, http_status_code = %s, accessed_time = %s, site_id = %s, page_type_code = %s, in_use = %s, hash_page = %s WHERE url = %s", (html_content, http_status_code, accessed_time, site_id, content_type, False, hash_page, url))
            conn.commit()


# Get first url in frontier
def getUrlFrontier():
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM crawldb.page WHERE page_type_code = %s AND in_use = %s ORDER BY accessed_time ASC FETCH FIRST ROW ONLY", ('FRONTIER', False))
                row = cur.fetchone()
                if row is not None:
                    cur.execute("UPDATE crawldb.page SET in_use = %s WHERE id = %s", (True, row[0]))
                conn.commit()
                return row

def errorCorrectionIsInUse(id):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:

                cur.execute("UPDATE crawldb.page SET in_use = %s WHERE id = %s", (False, id))
                conn.commit()


# For image url-s parse file name from url
def parse_filename_from_url(url):
    parsed_url = urlparse(url)
    path = parsed_url.path
    filename = path.split('/')[-1]
    return filename

# Fix db when urls in_use True but is not finnished
def fixIfError():
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM crawldb.page WHERE page_type_code = %s AND in_use = %s", ('FRONTIER', True))
                rows = cur.fetchall()


                if rows is not None:
                    for row in rows:
                        cur.execute("DELETE FROM crawldb.image WHERE page_id = %s", (row[0],))

                if rows is not None:
                    for row in rows:
                        cur.execute("UPDATE crawldb.page SET in_use = %s WHERE id = %s", (False, row[0]))
                conn.commit()

# Insert to link table
def updateLink(from_page, to_page, is_searched):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:
                try:
                    cur.execute("INSERT INTO crawldb.link (from_page, to_page, is_searched) VALUES (%s, %s, %s)", (from_page, to_page, is_searched))
                except psycopg2.IntegrityError:
                    conn.rollback() # Če že obstaja
                else:
                    conn.commit()

def updateLinkIsSearched(to_page, is_searched):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:
                try:
                    cur.execute('UPDATE crawldb.link SET is_searched = %s WHERE to_page = %s', (is_searched, to_page))
                except psycopg2.IntegrityError:
                    conn.rollback()
                else:
                    conn.commit()

htmlPages = 0
htmlPagesLock = Lock()

# Fetch and parse URL
def fetchAndParseUrl(queue, options):
    global visited_urls_count
    fail_retries = 0
    error_retry = 0
    global htmlPages

    while True: #not queue.empty():

        if htmlPages >= 50000:
            print(f"{threading.current_thread().name} konec!")
            break
        urlRow = getUrlFrontier()
        if urlRow is None:
            print("NO MORE AVAILABLE URLS", threading.current_thread().name)
            fail_retries += 1
            if fail_retries > 10:
                print("CLOSED THREAD!", threading.current_thread().name)
                break

            time.sleep(5)
            continue

        currentUrl = urlRow[3]
            
        if not isAllowedByRobots(currentUrl):
            print(f"URL {currentUrl} disallowed by robots.txt")
            updatePageInfo(currentUrl, None, 403, 'OTHER', datetime.now(), None, None)
            continue
        
        try:
            print(currentUrl, threading.current_thread().name)
            siteId = getSiteId(currentUrl)
            request = requests.get(currentUrl, stream=True)
            request.raise_for_status()

            # Check if the Content-Type is HTML (text/html)
            if request.headers['Content-Type'].split('/')[0] == "text":
                html_content = request.text
                pass
            else:
                pass

            print(request.headers['content-type'], threading.current_thread().name)

            if 'text/html' in request.headers.get('content-type', ''):
                page_hash = calculate_page_hash(html_content)

                if is_duplicate(page_hash):
                    print(f"Duplicate page detected for URL: {currentUrl}")
                    updatePageInfo(currentUrl, None, None, 'DUPLICATE', datetime.now(), None, page_hash)
                    continue

            fetchAndStoreRobots(currentUrl)
            fetchAndStoreSitemap(currentUrl)
            if 'text/html' in request.headers['content-type']:
                contentType = "HTML"
                with htmlPagesLock:
                    htmlPages += 1
            else:
                contentType = 'BINARY'
                print(request.headers['content-type'])
                updatePageInfo(currentUrl, None, request.status_code, contentType, datetime.now(), siteId, None)
                dataType = None

                if 'application/pdf' in request.headers['content-type']:
                    dataType = 'PDF'
                elif 'application/msword' in request.headers['content-type']:
                    dataType = 'DOC'
                elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in request.headers['content-type']:
                    dataType = 'DOCX'
                elif 'application/vnd.ms-powerpoint' in request.headers['content-type']:
                    dataType = 'PPT'
                elif 'application/vnd.openxmlformats-officedocument.presentationml.presentation' in request.headers['content-type']:
                    dataType = 'PPTX'
                elif 'image' in request.headers['content-type']:
                    filename = parse_filename_from_url(urlRow[3])
                    content_type = filename.split('.')[-1] if '.' in filename else None
                    if content_type is not None:
                        content_type = content_type.lower()
                    insertImageInfo(urlRow[3], urlRow[0], filename, content_type, datetime.now())
                    continue
                else:
                    dataType = 'OTHER'
                insertPageDataInfo(currentUrl, urlRow[0], dataType)
                continue

            if request.status_code != 200:
                updatePageInfo(currentUrl, None, request.status_code, contentType, datetime.now(), siteId, None)
                print(f"Request return invalid code", request.status_code)
                continue

            print(f"Visiting: {currentUrl}", threading.current_thread().name)
            service = FirefoxService(executable_path=WEB_DRIVER_LOCATION)

            driver = webdriver.Firefox(service=service, options=options)
            try:
                driver.get(currentUrl)
                time.sleep(TIMEOUT)
                pageLinks = driver.find_elements(By.TAG_NAME, "a")
                imgLinks = driver.find_elements(By.TAG_NAME, "img")

                for link in imgLinks:
                    src = link.get_attribute("src")
                    if src and src.startswith('http'):
                        try:
                            filename = parse_filename_from_url(src)
                            content_type = filename.split('.')[-1] if '.' in filename else None
                            if content_type is not None:
                                content_type = content_type.lower()
                            insertImageInfo(src, urlRow[0], filename, content_type, datetime.now())
                        except Exception as e:
                            print(f"Error inserting url ({src}): {e}", threading.current_thread().name)

                siteId = getSiteId(currentUrl)
                if siteId is None:
                    print(f"Site ID not found for URL: {currentUrl}")
                    driver.quit()
                    continue

                for link in pageLinks:
                    try:
                        href = link.get_attribute("href")
                        if href and href.startswith("http"):
                            href = canonicalizeUrl(href)
                        onClick = link.get_attribute("onclick")
                        if href and href.startswith("http"):
                            absoluteUrl = urljoin(currentUrl, href)
                            absoluteUrl = canonicalizeUrl(absoluteUrl)

                            try:
                                insertPageInfo(absoluteUrl, None, None,  datetime.now(), None, None)
                                toPageId = getPageId(absoluteUrl)
                                fromPageId = urlRow[0]
                                updateLink(fromPageId, toPageId, False)
                            except Exception as e:
                                continue
                                #print(f"Error inserting url ({absoluteUrl}): {e}", threading.current_thread().name)

                        if onClick:
                            matches = re.findall(r"(?:window\.location\s*=\s*|document\.location\s*=\s*)['\"](.*?)['\"]", onClick)
                            for match in matches:
                                absoluteUrl = urljoin(currentUrl, match)
                                absoluteUrl = canonicalizeUrl(absoluteUrl)
                                try:
                                    print("#INSERT(onclick): ", absoluteUrl, threading.current_thread().name)
                                    insertPageInfo(absoluteUrl, None, None, datetime.now(), None, None)
                                    toPageId = getPageId(absoluteUrl)
                                    fromPageId = urlRow[0]
                                    updateLink(fromPageId, toPageId, False)
                                except Exception as e:
                                    continue
                                    #print(f"Error inserting url ({absoluteUrl}): {e}", threading.current_thread().name)

                    except Exception as e:
                        print("StaleElementReferenceExceptionStaleElementReferenceExceptionStaleElementReferenceException")
                        continue

                accessedTime = datetime.now()
                htmlContent = driver.page_source
                updatePageInfo(currentUrl, htmlContent, request.status_code, contentType, accessedTime, siteId, page_hash)
                updateLinkIsSearched(urlRow[0], True)

                visited_urls_count += 1
            except Exception as e:
                accessedTime = datetime.now()
                updatePageInfo(currentUrl, None, 500, 'OTHER', accessedTime, None, None)
                print(f"Error visiting {currentUrl}: {e}")
            finally:
                driver.quit()

            error_retry = 0
        except requests.Timeout as e:
            print(f"Timeout occurred while fetching URL: {currentUrl}, Retrying...")
            fail_retries += 1
            if fail_retries > 10:
                print("Exceeded maximum retries. Closing thread.", threading.current_thread().name)
                break
            time.sleep(5)
            continue
        except Exception as e:
            print("Error while starting page analysis", e)
            error_retry += 1
            time.sleep(5)
            errorCorrectionIsInUse(urlRow[0])

            if error_retry > 5:
                print("Removed persistent error!", currentUrl)
                updatePageInfo(currentUrl, None, None, 'FRONTIER', datetime.now(), None, None)

    print(f"Total URLs visited: {visited_urls_count}")


def startCrawling(numOfWorkers):
    threads = []

    for i in range(numOfWorkers):
        time.sleep(5)
        thread = Thread(target=fetchAndParseUrl, args=(
            urlsToVisit, firefox_options))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()


def drop_rows_from_table(table_name):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM {}".format(table_name))
            conn.commit()

def getLinksFromPage(id):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM crawldb.link WHERE from_page = %s", (id,))
                links = cur.fetchall()
                return links

def getLinksToPage(id):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM crawldb.link WHERE to_page = %s", (id,))
                result = cur.fetchone()
                return result

def insertFixLink(from_page, to_page):
    with psycopg2.connect(database=DATABASE_NAME, user="postgres", password="postgres", host="localhost", port="5432") as conn:
        with lock:
            with conn.cursor() as cur:

                cur.execute("INSERT INTO crawldb.link (from_page, to_page, is_searched) VALUES (%s, %s, %s)", (from_page, to_page, True))
                conn.commit()



def fixLinks(queue, options, full_size):
    while not queue.empty():
        row = queue.get()

        links = getLinksFromPage(row[0])

        if len(links) == 0:
            currentUrl = row[2]
            print(f"Visiting: {currentUrl}", threading.current_thread().name, "left:", (1 - (queue.qsize() / full_size)) * 100, "%", queue.qsize())

            service = FirefoxService(executable_path=WEB_DRIVER_LOCATION)

            driver = webdriver.Firefox(service=service, options=options)
            try:
                driver.get(currentUrl)
                time.sleep(TIMEOUT)
                pageLinks = driver.find_elements(By.TAG_NAME, "a")
                for link in pageLinks:
                    try:
                        href = link.get_attribute("href")
                        if href and href.startswith("http"):
                            href = canonicalizeUrl(href)
                        onClick = link.get_attribute("onclick")
                        if href and href.startswith("http"):
                            absoluteUrl = urljoin(currentUrl, href)
                            absoluteUrl = canonicalizeUrl(absoluteUrl)

                            try:
                                toPageId = getPageId(absoluteUrl)
                                fromPageId = row[0]
                                result = getLinksToPage(toPageId)
                                if result:
                                    continue
                                else:
                                    if toPageId is not None:

                                        print("Insert IDDD:",fromPageId,toPageId, "already exists: ", False, "For page:", currentUrl )
                                        insertFixLink(fromPageId, toPageId)
                            except Exception as e:
                                continue
                    except Exception as e:
                        print("StaleElementReferenceExceptionStaleElementReferenceExceptionStaleElementReferenceException")
                        continue
            except Exception as e:
                print(f"Error ({queue.qsize()}) visiting  {currentUrl}: {e}")
                queue.put(row)
                print(f"size: {queue.qsize()}")
            finally:
                print("Quit", threading.current_thread().name)
                driver.quit()



def dropTablesStart():
    drop_rows_from_table("crawldb.link")
    drop_rows_from_table("crawldb.image")
    drop_rows_from_table("crawldb.page_data")
    drop_rows_from_table("crawldb.page")
    drop_rows_from_table("crawldb.site")


def insert():
    insertPageInfo(WEB_PAGE_ADDRESSES[0], None, None, datetime.now(), None, None)
    insertPageInfo(WEB_PAGE_ADDRESSES[1], None, None, datetime.now(), None, None)
    insertPageInfo(WEB_PAGE_ADDRESSES[2], None, None, datetime.now(), None, None)
    insertPageInfo(WEB_PAGE_ADDRESSES[3], None, None, datetime.now(), None, None)


#dropTablesStart()
#insert()

# If error while working set not finished urls: in_use to false.
fixIfError()

startCrawling(NUM_OF_WORKERS)