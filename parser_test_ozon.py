from bs4 import BeautifulSoup
# import requests
import logging
import time
import undetected_chromedriver as uc
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.support.ui import WebDriverWait

def main():
    driver = uc.Chrome()
    driver.implicitly_wait(5)

    driver.get('https://www.ozon.ru/product/1843974253')
    time.sleep(2)
    resp = str(driver.page_source)
    soup = BeautifulSoup(resp, 'lxml')
    price = soup.find('span', attrs={'class': 'z3k_27 kz2_27'})
    logging.debug(price)
    # driver.close()
    # driver.switch_to.window(driver.window_handles[0])
    driver.quit()

if __name__ == "__main__":
    main()