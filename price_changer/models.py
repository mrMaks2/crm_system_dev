from django.db import models

class Product_from_wb(models.Model):
    prod_art_from_wb = models.CharField(max_length=255, unique=True, verbose_name='Артикул товара с WB')
    price_with_discount_wb = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена с учетом скидки от кошелька')

    def __str__(self):
        return f'Товар с артикулом {self.prod_art_from_wb} с WB'
    
class Product_from_ozon(models.Model):
    prod_art_from_ozon = models.CharField(max_length=255, unique=True, verbose_name='Артикул товара с Ozon')
    price_with_discount_ozon = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена с учетом скидки от кошелька')

    def __str__(self):
        return f'Товар с артикулом {self.prod_art_from_ozon} с Ozon'