from django.db import models
from django.contrib.auth.models import User

class WheelSector(models.Model):
    """Модель для сектора на колесе фортуны."""
    text = models.CharField(max_length=255, verbose_name="Текст на секторе")
    weight = models.PositiveIntegerField(default=1, verbose_name="Вес (вероятность)")
    # Для цветов можно хранить hex-код, чтобы фронтенд мог его использовать.
    color = models.CharField(max_length=7, default='#FFFFFF', verbose_name="Цвет (HEX)")
    is_active = models.BooleanField(default=True, verbose_name="Активный сектор")

    class Meta:
        verbose_name = "Сектор колеса"
        verbose_name_plural = "Сектора колеса"

    def __str__(self):
        return f"{self.text} (Вес: {self.weight})"

class SpinResult(models.Model):
    """Модель для логирования результатов вращений."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    sector = models.ForeignKey(WheelSector, on_delete=models.CASCADE, verbose_name="Выигранный сектор")
    spin_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата и время вращения")

    class Meta:
        verbose_name = "Результат вращения"
        verbose_name_plural = "Результаты вращений"

    def __str__(self):
        return f"{self.user.username} - {self.sector.text}"