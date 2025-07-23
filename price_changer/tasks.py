from celery import shared_task
import requests
import os
from dotenv import load_dotenv
from .models import Product_from_wb, Product_from_ozon
from random import randint
import math
from .parsers import parse_from_ozon, parse_and_save_from_wb


@shared_task
def change_price():

    load_dotenv()
    jwt_price = os.getenv('jwt_price')
    client_id = os.getenv('client_id')
    api_key = os.getenv('api_key')
    url_wb = 'https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter'
    url_ozon_get = 'https://api-seller.ozon.ru/v5/product/info/prices'
    # url_ozon_post = 'https://api-seller.ozon.ru/v1/product/import/prices'

    prod_args = {
        236212732 : [1367964113, 1843974253],
        232314554 : [1367950643, 1843974975],
        228498596 : [1367946644, 1843959268],
        182951045 : [1367882893, 1843913521],
        296722841 : [1367183518, 1843409979],
        236216608 : [1368020708, 1844020803],
        228497127 : [1367960957, 1843971372],
        258125953 : [1906950401, 2240902428],
        239022653 : [1907035011, 2240964945],
        252129611 : [1367799106, 1843861735],
        239022843 : [1367190083, 1843417418],
        462984176 : [2215213789, 2474079859],
        465659390 : [2218731747, 2476912720],
    }

    headers_for_wb = {
        'Authorization' : jwt_price
    }

    headers_for_ozon = {
        'Client-Id' : client_id,
        'Api-Key' : api_key
    } 

    params_for_wb = {
        "limit": 1000
    }

    response_from_wb = requests.get(url_wb, headers=headers_for_wb, params=params_for_wb)
    prices_data_wb = response_from_wb.json()


    for list_goods in prices_data_wb['data']['listGoods']:

        wb_art = list_goods['nmID']
        product_id = prod_args[int(wb_art)][0]
        ozon_art = prod_args[int(wb_art)][1]

        parse_and_save_from_wb(wb_art)

        price_with_discount_ozon = int(parse_from_ozon(ozon_art).strip().replace('&thinsp;', '').replace('₽', '').replace(' ', '').replace('&nbsp;', ''))

        params_for_ozon_get = {
            "filter": {
                "product_id": [
                    str(product_id)
                ]
            },
            "limit": 1 # От 1 до 1000
        }

        response_from_ozon_get = requests.post(url_ozon_get, headers=headers_for_ozon, json=params_for_ozon_get)
        prices_data_ozon = response_from_ozon_get.json()['items'][0]['price']

        # min_price = prices_data_ozon['min_price']   # Минимальная цена товара после применения всех скидок
        # net_price = prices_data_ozon['net_price']   # Себестоимость товара
        # offer_id = response_from_ozon_get.json()['items'][0]['offer_id']   # Фильтр по параметру offer_id
        # old_price = prices_data_ozon['old_price']   # Зачеркнутая цена на карточке товара

        price_without_co_invest = int(prices_data_ozon['marketing_seller_price'])   # Цена без учета соинвеста
        price_with_co_invest = int(prices_data_ozon['marketing_price'])   # Цена с учетом соинвеста
        discount_co_invest = round(1 - price_with_co_invest / price_without_co_invest, 2)   #Скидка соинвеста
        discount_ozon_with_wallet = round(1 - price_with_discount_ozon / price_with_co_invest, 2)  # Цена товара с учетом Ozon кошелька
        price_wb = Product_from_wb.objects.values('price_with_discount_wb').first()
        price_with_discount_wb = price_wb['price_with_discount_wb']
        price_ozon_s_be_with_wallet = int(math.floor(int(price_with_discount_wb) * 1.01))   # Цена на Ozon, которая должна быть с учетом скидки Ozon кошелька
        price_ozon_s_be_with_co_invest = int(math.floor(price_ozon_s_be_with_wallet / (1 - discount_ozon_with_wallet)))  # Цена на Ozon, которая должна быть с учетом скидки соинвеста

        if price_ozon_s_be_with_co_invest > 0:
            price_ozon_s_be = math.floor(price_ozon_s_be_with_co_invest / (1 - discount_co_invest))   # Цена, которая должна быть на Ozon у продавца
        else:
            price_ozon_s_be = price_without_co_invest

        product, created = Product_from_ozon.objects.get_or_create(
                prod_art_from_wb=product_id,
                defaults={
                    'price_with_discount_ozon': price_with_discount_ozon,
                    'price_without_co_invest': price_without_co_invest,
                    'price_with_co_invest': price_with_co_invest,
                    'discount_co_invest': discount_co_invest,
                    'discount_ozon_with_wallet': discount_ozon_with_wallet,
                    'price_ozon_s_be_with_wallet': price_ozon_s_be_with_wallet,
                    'price_ozon_s_be_with_co_invest': price_ozon_s_be_with_co_invest,
                    'price_ozon_s_be': price_ozon_s_be
                }
            )
        
        if not created:
            product.price_with_discount_ozon = price_with_discount_ozon
            product.price_without_co_invest = price_without_co_invest
            product.price_with_co_invest = price_with_co_invest
            product.discount_co_invest = discount_co_invest
            product.discount_ozon_with_wallet = discount_ozon_with_wallet
            product.price_ozon_s_be_with_wallet = price_ozon_s_be_with_wallet
            product.price_ozon_s_be_with_co_invest = price_ozon_s_be_with_co_invest
            product.price_ozon_s_be = price_ozon_s_be
            product.save()
            print(f"Обновлен товар: {product_id}")
        else:
            print(f"Создан новый товар: {product_id}")


        # params_for_ozon_post = {
        #     "prices": {
        #         "auto_action_enabled": "DISABLED",
        #         "auto_add_to_ozon_actions_list_enabled": "DISABLED",
        #         "currency_code": "RUB",
        #         "min_price": min_price,   # Минимальная цена товара после применения всех скидок
        #         "min_price_for_auto_actions_enabled": 'true',
        #         "net_price": net_price,   # Себестоимость товара
        #         "offer_id": offer_id,   # Фильтр по параметру offer_id
        #         "old_price": old_price, # Зачеркнутая цена на карточке товара
        #         "price": price_ozon_s_be,    # Цена без учета скидки Ozon карты
        #         "price_strategy_enabled": "DISABLED",
        #         "product_id": product_id,  # Фильтр по параметру product_id
        #         "quant_size": 1,
        #         "vat": "0.05"
        #     },
        # }

        # requests.post(url_ozon_post, headers=headers_for_ozon, json=params_for_ozon_post)       
