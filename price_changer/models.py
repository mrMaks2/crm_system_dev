from django.db import models

class Product_from_wb(models.Model):
    prod_art_from_wb = models.CharField(max_length=255, unique=True, verbose_name='Артикул товара с WB')
    price_with_discount_wb = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, verbose_name='Цена с учетом скидки от кошелька')


    def __str__(self):
        return f'Товар с артикулом {self.prod_art_from_wb} с WB'
    
class Product_from_ozon(models.Model):
    prod_art_from_ozon = models.CharField(max_length=255, unique=True, verbose_name='Артикул товара с Ozon')
    price_with_discount_ozon = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, verbose_name='Цена с учетом скидки от кошелька')
    price_ozon_s_be = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, verbose_name='Цена, которая должна быть на Ozon')
    price_with_co_invest = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, verbose_name='Цена с соинвестом')
    price_without_co_invest = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, verbose_name='Цена без соинвеста')
    discount_co_invest = models.IntegerField(max_length=10, null=True, blank=True, verbose_name='Скидка соинвеста')
    discount_ozon_with_wallet = models.IntegerField(max_length=10, null=True, blank=True, verbose_name='Скидка кошелька Ozon')
    price_ozon_s_be_with_wallet = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, verbose_name='Цена, которая должна быть с учетом скидки кошелька Ozon')
    price_ozon_s_be_with_co_invest = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True, verbose_name='Цена, которая должна быть с учетом соинвеста')

    def __str__(self):
        return f'Товар с артикулом {self.prod_art_from_ozon} с Ozon'