from django.urls import path
from . import views

urlpatterns = [
    path('stocks_orders_report/', views.stocks_orders_report_async, name='stocks_orders_report'),
    path('check_task_status/<str:task_id>/', views.check_task_status, name='check_task_status'),
    path('clear_task_session/', views.clear_task_session, name='clear_task_session'),
]