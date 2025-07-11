from celery import shared_task
import requests
import os
from dotenv import load_dotenv
from .models import Review
from django.utils import timezone
import datetime

@shared_task
def fetch_reviews():

    load_dotenv()
    jwt = os.getenv('jwt')
    url = 'https://feedbacks-api.wildberries.ru/api/v1/feedbacks'

    with open('prod_args.txt', 'r') as f:
        prod_args = [ar.strip for ar in f.readlines()]

    for prod_arg in prod_args:
        headers = {
            'Authorization':jwt
        }
        params = {
            "isAnswered":True,
            "nmId":prod_arg,
            "take":5000,
            "skip":0
        }
        response = requests.get(url, headers=headers, params=params)
        reviews_data = response.json()

        for review in reviews_data['data']['feedbacks']:
            review_id = review['id']
            article_number = prod_arg
            author = review['userName']
            rating = review['productValuation']
            text = review['text']
            date = datetime(review['createdDate'])
            
            # Сохранение отзыва в базу данных, если он новый
            Review.objects.update_or_create(
                review_id=review_id,
                defaults={'article_number':article_number, 'date':date, 'author':author, 'rating':rating, 'text': text}
            )
    cutoff_date = timezone.now() - datetime.timedelta(days=730)
    Review.objects.filter(date__lt=cutoff_date).delete()