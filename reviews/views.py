from django.shortcuts import render
from .models import Review
from .forms import ReviewForm, HomeForm, DateForm, ReviewsCheckingForm
from django.core.paginator import Paginator
from django.utils import timezone
import logging
import datetime
# from sentence_transformers import SentenceTransformer

# docker-compose up --build - запуск Docker образа
# docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <имя_контейнера> - метод определения IP Docker контейнера

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('review_views')

# model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

def review_list(request):
    reviews = Review.objects.all().order_by('review_id')
    article_number = request.GET.get('article_number')
    sort_option = request.GET.get('sort_option')
    date_start = request.GET.get('date_start')
    date_end = request.GET.get('date_end')

    if article_number:
        reviews = reviews.filter(article_number=article_number)

    form1 = ReviewForm(request.GET or None)
    form2 = DateForm(request.GET or None)
    form3 = HomeForm(initial={'article_number': article_number} if article_number else {})

    if 'sort_option' in request.GET:
        if sort_option == 'prod_arg_form':
            reviews = reviews.order_by('article_number')
        elif sort_option == 'date_form':
            reviews = reviews.order_by('-date')

    if 'date_start' in request.GET and 'date_end' in request.GET:
        try:
            date_start = datetime.datetime.strptime(date_start, '%d/%m/%Y %H:%M')
            date_end = datetime.datetime.strptime(date_end, '%d/%m/%Y %H:%M')
            reviews = reviews.filter(date__range=(date_start, date_end))
        except (ValueError, TypeError):
            pass

    form1 = ReviewForm(initial={'my_dropdown': sort_option} if sort_option else {})
    form2 = DateForm(initial={'date_start': date_start, 'date_end': date_end} if date_start and date_end else {})

    paginator = Paginator(reviews, 50)
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)

    params = request.GET.copy()
    if 'page' in params:
        del params['page']

    context = {
        'form1': form1,
        'form2': form2,
        'form3': form3,
        'reviews': reviews_page,
        'paginator': paginator,
        'params': params,
    }
    return render(request, 'reviews/review_list.html', context)


def calculate_similarity(text1, text2):
    pass
    # try:
    #     embedding1 = model.encode(text1, normalize_embeddings=True)
    #     embedding2 = model.encode(text2, normalize_embeddings=True)
    #     similarity = sum(x * y for x, y in zip(embedding1, embedding2))
    #     return similarity

    # except Exception as e:
    #     logger.info(f"Ошибка при вычислении сходства: {e}")
    #     return None


def reviews_checking(request):
    results = []
    
    if request.method == 'POST':
        review_fields = [k for k in request.POST.keys() if k.startswith('review_example_')]
        form = ReviewsCheckingForm(request.POST, extra=len(review_fields))
        
        if form.is_valid():
            article_number = form.cleaned_data.get('article')
            cutoff_date = timezone.now() - datetime.timedelta(days=90)
            
            new_reviews = []
            for i in range(len(review_fields)):
                review = form.cleaned_data.get(f'review_example_{i}')
                if review:
                    new_reviews.append(review)
            logger.info(new_reviews)
            old_reviews = Review.objects.filter(article_number=article_number).filter(date__gt=cutoff_date)
            old_reviews_text = old_reviews.values_list('text', flat=True)
            old_reviews_text_list = list(old_reviews_text)
            
            for new_review in new_reviews:
                similarities = []
                for old_review in old_reviews_text_list:
                    if old_review:
                        similarity = calculate_similarity(new_review, old_review) * 100
                        logger.info(f"Similarity between texts: {similarity}")
                        if similarity is not None and similarity > 80:
                            similarities.append((similarity, old_review))
                
                results.append({
                    'review': new_review,
                    'is_unique': not similarities,
                    'similarities': similarities if similarities else []
                })
            
            return render(request, 'reviews/reviews_checking.html', {'form': form, 'results': results})
    else:
        form = ReviewsCheckingForm()
    
    return render(request, 'reviews/reviews_checking.html', {'form': form, 'results': results})