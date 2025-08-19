import logging
from DrissionPage import ChromiumPage, ChromiumOptions
from random import randint
import re
import time
import tempfile
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('price_changer.tasks')

headers = [
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
     'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
     'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
     'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
]

def get_chromium_options():
    """Создает и настраивает опции Chromium"""
    co = ChromiumOptions()
    
    # Базовые настройки
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-web-security')
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--headless=new')
    co.set_argument('--disable-extensions')
    co.set_argument('--disable-software-rasterizer')
    co.set_argument('--disable-setuid-sandbox')
    co.set_argument('--window-size=1920,1080')
    co.set_argument('--disable-features=VizDisplayCompositor')
    co.set_argument('--disable-background-timer-throttling')
    co.set_argument('--disable-backgrounding-occluded-windows')
    co.set_argument('--disable-renderer-backgrounding')
    co.set_argument('--disable-back-forward-cache')
    co.set_argument('--disable-ipc-flooding-protection')
    co.set_argument('--disable-hang-monitor')
    co.set_argument('--disable-client-side-phishing-detection')
    co.set_argument('--disable-sync')
    co.set_argument('--metrics-recording-only')
    co.set_argument('--no-first-run')
    co.set_argument('--safebrowsing-disable-auto-update')
    co.set_argument('--disable-default-apps')
    co.set_argument('--disable-prompt-on-repost')
    co.set_argument('--disable-domain-reliability')
    co.set_argument('--password-store=basic')
    co.set_argument('--use-mock-keychain')
    co.set_argument('--disable-component-update')
    
    # Настройки для обхода детекции
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--exclude-switches=enable-automation')
    co.set_argument('--disable-features=UserAgentClientHint')
    
    # Отключаем автоматический порт и используем фиксированный user data dir
    co.set_argument('--remote-debugging-port=0')
    co.set_argument('--disable-default-apps')
    
    # Создаем временную директорию для user data
    temp_dir = tempfile.mkdtemp(prefix='drissionpage_')
    co.set_argument(f'--user-data-dir={temp_dir}')
    
    # Отключаем изображения для ускорения
    co.no_imgs()
    co.incognito()
    
    return co, temp_dir

def parse_from_ozon(art):
    co, temp_dir = get_chromium_options()
    page = None
    
    try:
        # Устанавливаем User-Agent перед созданием страницы
        user_agent = headers[randint(0, 2)]['User-Agent']
        co.set_argument(f'--user-agent={user_agent}')
        
        page = ChromiumPage(addr_or_opts=co)
        
        # Дополнительная настройка User-Agent
        page.set.user_agent(user_agent)
        
        logger.debug(f"Переходим на страницу товара Ozon {art}")
        page.get(f'https://www.ozon.ru/product/{str(art)}')
        page.wait.load_start()
        time.sleep(3)
        
        # Ждем загрузки контента
        page.wait.ele_displayed('tag:body', timeout=20)
        time.sleep(2)
        
        # Поиск цены с несколькими селекторами
        price_selectors = [
            "@class=tsHeadline600Large",
            "xpath://div[contains(@class, 'pdp_be5') and contains(@class, 'pdp_b4e')]",
            'xpath://span[contains(@class, "tsHeadline600Large")]',
        ]
        
        price_element = None
        for selector in price_selectors:
            try:
                price_element = page.ele(selector, timeout=5)
                if price_element and price_element.text.strip():
                    break
            except:
                continue
        
        if price_element:
            price_text = price_element.text.strip()
            logger.debug(f"Найден текст цены: {price_text}")
            price_with_discount_ozon = int(re.sub(r'\D', '', price_text))
            logger.debug(f"Цена товара: {price_with_discount_ozon}")
            return int(price_with_discount_ozon)
        else:
            logger.debug("Элемент с ценой не найден, сохраняем скриншот")
            try:
                page.get_screenshot(path=f'ozon_error_{art}.png', full_page=True)
            except:
                pass
            return None
            
    except Exception as e:
        logger.error(f"Произошла ошибка при парсинге Ozon: {str(e)}")
        return None
    finally:
        if page:
            try:
                page.quit()
            except:
                pass
        # Очищаем временную директорию
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def parse_from_wb(art):
    co, temp_dir = get_chromium_options()
    page = None
    
    try:
        user_agent = headers[randint(0, 2)]['User-Agent']
        co.set_argument(f'--user-agent={user_agent}')
        
        page = ChromiumPage(addr_or_opts=co)
        page.set.user_agent(user_agent)
        
        logger.debug(f"Переходим на страницу WB товара {art}")
        page.get(f'https://www.wildberries.ru/catalog/{str(art)}/detail.aspx')
        page.wait.load_start()
        time.sleep(3)
        
        page.wait.ele_displayed('tag:body', timeout=20)
        time.sleep(2)
        
        # Поиск цены на WB
        price_selectors = [
            'xpath://span[contains(@class, "price-block__wallet-price") and contains(@class, "red-price")]',
            'xpath://span[contains(@class, "price-block__wallet-price")]',
            '@class=price-block__wallet-price red-price',
            '@class=price-block__wallet-price',
        ]
        
        price_element = None
        for selector in price_selectors:
            try:
                price_element = page.ele(selector, timeout=5)
                if price_element and price_element.text.strip():
                    break
            except:
                continue
        
        if price_element:
            price_text = price_element.text.strip()
            logger.debug(f"Найден текст цены WB: {price_text}")
            price_with_discount_wb = int(re.sub(r'\D', '', price_text))
            logger.debug(f"Цена товара WB: {price_with_discount_wb}")
            return int(price_with_discount_wb)
        else:
            logger.debug("Элемент с ценой WB не найден, сохраняем скриншот")
            try:
                page.get_screenshot(path=f'wb_error_{art}.png', full_page=True)
            except:
                pass
            return None
            
    except Exception as e:
        logger.error(f"Произошла ошибка при парсинге WB: {str(e)}")
        return None
    finally:
        if page:
            try:
                page.quit()
            except:
                pass
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass








