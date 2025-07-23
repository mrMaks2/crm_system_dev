import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('wb')

def main():

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get('https://www.wildberries.ru/catalog/236212732/detail.aspx?targetUrl=BP')
    driver.implicitly_wait(20)
    
    try:
        price_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'price-block__wallet-price') and contains(@class, 'red-price')]"))
        )

        logger.debug(price_element.text.strip().replace('&nbsp;', '').replace('₽', '').replace(' ', ''))
    except:
        logger.debug("Элемент с классами 'price-block__wallet-price' и 'red-price' не найден")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()