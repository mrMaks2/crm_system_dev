import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
from random import randint

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('parse')

# PROXY = "178.20.46.224:3128"

headers = [
    {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:47.0) Gecko/20100101 Firefox/47.0',
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:53.0) Gecko/20100101 Firefox/53.0',
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
    ]

def parse_from_ozon(art):
    options = Options()
    # options.add_argument(f'--proxy-server={PROXY}')
    # options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={headers[randint(0,2)]}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(f'https://www.ozon.ru/product/{str(art)}')
    driver.implicitly_wait(20)
    
    try:
        WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        price_element = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, "//span[contains(@class, 'y8k_27') and contains(@class, 'ky7_27')]"))
        )

        price_with_discount_ozon = int(price_element.text.strip().replace('&thinsp;', '').replace('₽', '').replace(' ', '').replace(' ', '').replace('&nbsp;', '').replace('\u00A0', ''))
        time.sleep(2)
        return price_with_discount_ozon
    except:
        logger.info("Элемент с классами 'y8k_27' и 'ky7_27' из Ozon не найден")
    finally:
        driver.quit()


def parse_from_wb(art):
    options = Options()
    # options.add_argument(f'--proxy-server={PROXY}')
    # options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={headers[randint(0,2)]}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(f'https://www.wildberries.ru/catalog/{str(art)}/detail.aspx?targetUrl=BP')
    driver.implicitly_wait(20)
    
    try:
        WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        price_element = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, "//span[contains(@class, 'price-block__wallet-price') and contains(@class, 'red-price')]"))
        )
        price_with_discount_wb = int(price_element.text.strip().replace('&nbsp;', '').replace('₽', '').replace(' ', ''))
        time.sleep(2)
        return price_with_discount_wb
    except:
        logger.info("Элемент с классами 'price-block__wallet-price' и 'red-price' из WB не найден")
        try:
            price_element = WebDriverWait(driver, 20).until(
                EC.visibility_of_element_located((By.XPATH, "//span[contains(@class, 'price-block__wallet-price')]"))
            )
            price_with_discount_wb = int(price_element.text.strip().replace('&nbsp;', '').replace('₽', '').replace(' ', ''))
            time.sleep(2)
            return price_with_discount_wb
        except:
            logger.info("Элемент с классом 'price-block__wallet-price' из WB не найден")
    finally:
        driver.quit()




















# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options
# from .models import Product_from_wb
# import time


# def parse_from_ozon(args):
#     options = Options()
#     # options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--disable-webrtc")
#     options.add_argument("--hide-scrollbars")
#     options.add_argument("--disable-notifications")
#     options.add_argument("--start-maximized")
#     options.add_argument("--disable-blink-features=AutomationControlled")
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36")
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option('useAutomationExtension', False)

#     driver = webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=options)
#     driver.get(f'https://www.ozon.ru/product/{str(args)}')
#     WebDriverWait(driver, 60).until(lambda d: d.execute_script('return document.readyState') == 'complete')
#     # WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.XPATH, "//span[contains(@class, 'k2z_27') and contains(@class, 'zk0_27')]")))

#     driver.implicitly_wait(60)
    
#     try:
#         # price_element = WebDriverWait(driver, 60).until(
#         #     EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'k2z_27') and contains(@class, 'zk0_27')]"))
#         # )
#         price_element = driver.execute_script("""
#             return document.querySelector('span.k2z_27.zk0_27');
#         """)
#         price_with_discount_ozon = price_element.text.strip().replace('&thinsp;', '').replace(' ', '').replace('₽', '').replace(' ', '').replace('\u00A0', '')
#         time.sleep(5)
#         return price_with_discount_ozon
#     finally:
#         driver.quit()

# def parse_and_save_from_wb(args):
#     options = Options()
#     # options.add_argument("--headless")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--disable-webrtc")
#     options.add_argument("--hide-scrollbars")
#     options.add_argument("--disable-notifications")
#     options.add_argument("--start-maximized")
#     options.add_argument("--disable-blink-features=AutomationControlled")
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36")
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option('useAutomationExtension', False)

#     driver = webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=options)
#     driver.get(f'https://www.wildberries.ru/catalog/{str(args)}/detail.aspx?targetUrl=BP')
#     WebDriverWait(driver, 60).until(lambda d: d.execute_script('return document.readyState') == 'complete')
#     # WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.XPATH, "//span[contains(@class, 'price-block__wallet-price') and contains(@class, 'red-price')]")))
#     driver.implicitly_wait(60)
    
#     try:
#         # price_element = WebDriverWait(driver, 60).until(
#         #     EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'price-block__wallet-price') and contains(@class, 'red-price')]"))
#         # )
#         price_element = driver.execute_script("""
#             return document.querySelector('span.price-block__wallet-price.red-price');
#         """)
#         price_with_discount_wb = int(price_element.text.strip().replace('&nbsp;', '').replace('₽', '').replace(' ', '').replace('\u00A0', ''))

#         product, created = Product_from_wb.objects.get_or_create(
#                 prod_art_from_wb=args,
#                 defaults={'price_with_discount_wb': price_with_discount_wb}
#             )
        
#         if not created:
#             product.price_with_discount_wb = price_with_discount_wb
#             product.save()
#             print(f"Обновлен товар: {args}")
#         else:
#             print(f"Создан новый товар: {args}")
#     finally:
#         driver.quit()

#     time.sleep(5)