import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from urllib.parse import urljoin
from threading import Thread, Lock
from queue import Queue

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
firefox_options.add_argument("--headless") # ce je zakomentirana odpira firefox za vsako
firefox_options.add_argument("user-agent=fri-wier-Skupina_G")
firefox_options.binary_location = r'C:\Program Files\Mozilla Firefox\firefox.exe' # Spremeni glede na tvojo pot do firefox.exe

# Queue
urlsToVisit = Queue()
for url in WEB_PAGE_ADDRESSES:
    urlsToVisit.put(url)
visitedUrls = set()
visitedUrlsLock = Lock()


# Fetcha URL iz queue, dobi vsebina in najde linke na strani. Nato doda nove linke v queue
def fetchAndParseUrl(queue, options):
    global visited_urls_count
    while not queue.empty():
        currentUrl = queue.get()
        with visitedUrlsLock:
            if currentUrl in visitedUrls:
                continue
            visitedUrls.add(currentUrl)

            print(f"Visiting: {currentUrl}")
            service = FirefoxService(executable_path=WEB_DRIVER_LOCATION)
            driver = webdriver.Firefox(service=service, options=options)
            try:
                driver.get(currentUrl)
                time.sleep(TIMEOUT)
                pageLinks = driver.find_elements(By.TAG_NAME, "a")

                for link in pageLinks:
                    href = link.get_attribute("href")
                    if href and href.startswith("http"):
                        absoluteUrl = urljoin(currentUrl, href)
                        with visitedUrlsLock:
                            if absoluteUrl not in visitedUrls:
                                queue.put(absoluteUrl)
                        print("Link:" + link)
            except Exception as e:
                print(f"Error visiting {currentUrl}: {e}")
            finally:
                driver.close()
                driver.quit()


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
