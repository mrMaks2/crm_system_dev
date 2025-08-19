from celery import shared_task
import requests
import os
from dotenv import load_dotenv
from .models import Review
from django.utils import timezone
import datetime
from random import randint
import logging

# python -m reviews.tasks запуск через главную вкладку

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('review_tasks.tasks')

load_dotenv()
jwt_reviews = os.getenv('jwt_reviews')
jwt_for_resp_and_get_cab1 = os.getenv('jwt_for_resp_and_get_cab1')
url_for_reviews = 'https://feedbacks-api.wildberries.ru/api/v1/feedbacks'
url_for_response = 'https://feedbacks-api.wildberries.ru/api/v1/feedbacks/answer'

headers_reviews = {
        'Authorization':jwt_reviews
    }


@shared_task
def fetch_reviews():

    with open('reviews/prod_args.txt', 'r') as f:
        prod_args = [int(ar.strip()) for ar in f.readlines()]
    
    cutoff_date = int((timezone.now() - datetime.timedelta(days=730)).timestamp())

    for prod_arg in prod_args:   
        params = {
            "isAnswered":'true',
            "nmId":prod_arg,
            "take":5000,
            "skip":0,
            "dateFrom": cutoff_date
        }
        response = requests.get(url_for_reviews, headers=headers_reviews, params=params)
        reviews_data = response.json()

        for review in reviews_data['data']['feedbacks']:
            review_id = review['id']
            article_number = prod_arg
            author = review['userName']
            rating = review['productValuation']
            text = review['text']
            date = review['createdDate']

            Review.objects.update_or_create(
                review_id=review_id,
                defaults={'article_number':article_number, 'date':date, 'author':author, 'rating':rating, 'text': text}
            )


@shared_task
def deleter_reviews():
    cutoff_date = timezone.now() - datetime.timedelta(days=730)
    Review.objects.filter(date__lt=cutoff_date).delete()

# @shared_task
def response_to_reviews():

    with open('reviews/response_list.txt', 'r', encoding='utf-8') as f:
        response_list = [str(resp.strip().strip('"')) for resp in f.readlines()]


    headers_cab1 = {
        'Authorization':jwt_for_resp_and_get_cab1
    }

    params_reviews_cab1 = {
            "isAnswered":'false',
            "take":5000,
            "skip":0
        }
    
    response = requests.get(url_for_reviews, headers=headers_cab1, params=params_reviews_cab1)
    reviews_data = response.json()

    ids = []

    for review in reviews_data['data']['feedbacks']:
        if review['productValuation'] == 5 or review['productValuation'] == 4:
            review_id = review['id']
            ids.append(review_id)

    logger.info(ids)

    for review_id in ids:
        params_response_cab1 = {
            "id": review_id,
            "text": response_list[randint(0,38)]
        }
        logger.info(params_response_cab1['text'])
        requests.post(url_for_response, headers=headers_cab1, json=params_response_cab1)
