from bs4 import BeautifulSoup
import requests
from random import randint
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent

useragent = UserAgent()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('wb')

proxies = ['46.47.197.210:3128', '79.174.12.190:80', '62.84.120.61:80']

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument('--proxy-server=http://%s' % proxies[randint(0,2)])
chrome_options.add_argument(f"user-agent={useragent.random}")


def main():

    url = f'https://www.wildberries.ru/catalog/236212732/detail.aspx'

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url, verify=False)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, 'lxml')
    logger.debug(soup)

    price = int(soup.find('span', class_ = 'price-block__wallet-price red-price').text.strip().replace('&nbsp;', '').replace('₽', ''))
    logger.debug(price)

    driver.quit()

if __name__ == "__main__":
    main()