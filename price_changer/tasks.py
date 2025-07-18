from celery import shared_task
import requests
import os
from dotenv import load_dotenv
from .models import Product_from_wb, Product_from_ozon
from bs4 import BeautifulSoup
from decimal import Decimal
from random import randint

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
    'https': 'https://188.234.158.66:80',
}

def parse_and_save_from_wb(args):
    url = f'https://www.wildberries.ru/catalog/{str(args)}/detail.aspx?targetUrl=GP'
    resp = requests.get(url, headers=headers[randint(0,2)], proxies=proxies)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.content, 'html.parser')
        div_list = soup.find('span', attrs={'class': 'price-block__price'})

        price_without_discount_wb = Decimal(div_list.find('ins', attrs={'class': 'price-block__final-price wallet'}).text.replae('&nbsp;', '').replace('₽', ''))
        price_with_discount_wb = Decimal(div_list.find('span', attrs={'class': 'price-block__wallet-price red-price'}).text.replae('&nbsp;', '').replace('₽', ''))

        product, created = Product_from_wb.objects.get_or_create(
                prod_art_from_wb=i,
                defaults={
                    'price_without_discount_wb': price_without_discount_wb,
                    'price_with_discount_wb': price_with_discount_wb,
                    'discount_wb': Decimal((price_without_discount_wb/price_with_discount_wb - 1)*100)                       
                }
            )
        
        if not created:
            product.price_without_discount_wb = price_without_discount_wb
            product.price_with_discount_wb = price_with_discount_wb
            product.save()
            print(f"Обновлен товар: {args}")
        else:
            print(f"Создан новый товар: {args}")


def parse_and_save_from_ozon(args):
    url = f'https://www.ozon.ru/product/{str(args)}'
    resp = requests.get(url, headers=headers[randint(0,2)], proxies=proxies)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.content, 'html.parser')
        prod_art_from_ozon = soup.find('div', attrs={'class':'ga5_3_1-a2 tsBodyControl400Small'}).text.replace('Артикул: ', '')
        div_list = soup.find('div', attrs={'class': 'k4z_27'})

        price_without_discount_ozon = Decimal(div_list.find('span', attrs={'class': 'zk8_27 z8k_27 l4l_27'}).text.replae('&thinsp;', '').replace('₽', ''))
        price_with_discount_ozon = Decimal(div_list.find('span', attrs={'class': 'z3k_27 kz2_27'}).text.replae('&thinsp;', '').replace('₽', ''))

        product, created = Product_from_ozon.objects.get_or_create(
                prod_art_from_wb=prod_art_from_ozon,
                defaults={
                    'price_without_discount_ozon': price_without_discount_ozon,
                    'price_with_discount_ozon': price_with_discount_ozon,
                    'discount_ozon': Decimal((price_without_discount_ozon/price_with_discount_ozon - 1)*100)                       
                }
            )
        
        if not created:
            product.price_without_discount_ozon = price_without_discount_ozon
            product.price_with_discount_ozon = price_with_discount_ozon
            product.save()
            print(f"Обновлен товар: {prod_art_from_ozon}")
        else:
            print(f"Создан новый товар: {prod_art_from_ozon}")

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
        16144452:2235224304,
        16144457:509376019,
        16144474:2235394210,
        16144478:2235574110
    }

    headers_for_wb = {
        'Authorization':jwt
    }

    headers_ror_ozon = {
        'Client-Id':client_id,
        'Api-Key':api_key
    }
    
    for wb_arg, ozon_arg in prod_args.values():  

        params_for_wb = {
            "isAnswered":'true',
            "nmId":wb_arg,
            "take":100,
            "skip":0
        }

        params_for_ozon_get = {
            "filter": {
                "product_id": [
                    str(ozon_arg)
                ]
            },
            "limit": 1 # От 1 до 1000
        }

        params_for_ozon_post = {
            "prices": {
                "auto_action_enabled": "DISABLED",
                "auto_add_to_ozon_actions_list_enabled": "DISABLED",
                "currency_code": "RUB",
                "min_price": "!!!!!!!!",   # Минимальная цена товара после применения всех скидок
                "min_price_for_auto_actions_enabled": 'true',
                "net_price": "!!!!!!!!",   # Себестоимость товара
                "offer_id": "!!!!!!!!!",   # Фильтр по параметру offer_id
                "old_price": "!!!!!!!!!!", # Зачеркнутая цена на карточке товара
                "price": "!!!!!!!!!!!",    # Цена без учета скидки Ozon карты
                "price_strategy_enabled": "DISABLED",
                "product_id": "!!!!!!!!",  # Фильтр по параметру product_id
                "quant_size": 1,
                "vat": "0.05"
            },
        }

        response_from_wb = requests.get(url_wb, headers=headers, params=params_for_wb)
        reviews_data = response_from_wb.json()
