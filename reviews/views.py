from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Review
from .forms import ReviewForm, HomeForm

def review_list(request, article_number):
    if article_number == 0:
        reviews = Review.objects.all()
        form = ReviewForm()
    else:
        reviews = Review.objects.filter(article_number=article_number)
        if request.method == 'POST':
            form = ReviewForm(request.POST)
            if form.is_valid():
                select_option = form.cleaned_data['my_dropdown']
                if select_option == 'prod_arg_form':
                    reviews = reviews.order_by('article_number')
                elif select_option == 'date_form':
                    reviews = reviews.order_by('date')
        else:
            form = ReviewForm()
    return render(request, 'review_list.html', {'form': form, 'reviews': reviews})

def home_list(request):
    article_number = request.GET.get('article_number')
    if article_number:
        return redirect('review_list', article_number=article_number)
    form = HomeForm()
    return render(request, 'index.html', {'form': form})