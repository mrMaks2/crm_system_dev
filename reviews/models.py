from django.db import models

class Review(models.Model):
    review_id = models.CharField(max_length=100, verbose_name='ID отзыва')
    article_number = models.CharField(max_length=100, verbose_name='Артикул товара')
    author = models.CharField(max_length=255, null=True, verbose_name="Автор")
    rating = models.IntegerField(null=True, verbose_name="Рейтинг")
    text = models.TextField(null=True, verbose_name='Текст отзыва')
    date = models.DateTimeField(verbose_name='Дата создания отзыва')

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"

    def __str__(self):
        return f"Отзыв на {self.article_number} от {self.date}"