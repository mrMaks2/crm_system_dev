from celery import shared_task
import requests
import os
from dotenv import load_dotenv
from .models import Product_from_wb, Product_from_ozon
from bs4 import BeautifulSoup
from decimal import Decimal
from random import randint
import time
import math

headers = [
    {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:47.0) Gecko/20100101 Firefox/47.0',
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.36',
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'},
    {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:53.0) Gecko/20100101 Firefox/53.0',
        'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
    ]

proxies = {
    'http': 'http://188.234.158.66:80',
    'http': 'https://62.84.120.61:80',
    'http': 'https://77.238.103.98:8080',
    'http': 'https://80.87.192.7:3128',
    'http': 'https://147.45.104.252:80',
    'http': 'https://91.222.238.112:80',
    'https': 'https://84.53.245.42:41258',
    'http': 'https://46.47.197.210:3128',
    'http': 'https://79.174.12.190:80',
}

def parse_and_save_from_wb(args):

    url = f'https://www.wildberries.ru/catalog/{str(args)}/detail.aspx?targetUrl=GP'
    resp = requests.get(url, headers=headers[randint(0,2)], proxies=proxies[randint(0,8)])
    
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.content, 'html.parser')
        price_with_discount_wb = Decimal(soup.find('span', attrs={'class': 'price-block__wallet-price red-price'}).text.replace('&nbsp;', '').replace('₽', ''))

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
            
    time.sleep(5)


def parse_and_save_from_ozon(args):

    url = f'https://www.ozon.ru/product/{str(args)}'
    resp = requests.get(url, headers=headers[randint(0,2)], proxies=proxies[randint(0,8)])

    if resp.status_code == 200:
        soup = BeautifulSoup(resp.content, 'html.parser')
        price_with_discount_ozon = Decimal(soup.find('span', attrs={'class': 'z3k_27 kz2_27'}).text.replace('&thinsp;', '').replace('₽', ''))

        product, created = Product_from_ozon.objects.get_or_create(
                prod_art_from_wb=args,
                defaults={'price_with_discount_ozon': price_with_discount_ozon}
            )
        
        if not created:
            product.price_with_discount_ozon = price_with_discount_ozon
            product.save()
            print(f"Обновлен товар: {args}")
        else:
            print(f"Создан новый товар: {args}")

    time.sleep(5)

@shared_task
def change_price():

    load_dotenv()
    jwt = os.getenv('jwt')
    client_id = os.getenv('client_id')
    api_key = os.getenv('api_key')
    url_wb = 'https://discounts-prices-api.wildberries.ru/api/v2/list/goods/filter'
    url_ozon_get = 'https://api-seller.ozon.ru/v5/product/info/prices'
    url_ozon_post = 'https://api-seller.ozon.ru/v1/product/import/prices'

    # with open('reviews/prod_args.txt', 'r') as f:
    #     prod_args = [int(ar.strip()) for ar in f.readlines()]

    prod_args = {
        16144452 : 2235224304,
        16144457 : 509376019,
        16144474 : 2235394210,
        16144478 : 2235574110
    }

    headers_for_wb = {
        'Authorization' : jwt
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
        # price_wb = list_goods['sizes'][0]['discountedPrice']
        ozon_art = prod_args[int(wb_art)]

        parse_and_save_from_wb(wb_art)
        # discount_wb = round(price_wb / Product_from_wb.objects.values('price_with_discount_wb') - 1, 2)

        parse_and_save_from_ozon(ozon_art)

        params_for_ozon_get = {
            "filter": {
                "product_id": [
                    str(ozon_art)
                ]
            },
            "limit": 1 # От 1 до 1000
        }

        response_from_ozon_get = requests.post(url_ozon_get, headers=headers_for_ozon, json=params_for_ozon_get)
        prices_data_ozon = response_from_ozon_get.json()['items'][0]['price']
        min_price = prices_data_ozon['min_price']   # Минимальная цена товара после применения всех скидок
        net_price = prices_data_ozon['net_price']   # Себестоимость товара
        offer_id = response_from_ozon_get.json()['items'][0]['offer_id']   # Фильтр по параметру offer_id
        product_id = response_from_ozon_get.json()['items'][0]['product_id']   # Фильтр по параметру product_id
        old_price = prices_data_ozon['old_price']   # Зачеркнутая цена на карточке товара
        price_without_co_invest = prices_data_ozon['marketing_seller_price']   # Цена без учета соинвеста
        price_with_co_invest = prices_data_ozon['marketing_price']   # Цена с учетом соинвеста
        discount_co_invest = round(1 - price_with_co_invest / price_without_co_invest, 2)   #Скидка соинвеста
        discount_ozon_with_wallet = round(1 - Product_from_ozon.objects.values('price_with_discount_ozon') / price_with_co_invest, 2)  # Цена товара с учетом Ozon кошелька
        price_ozon_s_be_with_wallet = math.floor(Product_from_wb.objects.values('price_with_discount_wb') * 1.01)   # Цена на Ozon, которая должна быть с учетом скидки Ozon кошелька
        price_ozon_s_be_with_co_invest = math.floor(price_ozon_s_be_with_wallet / (1 - discount_ozon_with_wallet))  # Цена на Ozon, которая должна быть с учетом скидки соинвеста

        if price_ozon_s_be_with_co_invest > 0:
            price_ozon_s_be = math.floor(price_ozon_s_be_with_co_invest / (1 - discount_co_invest))   # Цена, которая должна быть на Ozon у продавца
        else:
            price_ozon_s_be = price_without_co_invest

        params_for_ozon_post = {
            "prices": {
                "auto_action_enabled": "DISABLED",
                "auto_add_to_ozon_actions_list_enabled": "DISABLED",
                "currency_code": "RUB",
                "min_price": min_price,   # Минимальная цена товара после применения всех скидок
                "min_price_for_auto_actions_enabled": 'true',
                "net_price": net_price,   # Себестоимость товара
                "offer_id": offer_id,   # Фильтр по параметру offer_id
                "old_price": old_price, # Зачеркнутая цена на карточке товара
                "price": price_ozon_s_be,    # Цена без учета скидки Ozon карты
                "price_strategy_enabled": "DISABLED",
                "product_id": product_id,  # Фильтр по параметру product_id
                "quant_size": 1,
                "vat": "0.05"
            },
        }

        requests.post(url_ozon_post, headers=headers_for_ozon, json=params_for_ozon_post)       
