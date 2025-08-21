# from celery import shared_task
import time
import requests
import os
from dotenv import load_dotenv
import math
from .parsers import parse_from_ozon, parse_from_wb
import logging
import sys
# from .models import Product_from_ozon, Product_from_wb

# python -m price_changer.tasks запуск через главную вкладку

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('price_changer.tasks')

load_dotenv()
span = int(os.getenv('span'))
distinction = int(os.getenv('distinction'))
jwt_price_cab1 = os.getenv('jwt_price_cab1')
jwt_price_cab2 = os.getenv('jwt_price_cab2')
client_id_cab1 = os.getenv('client_id_cab1')
api_key_cab1 = os.getenv('api_key_cab1')
client_id_cab2 = os.getenv('client_id_cab2')
api_key_cab2 = os.getenv('api_key_cab2')
url_ozon_get = 'https://api-seller.ozon.ru/v5/product/info/prices'
url_ozon_post = 'https://api-seller.ozon.ru/v1/product/import/prices'
url_wb_get = 'https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter'
url_wb_post = 'https://discounts-prices-api.wildberries.ru/api/v2/upload/task'

def load_dict_from_file(filename):
    """Загружает словарь из текстового файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return eval(content)
            else:
                return {}
    except (FileNotFoundError, SyntaxError) as e:
        logger.error(f"Ошибка загрузки файла {filename}: {e}")
        return {}
    
# Загрузка данных из файлов
seller_arts = load_dict_from_file('price_changer/seller_arts.txt')
prod_arts_cab1 = load_dict_from_file('price_changer/prod_arts_cab1.txt')
prod_arts_cab2 = load_dict_from_file('price_changer/prod_arts_cab2.txt')
prices_dict_cab1 = load_dict_from_file('price_changer/prices_dict_cab1.txt')
prices_dict_cab2 = load_dict_from_file('price_changer/prices_dict_cab2.txt')

def get_headers_for_ozon(ozon_art):
    """Получает заголовки для Ozon API в зависимости от артикула продавца"""
    if ozon_art == 89293:
        return {
            'Client-Id': client_id_cab1,
            'Api-Key': api_key_cab1
        }
    else:
        return {
            'Client-Id': client_id_cab2,
            'Api-Key': api_key_cab2
        }

def get_headers_for_wb(wb_art):
    """Получает заголовки для WB API в зависимости от артикула продавца"""
    if wb_art == 92041:
        return {
            'Authorization': jwt_price_cab1,
        }
    else:
        return {
            'Authorization': jwt_price_cab2,
        }

def get_product_arts(ozon_art):
    """Возвращает соответствующий словарь артикулов товаров"""
    if ozon_art == 89293:
        return prod_arts_cab1
    elif ozon_art == 2558268:
        return prod_arts_cab2
    return {}

def get_prices_dict(wb_art):
    """Возвращает соответствующий словарь цен товаров WB"""
    if wb_art == 92041:
        return prices_dict_cab1
    elif wb_art == 1391979:
        return prices_dict_cab2
    return {}

def process_product(wb_arts, ozon_arts, prices_with_discount_wb, prices_with_discount_ozon, headers_for_ozon):
    """Обрабатывает один продукт и возвращает данные о ценах для Ozon"""
    offer_id = ozon_arts[0]

    params_for_ozon_get = {
        "filter": {
            "offer_id": [str(offer_id)]
        },
        "limit": 1
    }

    try:
        response_from_ozon_get = requests.post(url_ozon_get, headers=headers_for_ozon, json=params_for_ozon_get)
        response_from_ozon_get.raise_for_status()
        
        # Проверяем, что есть данные в ответе
        response_data = response_from_ozon_get.json()
        if not response_data.get('items') or len(response_data['items']) == 0:
            logger.warning(f"Продукт {offer_id} не найден в ответе API Ozon")
            return None
            
        prices_data_ozon = response_data['items'][0]['price']
        
        # Проверяем наличие необходимых полей
        if 'marketing_seller_price' not in prices_data_ozon or 'marketing_price' not in prices_data_ozon:
            logger.warning(f"Отсутствуют необходимые поля цены для продукта {offer_id}")
            return None

    except (requests.RequestException, KeyError, IndexError) as e:
        logger.error(f"Ошибка получения данных для продукта {offer_id}: {e}")
        return None

    # Проверяем, что артикулы есть в словарях цен
    if ozon_arts[1] not in prices_with_discount_ozon:
        logger.info(f"Артикул {ozon_arts[1]} не найден в распарсенных ценах Ozon")
        return None
        
    if wb_arts not in prices_with_discount_wb:
        logger.info(f"Артикул {wb_arts} не найден в распарсенных ценах WB")
        return None

    min_price = prices_data_ozon['min_price']   # Минимальная цена товара после применения всех скидок
    net_price = prices_data_ozon['net_price']   # Себестоимость товара
    old_price = prices_data_ozon['old_price']   # Зачеркнутая цена на карточке товара
    product_id = response_from_ozon_get.json()['items'][0]['product_id']   # Фильтр по параметру product_id
    vat = prices_data_ozon['vat']

    price_with_discount_ozon = prices_with_discount_ozon[ozon_arts[1]]
    price_with_discount_wb = prices_with_discount_wb[wb_arts]
    price_without_co_invest = int(prices_data_ozon['marketing_seller_price'])
    price_with_co_invest = int(prices_data_ozon['marketing_price'])
    
    if price_without_co_invest == 0:
        logger.warning(f"Цена без соинвеста равна 0 для продукта {offer_id}")
        return None
        
    discount_co_invest = round(1 - price_with_co_invest / price_without_co_invest, 2)
    
    if price_with_co_invest == 0:
        logger.warning(f"Цена с соинвестом равна 0 для продукта {offer_id}")
        return None
        
    discount_ozon_with_wallet = round(1 - price_with_discount_ozon / price_with_co_invest, 2)
    price_ozon_s_be_with_wallet = int(math.floor(price_with_discount_wb * distinction))
    
    if discount_ozon_with_wallet >= 1:
        logger.warning(f"Скидка Ozon кошелька >= 1 для продукта {offer_id}")
        return None
        
    price_ozon_s_be_with_co_invest = int(math.floor(price_ozon_s_be_with_wallet / (1 - discount_ozon_with_wallet)))

    if discount_co_invest >= 1:
        logger.warning(f"Скидка соинвеста >= 1 для продукта {offer_id}")
        return None
        
    if price_ozon_s_be_with_co_invest > 0:
        price_ozon_s_be = math.floor(price_ozon_s_be_with_co_invest / (1 - discount_co_invest))
    else:
        price_ozon_s_be = price_without_co_invest

    return {
            "auto_action_enabled": "DISABLED",
            "auto_add_to_ozon_actions_list_enabled": "DISABLED",
            "currency_code": "RUB",
            "min_price": str(min_price),
            "min_price_for_auto_actions_enabled": True,
            "net_price": str(net_price),
            "offer_id": str(offer_id),
            "old_price": str(old_price),
            "price": str(price_ozon_s_be),
            "price_strategy_enabled": "DISABLED",
            "product_id": int(product_id),
            # "quant_size": 1,
            "vat": str(vat)
        }

def process_price(wb_articul, old_price, wb_price, wb_old_price):
    """Обрабатывает один продукт и возвращает данные о ценах для WB"""
    # Проверяем какая цена, спарсенная или необходимая, больше или меньше
    if wb_price < old_price:
        # Если спарсенная цена больше от необходимой
        price_difference = 1 - wb_price / old_price
        new_price = math.floor(wb_old_price * (1 - price_difference))
    elif old_price < wb_price:
        # Если спарсенная цена меньше от необходимой
        price_difference = 1 - old_price / wb_price
        new_price = math.floor(wb_old_price / (1 - price_difference))
    else:
        # Если равны, то пропускаем "итерацию"
        return None

    return {
        "nmID": int(wb_articul),
        "price": int(new_price)
    }

# @shared_task
def change_price():

    params_for_ozon_post_all = {"prices": []}
    params_for_wb_post_all = {"data": []}
    prices_data_dict_wb = {}

    for wb_art, ozon_art in seller_arts.items():

        headers_for_wb = get_headers_for_wb(wb_art)
        params_for_wb_get = {
            "limit": 1000
        }
    
        try:
            response_from_wb_get = requests.get(url_wb_get, headers=headers_for_wb, json=params_for_wb_get)
            response_from_wb_get.raise_for_status()
            
            # Проверяем, что есть данные в ответе
            response_data = response_from_wb_get.json()
            if not response_data.get('data') or len(response_data['data']['listGoods']) == 0:
                logger.warning(f"Товары не найден в ответе API WB")
                continue

        except (requests.RequestException, KeyError, IndexError) as e:
            logger.error(f"Ошибка получения данных товаров с WB: {e}")
            continue

        for price_data_wb in response_data['data']['listGoods']:
            # Проверяем на наличие данных о цене у товара
            if price_data_wb['sizes'][0]['price']:
                prices_data_dict_wb[price_data_wb['nmID']] = price_data_wb['sizes'][0]['price']
            else:
                logger.info(f"Не нашлись данные цены для {price_data_wb['nmID']}")

        try:
            prices_with_discount_wb = parse_from_wb(wb_art)
            
            # Проверяем, что парсинг прошел успешно
            if not prices_with_discount_wb:
                logger.error(f"Не удалось распарсить цены для WB арт {wb_art}")
                continue
                
        except Exception as e:
            logger.error(f"Ошибка парсинга для WB арт {wb_art}: {e}")
            continue
        
        prices_dict = get_prices_dict(wb_art)

        for wb_articul, wb_price in prices_dict.items():
            # Проверям на равенство цены насранице WB от ожидаемой
            if wb_articul not in prices_with_discount_wb:
                logger.warning(f"Артикул {wb_articul} не найден в распарсенных ценах WB")
                continue
            old_price = prices_with_discount_wb[wb_articul]

            if old_price and not (wb_price - span <= old_price <= wb_price + span):
                if wb_articul not in prices_data_dict_wb:
                    logger.warning(f"Артикул {wb_articul} не найден в данных WB API")
                    continue
                wb_old_price = prices_data_dict_wb[wb_articul]
                new_price_for_wb = process_price(wb_articul, old_price, wb_price, wb_old_price)

                # Проверяем на наличие полученных данных new_price_for_wb
                if new_price_for_wb:
                    logger.info(f"Новая цена для WB: {new_price_for_wb['price']}")
                    params_for_wb_post_all['data'].append(new_price_for_wb)
                else:
                    logger.warning(f"Не удалось обработать цену продукта WB: {wb_articul}")
                    continue
            
            else:
                logger.warning(f"Нет данных по цене с парсенных результатов: {wb_articul}")
                continue

        res_for_wb = requests.post(url_wb_post, headers=headers_for_wb, json=params_for_wb_post_all)
        logger.info(f"Статус ответа: {res_for_wb.status_code}")

        if res_for_wb.status_code == 200 or res_for_wb.status_code == 208:
            logger.info(f"Изменена ли цена товара {res_for_wb.json()['data']['id']}: {not res_for_wb.json()['data']['alreadyExists']}")
            if res_for_wb.json()['data']['alreadyExists'] == True:
                logger.info(f"Ошибки: {res_for_wb.json()['errorText']}")
        else:
            logger.info(f"Сообщение ошибки: {res_for_wb.json()['errorText']}")

        time.sleep(5)

        try:
            prices_with_discount_wb = parse_from_wb(wb_art)
            prices_with_discount_ozon = parse_from_ozon(ozon_art)
            
            # Проверяем, что парсинг прошел успешно
            if not prices_with_discount_wb or not prices_with_discount_ozon:
                logger.error(f"Не удалось распарсить цены для WB арт {wb_art}, Ozon арт {ozon_art}")
                continue
                
        except Exception as e:
            logger.error(f"Ошибка парсинга для WB арт {wb_art}, Ozon арт {ozon_art}: {e}")
            continue

        headers_for_ozon = get_headers_for_ozon(ozon_art)
        product_arts_dict = get_product_arts(ozon_art)

        # Проверяем, что словарь артикулов не пустой
        if not product_arts_dict:
            logger.warning(f"Не найден словарь артикулов для Ozon арт {ozon_art}")
            continue

        for wb_arts, ozon_arts in product_arts_dict.items():
            # Проверяем структуру ozon_arts
            if not isinstance(ozon_arts, list) or len(ozon_arts) < 2:
                logger.warning(f"Некорректная структура ozon_arts для WB арт {wb_arts}: {ozon_arts}")
                continue
                
            params_for_ozon_post = process_product(
                wb_arts, ozon_arts, prices_with_discount_wb, 
                prices_with_discount_ozon, headers_for_ozon
            )

            if params_for_ozon_post:
                params_for_ozon_post_all['prices'].append(params_for_ozon_post)
            else:
                logger.warning(f"Не удалось обработать продукт WB: {wb_arts}, Ozon: {ozon_arts}")

        res_for_ozon = requests.post(url_ozon_post, headers=headers_for_ozon, json=params_for_ozon_post_all)
        logger.info(f"Статус ответа: {res_for_ozon.status_code}")

        if res_for_ozon.status_code == 200:
            for i in range(len(res_for_ozon.json()['result'])):
                logger.info(f"Изменена ли цена товара {res_for_ozon.json()['result'][i]['offer_id']}: {res_for_ozon.json()['result'][i]['updated']}")
                if res_for_ozon.json()['result'][i]['updated'] == False:
                    logger.info(f"Ошибки: {res_for_ozon.json()['result'][i]['errors']}")
        else:
            logger.info(f"Код ошибки: {res_for_ozon.json()['code']}, сообщение ошибки: {res_for_ozon.json()['message']}")

if __name__ == "__main__":
    change_price()






# from celery import shared_task
# import requests
# import os
# from dotenv import load_dotenv
# import math
# from .parsers import parse_from_ozon, parse_from_wb
# import logging
# import json
# # from .models import Product_from_ozon, Product_from_wb

# # python -m price_changer.tasks запуск через главную вкладку

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger('price_changer.tasks')

# load_dotenv()
# client_id_cab1 = os.getenv('client_id_cab1')
# api_key_cab1 = os.getenv('api_key_cab1')
# client_id_cab2 = os.getenv('client_id_cab2')
# api_key_cab2 = os.getenv('api_key_cab2')
# url_ozon_get = 'https://api-seller.ozon.ru/v5/product/info/prices'
# # url_ozon_post = 'https://api-seller.ozon.ru/v1/product/import/prices'

# seller_arts = {
#     92041 : 89293,
#     1391979 : 2558268
# }
    
# prod_arts_cab1 = {
#     33641962 : [33641962, 279223783],
#     16144464 : [4464100800, 279223426],
#     16144461 : [16144461, 485987080],
#     16144458 : [16144458, 488089809],
#     18818825 : [18818825, 487051162],
#     16144445 : [16144445, 486053425],
#     16144447 : [16144457, 509376019],
#     16144451 : [4451100800, 509495481],
#     160925362 : [160925362, 1045899799],
#     27886874 : [27886874, 1045946594],
#     16144447 : [4447100800, 1765179665],
#     16144455 : [4455100800, 1775960875],
#     253224463 : [253224463, 1777040306],
#     253224043 : [253224043, 1777104588],
#     16144473 : [355100800, 487061186],
#     16144482 : [16144482, 2234526836],
#     31683551 : [31683551, 2234861190],
#     247211124 : [247211124, 2234968818],
#     253224239 : [253224239, 2235045529],
#     16144452 : [16144452, 2235224304],
#     16144457 : [16144457, 509376019],
#     16144474 : [16144474, 2235394210],
#     16144478 : [16144478, 2235574110],
# }

# prod_arts_cab2 = {
#     236212732 : [2732100, 1843974253],
#     232314554 : [232314554, 1843974975],
#     228498596 : [228498596, 1843959268],
#     182951045 : [182951045, 1843913521],
#     296722841 : [296722841, 1843409979],
#     236216608 : [236216608, 1844020803],
#     228497127 : [228497127, 1843971372],
#     258125953 : [258125953, 2240902428],
#     239022653 : [239022653, 2240964945],
#     252129611 : [252129611, 1843861735],
#     239022843 : [239022843, 1843417418],
#     462984176 : [462984176, 2474079859],
#     465659390 : [465659390, 2476912720],
# }

# @shared_task
# def change_price():

#     for wb_art, ozon_art in seller_arts.items():

#         prices_with_discount_wb = parse_from_wb(wb_art)

#         prices_with_discount_ozon = parse_from_ozon(ozon_art)

#         headers_for_ozon = {
#             'Client-Id' : client_id_cab1 if ozon_art == 89293 else client_id_cab2,
#             'Api-Key' : api_key_cab1 if ozon_art == 89293 else api_key_cab2
#         } 

#         prodacts = []

#         if ozon_art == 89293:
#             for wb_arts, ozon_arts in prod_arts_cab1.items():
#                 if wb_arts in prices_with_discount_wb.keys() and ozon_arts[1] in prices_with_discount_ozon.keys():

#                     product_id = ozon_arts[0]

#                     params_for_ozon_get = {
#                         "filter": {
#                             "product_id": [
#                                 str(product_id)
#                             ]
#                         },
#                         "limit": 1 # От 1 до 1000
#                     }

#                     response_from_ozon_get = requests.post(url_ozon_get, headers=headers_for_ozon, json=params_for_ozon_get)
#                     prices_data_ozon = response_from_ozon_get.json()['items'][0]['price']

#                     # min_price = prices_data_ozon['min_price']   # Минимальная цена товара после применения всех скидок
#                     # net_price = prices_data_ozon['net_price']   # Себестоимость товара
#                     # offer_id = response_from_ozon_get.json()['items'][0]['offer_id']   # Фильтр по параметру offer_id
#                     # old_price = prices_data_ozon['old_price']   # Зачеркнутая цена на карточке товара

#                     price_with_discount_ozon = prices_with_discount_ozon[ozon_arts[1]]
#                     price_with_discount_wb = prices_with_discount_wb[wb_arts]
#                     price_without_co_invest = int(prices_data_ozon['marketing_seller_price'])   # Цена без учета соинвеста
#                     price_with_co_invest = int(prices_data_ozon['marketing_price'])   # Цена с учетом соинвеста
#                     discount_co_invest = round(1 - price_with_co_invest / price_without_co_invest, 2)   #Скидка соинвеста
#                     discount_ozon_with_wallet = round(1 - price_with_discount_ozon / price_with_co_invest, 2)  # Цена товара с учетом Ozon кошелька
#                     price_ozon_s_be_with_wallet = int(math.floor(price_with_discount_wb * 1.01))   # Цена на Ozon, которая должна быть с учетом скидки Ozon кошелька
#                     price_ozon_s_be_with_co_invest = int(math.floor(price_ozon_s_be_with_wallet / (1 - discount_ozon_with_wallet)))  # Цена на Ozon, которая должна быть с учетом скидки соинвеста

#                     if price_ozon_s_be_with_co_invest > 0:
#                         price_ozon_s_be = math.floor(price_ozon_s_be_with_co_invest / (1 - discount_co_invest))   # Цена, которая должна быть на Ozon у продавца
#                     else:
#                         price_ozon_s_be = price_without_co_invest

#                     # product_from_ozon = Product_from_ozon(
#                     #     prod_art_from_ozon=ozon_art,
#                     #     price_with_discount_ozon=price_with_discount_ozon,
#                     #     price_without_co_invest=price_without_co_invest,
#                     #     price_with_co_invest=price_with_co_invest,
#                     #     discount_co_invest=discount_co_invest,
#                     #     discount_ozon_with_wallet=discount_ozon_with_wallet,
#                     #     price_ozon_s_be_with_wallet=price_ozon_s_be_with_wallet,
#                     #     price_ozon_s_be_with_co_invest=price_ozon_s_be_with_co_invest,
#                     #     price_ozon_s_be=price_ozon_s_be
#                     #     )
#                     # logger.info(product_from_ozon)
#                     # product_from_ozon.save()

#                     # product_from_wb = Product_from_wb(
#                     #     prod_art_from_wb=wb_arts,
#                     #     price_with_discount_wb=price_with_discount_wb
#                     # )
#                     # logger.info(product_from_wb)
#                     # product_from_wb.save()

#                     product = {
#                             'Артикул товара на Ozon': product_id,
#                             'Артикул товара на WB': wb_arts,
#                             'Цены':{
#                                 'Цена на WB с кошельком': price_with_discount_wb,
#                                 'Цена товара в Ozon с учетом кошелька': price_with_discount_ozon,
#                                 'Цена в Ozon без соинвеста': price_without_co_invest,
#                                 'Цена в Ozon с соинвестом': price_with_co_invest,
#                                 'Скидка соинвеста': discount_co_invest,
#                                 'Скидка Ozon кошелька': discount_ozon_with_wallet,
#                                 'Цена на Ozon с кошельком, которая должна быть': price_ozon_s_be_with_wallet,
#                                 'Цена на Ozon с соинвестом, которая должна быть': price_ozon_s_be_with_co_invest,
#                                 'Цена, которая должна быть на Ozon': price_ozon_s_be
#                             }
#                     }

#                     prodacts.append(product)

#         elif ozon_art == 2558268:
#             for wb_arts, ozon_arts in prod_arts_cab2.items():
#                 if wb_arts in prices_with_discount_wb.keys() and ozon_arts[1] in prices_with_discount_ozon.keys():

#                     product_id = ozon_arts[0]

#                     params_for_ozon_get = {
#                         "filter": {
#                             "product_id": [
#                                 str(product_id)
#                             ]
#                         },
#                         "limit": 1 # От 1 до 1000
#                     }

#                     response_from_ozon_get = requests.post(url_ozon_get, headers=headers_for_ozon, json=params_for_ozon_get)
#                     prices_data_ozon = response_from_ozon_get.json()['items'][0]['price']

#                     # min_price = prices_data_ozon['min_price']   # Минимальная цена товара после применения всех скидок
#                     # net_price = prices_data_ozon['net_price']   # Себестоимость товара
#                     # offer_id = response_from_ozon_get.json()['items'][0]['offer_id']   # Фильтр по параметру offer_id
#                     # old_price = prices_data_ozon['old_price']   # Зачеркнутая цена на карточке товара

#                     price_without_co_invest = int(prices_data_ozon['marketing_seller_price'])   # Цена без учета соинвеста
#                     price_with_co_invest = int(prices_data_ozon['marketing_price'])   # Цена с учетом соинвеста
#                     discount_co_invest = round(1 - price_with_co_invest / price_without_co_invest, 2)   #Скидка соинвеста
#                     discount_ozon_with_wallet = round(1 - price_with_discount_ozon / price_with_co_invest, 2)  # Цена товара с учетом Ozon кошелька
#                     price_ozon_s_be_with_wallet = int(math.floor(price_with_discount_wb * 1.01))   # Цена на Ozon, которая должна быть с учетом скидки Ozon кошелька
#                     price_ozon_s_be_with_co_invest = int(math.floor(price_ozon_s_be_with_wallet / (1 - discount_ozon_with_wallet)))  # Цена на Ozon, которая должна быть с учетом скидки соинвеста

#                     if price_ozon_s_be_with_co_invest > 0:
#                         price_ozon_s_be = math.floor(price_ozon_s_be_with_co_invest / (1 - discount_co_invest))   # Цена, которая должна быть на Ozon у продавца
#                     else:
#                         price_ozon_s_be = price_without_co_invest

#                     # product_from_ozon = Product_from_ozon(
#                     #     prod_art_from_ozon=ozon_art,
#                     #     price_with_discount_ozon=price_with_discount_ozon,
#                     #     price_without_co_invest=price_without_co_invest,
#                     #     price_with_co_invest=price_with_co_invest,
#                     #     discount_co_invest=discount_co_invest,
#                     #     discount_ozon_with_wallet=discount_ozon_with_wallet,
#                     #     price_ozon_s_be_with_wallet=price_ozon_s_be_with_wallet,
#                     #     price_ozon_s_be_with_co_invest=price_ozon_s_be_with_co_invest,
#                     #     price_ozon_s_be=price_ozon_s_be
#                     #     )
#                     # logger.info(product_from_ozon)
#                     # product_from_ozon.save()

#                     # product_from_wb = Product_from_wb(
#                     #     prod_art_from_wb=wb_arts,
#                     #     price_with_discount_wb=price_with_discount_wb
#                     # )
#                     # logger.info(product_from_wb)
#                     # product_from_wb.save()

#         # params_for_ozon_post = {
#         #     "prices": {
#         #         "auto_action_enabled": "DISABLED",
#         #         "auto_add_to_ozon_actions_list_enabled": "DISABLED",
#         #         "currency_code": "RUB",
#         #         "min_price": min_price,   # Минимальная цена товара после применения всех скидок
#         #         "min_price_for_auto_actions_enabled": 'true',
#         #         "net_price": net_price,   # Себестоимость товара
#         #         "offer_id": offer_id,   # Фильтр по параметру offer_id
#         #         "old_price": old_price, # Зачеркнутая цена на карточке товара
#         #         "price": price_ozon_s_be,    # Цена без учета скидки Ozon карты
#         #         "price_strategy_enabled": "DISABLED",
#         #         "product_id": product_id,  # Фильтр по параметру product_id
#         #         "quant_size": 1,
#         #         "vat": "0.05"
#         #     },
#         # }

#         # requests.post(url_ozon_post, headers=headers_for_ozon, json=params_for_ozon_post)       
