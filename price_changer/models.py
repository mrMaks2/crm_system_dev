from django.db import models

class Product_from_wb(models.Model):
    prod_art_from_wb = models.CharField(max_length=255, unique=True, verbose_name='Артикул товара с WB')
    price_with_discount_wb = models.IntegerField(null=True, blank=True, verbose_name='Цена с учетом скидки от кошелька')

    class Meta:
        verbose_name = "Товар с ВБ"
        verbose_name_plural = "Товары с ВБ"

    def __str__(self):
        return f'Товар с артикулом {self.prod_art_from_wb} с WB'
    
class Product_from_ozon(models.Model):
    prod_art_from_ozon = models.CharField(max_length=255, unique=True, verbose_name='Артикул товара с Ozon')
    price_with_discount_ozon = models.IntegerField(null=True, blank=True, verbose_name='Цена с учетом скидки от кошелька')
    price_ozon_s_be = models.IntegerField(null=True, blank=True, verbose_name='Цена, которая должна быть на Ozon')
    price_with_co_invest = models.IntegerField(null=True, blank=True, verbose_name='Цена с соинвестом')
    price_without_co_invest = models.IntegerField(null=True, blank=True, verbose_name='Цена без соинвеста')
    discount_co_invest = models.FloatField(null=True, blank=True, verbose_name='Скидка соинвеста')
    discount_ozon_with_wallet = models.FloatField(null=True, blank=True, verbose_name='Скидка кошелька Ozon')
    price_ozon_s_be_with_wallet = models.IntegerField(null=True, blank=True, verbose_name='Цена, которая должна быть с учетом скидки кошелька Ozon')
    price_ozon_s_be_with_co_invest = models.IntegerField(null=True, blank=True, verbose_name='Цена, которая должна быть с учетом соинвеста')

    class Meta:
        verbose_name = "Товар с Озона"
        verbose_name_plural = "Товары с Озон"

    def __str__(self):
        return f'Товар с артикулом {self.prod_art_from_ozon} с Ozon'