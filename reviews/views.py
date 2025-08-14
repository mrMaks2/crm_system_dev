from django.shortcuts import render
from .models import Review
from .forms import ReviewForm, HomeForm, DateForm, ReviewsCheckingForm
from django.core.paginator import Paginator
from django.utils import timezone
import logging
import openai
import os
from dotenv import load_dotenv
# from django.contrib import messages


load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('review_views')

# docker-compose up --build

def review_list(request):
    reviews = Review.objects.all().order_by('review_id')
    article_number = request.GET.get('article_number')

    if article_number:
        reviews = reviews.filter(article_number=article_number)

    form1 = ReviewForm()
    form2 = DateForm()
    form3 = HomeForm()

    if request.method == 'POST':
        if 'sort_submit' in request.POST:
            form1 = ReviewForm(request.POST)
            if form1.is_valid():
                select_option = form1.cleaned_data['my_dropdown']
                if select_option == 'prod_arg_form':
                    reviews = reviews.order_by('article_number')
                elif select_option == 'date_form':
                    reviews = reviews.order_by('-date')
        elif 'date_submit' in request.POST:
            form2 = DateForm(request.POST)
            if form2.is_valid():
                date_start = form2.cleaned_data.get('date_start')
                date_end = form2.cleaned_data.get('date_end')
                if date_start and date_end:
                    reviews = reviews.filter(date__range=(date_start, date_end))

    paginator = Paginator(reviews, 20)
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)

    context = {
        'form1': form1,
        'form2': form2,
        'form3': form3,
        'reviews': reviews_page,
        'paginator': paginator,
    }
    return render(request, 'review_list.html', context)


def calculate_similarity(text1, text2):

    try:
        response = openai.Embedding.create(
            input=[text1, text2],
            model="text-embedding-ada-002"  #  Рекомендуется использовать embedding model
        )

        embedding1 = response['data'][0]['embedding']
        embedding2 = response['data'][1]['embedding']

        # Вычисление косинусного сходства
        dot_product = sum(x * y for x, y in zip(embedding1, embedding2))
        magnitude1 = sum(x ** 2 for x in embedding1) ** 0.5
        magnitude2 = sum(x ** 2 for x in embedding2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0  # Избегаем деления на ноль

        similarity = dot_product / (magnitude1 * magnitude2)
        return similarity

    except Exception as e:
        print(f"Ошибка при вычислении сходства: {e}")
        return None


def reviews_checking(request):
    if request.method == 'POST':
        form = ReviewsCheckingForm(request.POST)
        if form.is_valid():
            similarities = []
            article_number = form.cleaned_data['article']
            new_review = form.cleaned_data['review_example']
            old_reviews = Review.objects.filter(article_number=article_number)
            old_reviews_text = old_reviews.values_list('text', flat=True)
            old_reviews_text_list = list(old_reviews_text)
            for old_review in old_reviews_text_list:
                similarity = calculate_similarity(new_review, old_review) * 100
                if similarity is not None and similarity > 80:
                    similarities.append((similarity, old_review))
            return render(request, 'reviews_checking.html', {'form': form, 'similarities': similarities})
    similarities = None
    form = ReviewsCheckingForm()
    return render(request, 'reviews_checking.html', {'form': form, 'similarities': similarities})