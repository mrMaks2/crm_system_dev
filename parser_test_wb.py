import logging
from DrissionPage import ChromiumPage, ChromiumOptions
from random import randint
import re
import time
import tempfile
import sys
import json
from fake_useragent import UserAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('price_changer.tasks')

ua = UserAgent(browsers='chrome', os='windows', platforms='pc')

def get_chromium_options():

    co = ChromiumOptions()

    co.set_argument('--no-sandbox')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-web-security')
    co.set_argument('--disable-blink-features=AutomationControlled')
    # co.set_argument('--headless=new')
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

        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(page.html)

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

if __name__ == "__main__":
    result = parse_from_ozon(92041)
    print(f"Результат: {result}")