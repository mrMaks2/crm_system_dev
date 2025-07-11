from django.urls import path
from . import views

urlpatterns = [
    path('list/<str:article_number>/', views.review_list, name='review_list'),
    path('home', views.home_list, name='home_list'),
]