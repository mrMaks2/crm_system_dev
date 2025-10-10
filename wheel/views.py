import random
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import WheelSector, SpinResult

def wheel_page(request):
    """Представление для отображения страницы с колесом."""
    sectors = WheelSector.objects.filter(is_active=True)
    context = {
        'sectors': sectors,
    }
    return render(request, 'wheel/wheel.html', context)

@csrf_exempt  # Для простоты, в продакшене используйте более безопасный метод
@require_http_methods(["POST"])
@login_required
def spin_wheel_api(request):
    """API-представление для обработки вращения колеса."""
    
    # Получаем все активные сектора
    sectors = WheelSector.objects.filter(is_active=True)
    if not sectors.exists():
        return JsonResponse({'error': 'Нет активных секторов'}, status=400)
    
    # Подготавливаем списки для взвешенного случайного выбора
    choices = []
    weights = []
    for sector in sectors:
        choices.append(sector)
        weights.append(sector.weight)
    
    # Выбираем случайный сектор на основе веса
    winning_sector = random.choices(choices, weights=weights, k=1)[0]
    
    # Логируем результат
    SpinResult.objects.create(user=request.user, sector=winning_sector)
    
    # Возвращаем результат фронтенду
    return JsonResponse({
        'success': True,
        'winning_sector': {
            'id': winning_sector.id,
            'text': winning_sector.text,
            'color': winning_sector.color,
        }
    })