from django.urls import path
from . import views

urlpatterns = [
    path('wheel/', views.wheel_page, name='wheel_page'),
    path('api/spin-wheel/', views.spin_wheel_api, name='spin_wheel_api'),
]