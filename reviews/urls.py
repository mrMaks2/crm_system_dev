from django.urls import path
from . import views

urlpatterns = [
    path('list/<str:article_number>/', views.review_list, name='review_list_with_number'),
    path('list/', views.review_list, name='review_list'),
    path('check/', views.reviews_checking, name='check'),
]