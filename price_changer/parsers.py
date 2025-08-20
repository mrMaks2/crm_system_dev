import logging
from DrissionPage import ChromiumPage, ChromiumOptions
from random import randint
import re
import time
import tempfile
import sys
from fake_useragent import UserAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('price_changer.tasks')

ua = UserAgent(browsers='chrome', os='windows', platforms='pc')

def get_chromium_options():

    co = ChromiumOptions()

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
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--exclude-switches=enable-automation')
    co.set_argument('--disable-features=UserAgentClientHint')
    co.set_argument('--remote-debugging-port=0')
    co.set_argument('--disable-default-apps')
    temp_dir = tempfile.mkdtemp(prefix='drissionpage_')
    co.set_argument(f'--user-data-dir={temp_dir}')
    co.no_imgs()
    co.incognito()
    
    return co, temp_dir

def gradual_scroll(page, scroll_pixels=1000, pause=1, max_scrolls=10):
    current_height = page.run_js('return document.documentElement.scrollHeight')
    
    for _ in range(max_scrolls):

        page.scroll.down(scroll_pixels)
        time.sleep(pause)

        new_height = page.run_js('return document.documentElement.scrollHeight')
        if new_height == current_height:
            break
        current_height = new_height

def parse_from_ozon(art):
    co, temp_dir = get_chromium_options()
    page = None
    
    try:

        user_agent = ua.random
        co.set_argument(f'--user-agent={user_agent}')
        
        page = ChromiumPage(addr_or_opts=co)
        page.set.user_agent(user_agent)
        
        logger.info(f"Переходим на страницу продавца Ozon {art}")
        page.get(f'https://www.ozon.ru/seller/{str(art)}')
        page.wait.load_start()
        page.wait.doc_loaded(timeout=60)
        time.sleep(5)
        gradual_scroll(page, max_scrolls=15)
        logger.info("Прокрутка страницы завершена")

        block_selectors = [
            "xpath://div[contains(@class, 'tile-root')]",
            ".qi1_24.tile-root.wi5_24.wi6_24",
            'xpath://div[contains(@class, "qi1_24") and contains(@class, "tile-root") and contains(@class, "wi5_24") and contains(@class, "wi6_24"]',
        ]

        price_selectors = [
            "xpath://span[contains(@class, 'tsHeadline500Medium')]",
            ".c35_3_3-a1.tsHeadline500Medium.c35_3_3-b1.c35_3_3-a6",
            'xpath://span[contains(@class, "tsHeadline500Medium") and contains(@class, "c35_3_3-a1") and contains(@class, "c35_3_3-b1") and contains(@class, "c35_3_3-a6"]', 
        ]

        article_selectors = [
            "xpath://a[contains(@class, 'tile-clickable-element')]",
            ".q4b1_3_0-a.tile-clickable-element.iq7_24.qi7_24",
            'xpath://a[contains(@class, "tile-clickable-element") and contains(@class, "q4b1_3_0-a") and contains(@class, "iq7_24") and contains(@class, "qi7_24"]',
        ]
        
        result = {}
        block_elements = []

        for block_selector in block_selectors:
            try:
                page.wait.ele_displayed(block_selector, timeout=10)
                logger.info(f"Применен селктор {block_selector}")
                block_elements = page.eles(block_selector, timeout=10)
                if block_elements:
                    logger.info(f"Найдено {len(block_elements)} блоков товаров")
                    break
            except:
                logger.info(f"Селектор {block_selector} не сработал: {e}")
                continue

        if not block_elements:
            logger.error("Не найдено ни одного блока товаров")
            return None
        
        for block_element in block_elements:
            price_element = None

            for price_selector in price_selectors:
                try:
                    price_element = block_element.ele(price_selector)
                    if price_element and price_element.text.strip():
                        break
                except:
                    continue
            
            if price_element:
                price_text = price_element.text.strip()
                price_with_discount_ozon = int(re.sub(r'\D', '', price_text))
                logger.info(f"Цена товара: {price_with_discount_ozon}")
            else:
                logger.info("Элемент с ценой в Ozon не найден")

            article_element = None
            for article_selector in article_selectors:
                try:
                    article_element = block_element.ele(article_selector).attr('href')
                    if article_element:
                        break
                except:
                    continue
            
            if article_element:
                article_match = re.search(r'(\d{10})', article_element)
                if article_match:
                    article_number = int(article_match.group(1))
                    logger.info(f"Артикл товара: {article_number}")
                else:
                    article_match = re.search(r'(\d{9})', article_element)
                    article_number = int(article_match.group(1))
                    logger.info(f"Артикл товара: {article_number}")
            else:
                logger.info("Элемент с артиклом в Ozon не найден")

            result[article_number] = price_with_discount_ozon
            
        return result

    except Exception as e:
        logger.error(f"Произошла ошибка при парсинге Ozon: {str(e)}")
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

