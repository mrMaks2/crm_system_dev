from django import template
from datetime import datetime
from collections import OrderedDict

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def format_date_string(value):
    """Форматирует дату из формата YYYY-MM-DD в DD.MM.YYYY"""
    if not value:
        return "..."
    try:
        # Если значение уже datetime объект
        if isinstance(value, datetime):
            return value.strftime("%d.%m.%Y")
        # Если это строка
        return datetime.strptime(str(value), "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(value)
    
@register.filter
def div(value, arg):
    """Деление значения на аргумент"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def mul(value, arg):
    """Умножение значения на аргумент"""
    try:
        return float(value) * float(arg)
    except ValueError:
        return 0
    
@register.filter
def multiply(value, arg):
    """Умножает значение на аргумент"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0
    
@register.filter
def get_cluster_color(cluster_name):
    """Возвращает выразительный цвет для кластера (для заголовков)"""
    colors = {
        'Центральный': '#FF6B6B',           # Яркий красный
        'Приволжский': '#4ECDC4',           # Бирюзовый
        'Южный + Северо-Кавказский': '#45B7D1', # Яркий голубой
        'Уральский': '#96CEB4',             # Мятный зеленый
        'Северо-Западный': '#FFEAA7',       # Яркий желтый
        'Казахстан': '#DDA0DD',             # Сливовый
        'Дальневосточный + Сибирский': '#98D8C8', # Зеленый океан
        'Беларусь': '#F7DC6F',              # Золотистый
        'Армения': '#BB8FCE',               # Фиолетовый
        'Грузия': '#85C1E9',                # Небесно-голубой
        'Узбекистан': '#F8C471'             # Оранжевый
    }
    return colors.get(cluster_name, '#F8F9FA')

@register.filter
def get_cluster_color_light(cluster_name):
    """Возвращает светлый цвет для кластера (для ячеек)"""
    colors = {
        'Центральный': '#FFE5E5',           # Светло-красный
        'Приволжский': '#E0F7FA',           # Светло-бирюзовый
        'Южный + Северо-Кавказский': '#E3F2FD', # Светло-голубой
        'Уральский': '#E8F5E8',             # Светло-зеленый
        'Северо-Западный': '#FFFDE7',       # Светло-желтый
        'Казахстан': '#F3E5F5',             # Светло-фиолетовый
        'Дальневосточный + Сибирский': '#E0F2F1', # Светло-морской
        'Беларусь': '#FFF9C4',              # Светло-золотой
        'Армения': '#F3E5F5',               # Светло-лавандовый
        'Грузия': '#E1F5FE',                # Светло-небесный
        'Узбекистан': '#FFF3E0'             # Светло-оранжевый
    }
    return colors.get(cluster_name, '#FFFFFF')