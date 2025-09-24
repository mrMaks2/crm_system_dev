from django.db import models

class Statics(models.Model):
    cab_num = models.IntegerField(null=True, blank=True, verbose_name="Номер кабинета")
    date = models.DateField(verbose_name='Дата')
    article_number = models.CharField(max_length=100, verbose_name='Артикул товара')
    avg_spp = models.FloatField(null=True, blank=True, verbose_name='Среднее значение СПП')
    adv_expenses = models.IntegerField(null=True, blank=True, verbose_name="Рекламные расходы")
    clicks_PK = models.IntegerField(null=True, blank=True, verbose_name="Клики по РК")
    views_PK = models.IntegerField(null=True, blank=True, verbose_name="Показы по РК")
    total_num_orders = models.IntegerField(null=True, blank=True, verbose_name="Общее количество заказов")
    total_sum_orders = models.IntegerField(null=True, blank=True, verbose_name="Общая сумма заказов")
    total_clicks = models.IntegerField(null=True, blank=True, verbose_name="Клики всего")
    total_basket = models.IntegerField(null=True, blank=True, verbose_name="Корзина всего")
    basket_PK = models.IntegerField(null=True, blank=True, verbose_name="Корзина из РК")
    orders_num_PK = models.IntegerField(null=True, blank=True, verbose_name="Количество заказов с РК")
    orders_sum_PK = models.IntegerField(null=True, blank=True, verbose_name="Сумма заказов с РК")
    buyouts_num = models.IntegerField(null=True, blank=True, verbose_name="Количество выкупов")
    buyouts_sum = models.IntegerField(null=True, blank=True, verbose_name="Сумма выкупов")
    views_AYK = models.IntegerField(null=True, blank=True, verbose_name="АУК показы")
    clicks_AYK = models.IntegerField(null=True, blank=True, verbose_name="АУК клики")
    basket_AYK = models.IntegerField(null=True, blank=True, verbose_name="АУК корзина")
    orders_AYK = models.IntegerField(null=True, blank=True, verbose_name="АУК заказы")
    cost_AYK = models.IntegerField(null=True, blank=True, verbose_name="АУК затраты")
    views_APK = models.IntegerField(null=True, blank=True, verbose_name="АРК показы")
    clicks_APK = models.IntegerField(null=True, blank=True, verbose_name="АРК клики")
    basket_APK = models.IntegerField(null=True, blank=True, verbose_name="АРК корзина")
    orders_APK = models.IntegerField(null=True, blank=True, verbose_name="АРК заказы")
    cost_APK = models.IntegerField(null=True, blank=True, verbose_name="АРК затраты")

    class Meta:
        verbose_name = "Статистика"
        verbose_name_plural = "Статистики"

    def __str__(self):
        return f"Статистика на {self.article_number} от {self.date}"