def parse_from_wb(art):
    co, temp_dir = get_chromium_options()
    page = None
    
    try:

        user_agent = ua.random
        logger.info(user_agent)
        co.set_argument(f'--user-agent={user_agent}')
        
        page = ChromiumPage(addr_or_opts=co)
        page.set.user_agent(user_agent)
        
        logger.info(f"Переходим на страницу продавца WB {art}")
        page.get(f'https://www.wildberries.ru/seller/{str(art)}')
        page.wait.load_start()
        page.wait.doc_loaded(timeout=60)
        time.sleep(5)
        gradual_scroll(page, max_scrolls=15)
        logger.info("Прокрутка страницы завершена")

        block_selectors = [
            "xpath://article[contains(@class, 'product-card') and contains(@class, 'j-card-item') and contains(@class, 'j-analitics-item')]",
            "xpath://article[contains(@class, 'product-card') and contains(@class, 'j-card-item')]",
            "xpath://article[contains(@class, 'product-card') and contains(@class, 'j-analitics-item')]",
            "xpath://article[contains(@class, 'product-card')]",
        ]

        price_selectors = [
            "xpath://ins[contains(@class, 'price__lower-price') and contains(@class, 'wallet-price') and contains(@class, 'red-price')]",
            "xpath://ins[contains(@class, 'price__lower-price') and contains(@class, 'wallet-price')]",
            "xpath://ins[contains(@class, 'wallet-price')]",
            "xpath://ins[contains(@class, 'price__lower-price')]",
        ]

        article_selectors = [
            "xpath://a[contains(@class, 'product-card__link') and contains(@class, 'j-card-link') and contains(@class, 'j-open-full-product-card')]",
            "xpath://span[contains(@class, 'j-open-full-product-card')]",
        ]
        
        result = {}
        block_elements = []

        for block_selector in block_selectors:
            try:
                page.wait.ele_displayed(block_selector, timeout=10)
                logger.info(f"Применен селктор {block_selector}")
                block_elements = page.eles(block_selector, timeout=10)
                if block_elements:
                    logger.info(f"Найдено {len(block_elements)} блоков товаров")
                    break
            except:
                logger.info(f"Селектор {block_selector} не сработал: {e}")
                continue

        if not block_elements:
            logger.error("Не найдено ни одного блока товаров")
            return None
        
        for block_element in block_elements:
            price_element = None

            for price_selector in price_selectors:
                try:
                    price_element = block_element.ele(price_selector)
                    if price_element and price_element.text.strip():
                        break
                except:
                    continue
            
            if price_element:
                price_text = price_element.text.strip()
                price_with_discount_ozon = int(re.sub(r'\D', '', price_text))
                logger.info(f"Цена товара: {price_with_discount_ozon}")
            else:
                logger.info("Элемент с ценой в WB не найден")

            article_element = None
            for article_selector in article_selectors:
                try:
                    article_element = block_element.attr('data-nm-id')
                    if article_element:
                        break
                except:
                    continue
            
            if article_element:
                article_number = int(article_element.strip())
                logger.info(f"Артикл товара: {article_number}")
            else:
                logger.info("Элемент с артиклом в WB не найден")

            result[article_number] = price_with_discount_ozon
            
        return result

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
# import tempfile

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger('ozon')

# headers = [
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#      'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
#      'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
#      'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
# ]

# def get_chromium_options():
#     """Создает и настраивает опции Chromium"""
#     co = ChromiumOptions()
    
#     # Базовые настройки
#     co.set_argument('--no-sandbox')
#     co.set_argument('--disable-dev-shm-usage')
#     co.set_argument('--disable-gpu')
#     co.set_argument('--disable-web-security')
#     co.set_argument('--disable-blink-features=AutomationControlled')
#     co.set_argument('--headless=new')
#     co.set_argument('--disable-extensions')
#     co.set_argument('--disable-software-rasterizer')
#     co.set_argument('--disable-setuid-sandbox')
#     co.set_argument('--window-size=1920,1080')
#     co.set_argument('--disable-features=VizDisplayCompositor')
#     co.set_argument('--disable-background-timer-throttling')
#     co.set_argument('--disable-backgrounding-occluded-windows')
#     co.set_argument('--disable-renderer-backgrounding')
#     co.set_argument('--disable-back-forward-cache')
#     co.set_argument('--disable-ipc-flooding-protection')
#     co.set_argument('--disable-hang-monitor')
#     co.set_argument('--disable-client-side-phishing-detection')
#     co.set_argument('--disable-sync')
#     co.set_argument('--metrics-recording-only')
#     co.set_argument('--no-first-run')
#     co.set_argument('--safebrowsing-disable-auto-update')
#     co.set_argument('--disable-default-apps')
#     co.set_argument('--disable-prompt-on-repost')
#     co.set_argument('--disable-domain-reliability')
#     co.set_argument('--password-store=basic')
#     co.set_argument('--use-mock-keychain')
#     co.set_argument('--disable-component-update')
    
#     # Настройки для обхода детекции
#     co.set_argument('--disable-blink-features=AutomationControlled')
#     co.set_argument('--exclude-switches=enable-automation')
#     co.set_argument('--disable-features=UserAgentClientHint')
    
