import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('ozon')

def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get('https://www.ozon.ru/product/1843974253')
    driver.implicitly_wait(20)
    
    try:
        price_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'k2z_27') and contains(@class, 'zk0_27')]"))
        )

        logger.debug(price_element.text.strip().replace('&thinsp;', '').replace('₽', '').replace(' ', '').replace('&nbsp;', ''))
    except:
        logger.debug("Элемент с классами 'z3k_27' и 'kz2_27' не найден")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()