# import logging
# from DrissionPage import ChromiumPage, ChromiumOptions
# from random import randint
# import re
# import time

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger('ozon')

# headers = [
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:47.0) Gecko/20100101 Firefox/47.0',
#         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
#         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:53.0) Gecko/20100101 Firefox/53.0',
#         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
#     ]

# def parse_from_ozon(art):

#     co = ChromiumOptions()
#     co.auto_port()
#     co.no_imgs()
#     co.incognito()
#     co.set_argument('--disable-web-security')
#     co.set_argument('--no-sandbox')
#     co.set_argument('--headless=new')
#     co.set_argument("--disable-blink-features=AutomationControlled")
#     co.set_argument("--disable-gpu")
#     co.set_paths(browser_path=None, local_port=None)
#     co.set_argument("--remote-debugging-port=0")

#     page = ChromiumPage(addr_or_opts=co)
#     user_agent = headers[randint(0, 2)]['User-Agent']
#     page.set.user_agent(user_agent)
    
#     try:
#         page.get(f'https://www.ozon.ru/product/{str(art)}')
#         page.wait.load_start()
#         time.sleep(5)
#         price_element = page.ele('@class=tsHeadline600Large', timeout=20)
        
#         if price_element:
#             price_text = price_element.text.strip()
#             price_with_discount_ozon = int(re.sub(r'\D', '', price_text))
#             logger.debug(f"Цена товара: {price_with_discount_ozon}")
#             return int(price_with_discount_ozon)
#         else:
#             logger.debug("Элемент с ценой не найден")      
#     except Exception as e:
#         logger.error(f"Произошла ошибка: {str(e)}")
#     finally:
#         page.quit()


# def parse_from_wb(art):

#     co = ChromiumOptions()
#     co.auto_port()
#     co.no_imgs()
#     co.incognito()
#     co.set_argument('--disable-web-security')
#     co.set_argument('--no-sandbox')
#     co.set_argument('--headless=new')
#     co.set_argument("--disable-blink-features=AutomationControlled")
#     co.set_argument("--disable-gpu")
#     co.set_paths(browser_path=None, local_port=None)
#     co.set_argument("--remote-debugging-port=0")

#     page = ChromiumPage(addr_or_opts=co)
#     user_agent = headers[randint(0, 2)]['User-Agent']
#     page.set.user_agent(user_agent)
    
