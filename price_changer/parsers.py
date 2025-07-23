from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from .models import Product_from_wb
import time
import os

def parse_from_ozon(args):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-webrtc")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    SELENIUM_REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL", "http://selenium:4444/wd/hub")

    driver = webdriver.Remote(command_executor=SELENIUM_REMOTE_URL, options=options)
    driver.get(f'https://www.ozon.ru/product/{str(args)}')
    driver.implicitly_wait(20)
    
    try:
        price_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'k2z_27') and contains(@class, 'zk0_27')]"))
        )
        price_with_discount_ozon = price_element.text.strip().replace('&thinsp;', '').replace('₽', '').replace(' ', '')
        time.sleep(5)
        return price_with_discount_ozon
    finally:
        driver.quit()

def parse_and_save_from_wb(args):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-webrtc")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")

    SELENIUM_REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL", "http://selenium:4444/wd/hub")

    driver = webdriver.Remote(command_executor=SELENIUM_REMOTE_URL, options=options)
    driver.get(f'https://www.wildberries.ru/catalog/{str(args)}/detail.aspx?targetUrl=BP')
    driver.implicitly_wait(20)
    
    try:
        price_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'price-block__wallet-price') and contains(@class, 'red-price')]"))
        )
        price_with_discount_wb = int(price_element.text.strip().replace('&nbsp;', '').replace('₽', '').replace(' ', ''))

        product, created = Product_from_wb.objects.get_or_create(
                prod_art_from_wb=args,
                defaults={'price_with_discount_wb': price_with_discount_wb}
            )
        
        if not created:
            product.price_with_discount_wb = price_with_discount_wb
            product.save()
            print(f"Обновлен товар: {args}")
        else:
            print(f"Создан новый товар: {args}")
    finally:
        driver.quit()

    time.sleep(5)