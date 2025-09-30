from django.urls import path
from . import views

urlpatterns = [
    path('product_cards/', views.product_cards, name='product_cards'),
    path('update_product_card/', views.update_product_card, name='update_product_card'),
    path('upload_media_file/', views.upload_media_file, name='upload_media_file'),
    path('reorder_images/', views.reorder_images, name='reorder_images'),
]