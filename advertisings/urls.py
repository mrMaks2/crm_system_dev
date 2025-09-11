from django.urls import path
from . import views

urlpatterns = [
    path('campaign_analysis/', views.advertisings_analysis, name='campaign_analysis'),
    path('keywords_analysis/', views.keywords_analysis, name='keywords_analysis'),
]