#     # Отключаем автоматический порт и используем фиксированный user data dir
#     co.set_argument('--remote-debugging-port=0')
#     co.set_argument('--disable-default-apps')
    
#     # Создаем временную директорию для user data
#     temp_dir = tempfile.mkdtemp(prefix='drissionpage_')
#     co.set_argument(f'--user-data-dir={temp_dir}')
    
#     # Отключаем изображения для ускорения
#     co.no_imgs()
#     co.incognito()
    
#     return co, temp_dir

# def parse_from_ozon(art):
#     co, temp_dir = get_chromium_options()
#     page = None
    
#     try:
#         # Устанавливаем User-Agent перед созданием страницы
#         user_agent = headers[randint(0, 2)]['User-Agent']
#         co.set_argument(f'--user-agent={user_agent}')
        
#         page = ChromiumPage(addr_or_opts=co)
        
#         # Дополнительная настройка User-Agent
#         page.set.user_agent(user_agent)
        
#         logger.debug(f"Переходим на страницу товара Ozon {art}")
#         page.get(f'https://www.ozon.ru/product/{str(art)}')
#         page.wait.load_start()
#         time.sleep(3)
        
#         # Ждем загрузки контента
#         page.wait.ele_displayed('tag:body', timeout=20)
#         time.sleep(2)
        
#         # Поиск цены с несколькими селекторами
#         price_selectors = [
#             "@class=tsHeadline600Large",
#             "xpath://div[contains(@class, 'pdp_be5') and contains(@class, 'pdp_b4e')]",
#             'xpath://span[contains(@class, "tsHeadline600Large")]',
#         ]
        
#         price_element = None
#         for selector in price_selectors:
#             try:
#                 price_element = page.ele(selector, timeout=5)
#                 if price_element and price_element.text.strip():
#                     break
#             except:
#                 continue
        
#         if price_element:
#             price_text = price_element.text.strip()
#             logger.debug(f"Найден текст цены: {price_text}")
#             price_with_discount_ozon = int(re.sub(r'\D', '', price_text))
#             logger.debug(f"Цена товара: {price_with_discount_ozon}")
#             return int(price_with_discount_ozon)
#         else:
#             logger.debug("Элемент с ценой не найден, сохраняем скриншот")
#             try:
#                 page.get_screenshot(path=f'ozon_error_{art}.png', full_page=True)
#             except:
#                 pass
#             return None
            
#     except Exception as e:
#         logger.error(f"Произошла ошибка при парсинге Ozon: {str(e)}")
#         return None
#     finally:
#         if page:
#             try:
#                 page.quit()
#             except:
#                 pass
#         # Очищаем временную директорию
#         try:
#             import shutil
#             shutil.rmtree(temp_dir, ignore_errors=True)
#         except:
#             pass

# def parse_from_wb(art):
#     co, temp_dir = get_chromium_options()
#     page = None
    
#     try:
#         user_agent = headers[randint(0, 2)]['User-Agent']
#         co.set_argument(f'--user-agent={user_agent}')
        
#         page = ChromiumPage(addr_or_opts=co)
#         page.set.user_agent(user_agent)
        
#         logger.debug(f"Переходим на страницу WB товара {art}")
#         page.get(f'https://www.wildberries.ru/catalog/{str(art)}/detail.aspx')
#         page.wait.load_start()
#         time.sleep(3)
        
#         page.wait.ele_displayed('tag:body', timeout=20)
#         time.sleep(2)
        
#         # Поиск цены на WB
#         price_selectors = [
#             'xpath://span[contains(@class, "price-block__wallet-price") and contains(@class, "red-price")]',
#             'xpath://span[contains(@class, "price-block__wallet-price")]',
#             '@class=price-block__wallet-price red-price',
#             '@class=price-block__wallet-price',
#         ]
        
#         price_element = None
#         for selector in price_selectors:
#             try:
#                 price_element = page.ele(selector, timeout=5)
#                 if price_element and price_element.text.strip():
#                     break
#             except:
#                 continue
        
#         if price_element:
#             price_text = price_element.text.strip()
#             logger.debug(f"Найден текст цены WB: {price_text}")
#             price_with_discount_wb = int(re.sub(r'\D', '', price_text))
#             logger.debug(f"Цена товара WB: {price_with_discount_wb}")
#             return int(price_with_discount_wb)
#         else:
#             logger.debug("Элемент с ценой WB не найден, сохраняем скриншот")
#             try:
#                 page.get_screenshot(path=f'wb_error_{art}.png', full_page=True)
#             except:
#                 pass
#             return None
            
#     except Exception as e:
#         logger.error(f"Произошла ошибка при парсинге WB: {str(e)}")
#         return None
#     finally:
#         if page:
#             try:
#                 page.quit()
#             except:
#                 pass
#         try:
#             import shutil
#             shutil.rmtree(temp_dir, ignore_errors=True)
#         except:
#             pass
