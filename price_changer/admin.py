from django.contrib import admin

from .models import Product_from_wb, Product_from_ozon

admin.site.register(Product_from_wb)
admin.site.register(Product_from_ozon)