#     try:
#         page.get(f'https://www.wildberries.ru/catalog/{str(art)}/detail.aspx?targetUrl=BP')
#         page.wait.load_start()
#         time.sleep(5)
#         price_element_1 = page.ele('@class=price-block__wallet-price red-price', timeout=20)
#         if price_element_1:
#             price_text = price_element_1.text.strip()
#             price_with_discount_wb = int(re.sub(r'\D', '', price_text))
#             logger.debug(f"Цена товара: {price_with_discount_wb}")
#             return int(price_with_discount_wb)
#         else:
#             logger.debug("Элемент с блоком price-block__wallet-price red-price не найден")
#             price_element_2 = page.ele('@class=price-block__wallet-price', timeout=20)
#             if price_element_2:
#                 price_text = price_element_2.text.strip()
#                 price_with_discount_wb = int(re.sub(r'\D', '', price_text))
#                 logger.debug(f"Цена товара: {price_with_discount_wb}")
#                 return int(price_with_discount_wb)
#             else:
#                 logger.debug("Элемент с блоком price-block__wallet-price не найден")       
#     except Exception as e:
#         logger.error(f"Произошла ошибка: {str(e)}")
#     finally:
#         page.quit()

















# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options
# import time
# from selenium_stealth import stealth
# import logging
# import re
# from random import randint
# from dotenv import load_dotenv
# import os

# load_dotenv()
# PROXY_USER = os.getenv('PROXY_USER')
# PROXY_PASS = os.getenv('PROXY_PASS')

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger('parse')

# headers = [
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:47.0) Gecko/20100101 Firefox/47.0',
#         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
#         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:53.0) Gecko/20100101 Firefox/53.0',
#         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
#     ]

# PROXYS = ['195.19.200.130:8000', '195.19.115.79:8000', '195.19.200.219:8000']
# USERNAME = PROXY_USER
# PASSWORD = PROXY_PASS

# def parse_from_ozon(args):

#     proxy = PROXYS[randint(0, 2)]

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
#     options.add_argument(f"user-agent={headers[randint(0,2)]}")
#     options.add_argument(f'--proxy-server=http://{USERNAME}:{PASSWORD}@{proxy}')
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option('useAutomationExtension', False)

#     driver = webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=options)
#     driver.get(f'https://www.ozon.ru/product/{str(args)}')
#     logger.info(driver.page_source)
    
#     try:
#         WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
#         price_element = WebDriverWait(driver, 30).until(
#             EC.visibility_of_element_located((By.XPATH, "//span[contains(@class, 'tsHeadline600Large')")) # tsHeadline600Large
#         )

#         price_with_discount_ozon = int(re.sub(r'\D', '', price_element.text.strip()))
#         time.sleep(2)
#         return price_with_discount_ozon
#     except:
#         logger.info("Элемент с классами 'tsHeadline600Large' из Ozon не найден")
#         return None
#     finally:
#         driver.quit()

# def parse_from_wb(args):

#     proxy = PROXYS[randint(0, 2)]

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
#     options.add_argument(f"user-agent={headers[randint(0,2)]}")
#     options.add_argument(f'--proxy-server=http://{USERNAME}:{PASSWORD}@{proxy}')
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option('useAutomationExtension', False)

#     driver = webdriver.Remote(command_executor="http://selenium:4444/wd/hub", options=options)
#     driver.get(f'https://www.wildberries.ru/catalog/{str(args)}/detail.aspx?targetUrl=BP')
#     logger.info(driver.page_source)
    
#     try:
#         WebDriverWait(driver, 30).until(lambda d: d.execute_script('return document.readyState') == 'complete')
#         price_element = WebDriverWait(driver, 30).until(
#             EC.visibility_of_element_located((By.XPATH, "//span[contains(@class, 'price-block__wallet-price') and contains(@class, 'red-price')]"))
#         )
#         price_with_discount_wb = int(re.sub(r'\D', '', price_element.text.strip()))
#         time.sleep(2)
#         return price_with_discount_wb
#     except:
#         logger.info("Элемент с классами 'price-block__wallet-price' и 'red-price' из WB не найден")
#         try:
#             price_element = WebDriverWait(driver, 30).until(
#                 EC.visibility_of_element_located((By.XPATH, "//span[contains(@class, 'price-block__wallet-price')]"))
#             )
#             price_with_discount_wb = int(price_element.text.strip().replace('&nbsp;', '').replace('₽', '').replace(' ', ''))
#             time.sleep(2)
#             return price_with_discount_wb
#         except:
#             logger.info("Элемент с классом 'price-block__wallet-price' из WB не найден")
#             return None
#     finally:
#         driver.quit()

    
    