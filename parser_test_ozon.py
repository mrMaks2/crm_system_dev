# import logging
# from DrissionPage import ChromiumPage, ChromiumOptions
# from time import sleep
# from dotenv import load_dotenv
# import os
# from random import randint

# load_dotenv()
# PROXY_USER = os.getenv('PROXY_USER')
# PROXY_PASS = os.getenv('PROXY_PASS')

# headers = [
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:47.0) Gecko/20100101 Firefox/47.0',
#         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
#         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
#     {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:53.0) Gecko/20100101 Firefox/53.0',
#         'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
#     ]

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger('ozon')


# def main():
#     try:
#         co = ChromiumOptions().auto_port()
#         co.incognito()
#         # co.set_argument('--disable-web-security')
#         # co.set_argument('--headless=new')
#         co.no_imgs()
#         # co.set_argument('--disable-blink-features=AutomationControlled')
#         # co.set_argument('--disable-dev-shm-usage')
#         # co.set_argument('--remote-debugging-port=0')

#         proxy_url = f"http://n61Jcu:P4rhyT@195.19.200.130:8000"
#         co.set_proxy(proxy_url)
        
#         page = ChromiumPage(addr_or_opts=co)
#         user_agent = headers[randint(0, 2)]['User-Agent']
#         page.set.user_agent(user_agent)
        
#         page.get('https://www.ozon.ru/product/1843974253', timeout=30)
#         sleep(2)
        
#         price_element = page.ele('@class=k3z_27 zk2_27', timeout=15)
        
#         if price_element:
#             price_text = price_element.text.strip()
#             cleaned_price = ''.join(c for c in price_text if c.isdigit())
#             logger.debug(f"Успешно! Цена: {cleaned_price} руб.")
#             page.get_screenshot('ozon_price.png')
#         else:
#             logger.debug("Цена не найдена")
#             page.get_screenshot('ozon_no_price.png')
            
#     except Exception as e:
#         logger.error(f"Критическая ошибка: {str(e)}")
#         if 'page' in locals():
#             page.get_screenshot('ozon_error.png')
#     finally:
#         if 'page' in locals():
#             page.quit()

# if __name__ == "__main__":
#     main()





import logging
from DrissionPage import ChromiumPage, ChromiumOptions
from DrissionPage.common import By


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('ozon')

def main():

    co = ChromiumOptions()
    co.no_imgs()
    co.incognito()
    # co.set_argument("--disable-blink-features=AutomationControlled")
    # co.set_argument("--disable-infobars")
    # co.set_argument("--no-first-run")
    # co.set_argument("--headless=new")
    # co.set_argument("--disable-extensions")
    # co.set_argument("--disable-gpu")
    co.set_argument('--disable-web-security')
    # co.set_argument('--proxy-server=http://n61Jcu:P4rhyT@195.19.200.130:8000')
    # co.set_argument('--ignore-certificate-errors')
    # co.set_argument('--disable-redirect-handling')
    # co.set_argument("--disable-save-password-bubble")
    # co.set_argument("--disable-autofill")
    # co.set_argument('--no-sandbox')

    page = ChromiumPage(addr_or_opts=co)
    
    page.set.user_agent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36')

    page.run_js('''
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
        window.navigator.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3],
        });
    ''')

    page.get("https://bot.sannysoft.com")  # Сервис для проверки автоматизации
    page.get_screenshot("stealth_test.png")
    
    try:
        page.get('https://www.ozon.ru/product/1843974253')

        page.wait.load_start()
        price_element = page.ele('@class=k3z_27 zk2_27', timeout=20)
        
        if price_element:
            price_text = price_element.text.strip()
            cleaned_price = (price_text
                           .replace('&thinsp;', '')
                           .replace('₽', '')
                           .replace(' ', '')
                           .replace(' ', '')
                           .replace('&nbsp;', '')
                           .replace('\u00A0', ''))
            logger.debug(f"Цена товара: {cleaned_price}")
        else:
            logger.debug("Элемент с ценой не найден")
            
    except Exception as e:
        page.get_screenshot('ozon_page.png')
        logger.error(f"Произошла ошибка: {str(e)}")
    finally:
        page.quit()

if __name__ == "__main__":
    main()







# import logging
# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.common.by import By
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.options import Options

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger('ozon')

# def main():
#     options = Options()
#     # options.add_argument("--headless=new")
#     options.add_argument("--disable-blink-features=AutomationControlled")
#     options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36")
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option('useAutomationExtension', False)
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
#     driver.get('https://www.ozon.ru/product/1843974253')
#     driver.implicitly_wait(20)
    
#     try:
#         price_element = WebDriverWait(driver, 20).until(
#             EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'k3z_27') and contains(@class, 'zk2_27')]")) 
#         )

#         logger.debug(price_element.text.strip().replace('&thinsp;', '').replace('₽', '').replace(' ', '').replace(' ', '').replace('&nbsp;', '').replace('\u00A0', ''))
#     except:
#         logger.debug("Элемент с классами 'z3k_27' и 'kz2_27' не найден")
#     finally:
#         driver.quit()

# if __name__ == "__main__":
#     main()