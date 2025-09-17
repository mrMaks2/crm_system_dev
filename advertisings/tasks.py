from celery import shared_task
import requests
import os
from dotenv import load_dotenv
from .models import Statics
import datetime
import logging
import uuid
import time
from collections import defaultdict
from .views import (
    make_batched_requests,
    process_api_data,
    process_zip_report
)
from .google_sheets import sheets_exporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('advertisings.tasks')

load_dotenv()
jwt_advertisings_cab1 = os.getenv('jwt_advertisings_cab1')
jwt_advertisings_cab2 = os.getenv('jwt_advertisings_cab2')
jwt_advertisings_cab3 = os.getenv('jwt_advertisings_cab3')

jwts_advertisings = [jwt_advertisings_cab1, jwt_advertisings_cab2, jwt_advertisings_cab3]

url_all_campaigns = 'https://advert-api.wildberries.ru/adv/v1/promotion/count' # GET
url_info_campaign_nmID = 'https://advert-api.wildberries.ru/adv/v1/promotion/adverts' # POST
url_info_campaign_stats = 'https://advert-api.wildberries.ru/adv/v3/fullstats' # GET
url_create_report = 'https://seller-analytics-api.wildberries.ru/api/v2/nm-report/downloads' # POST
url_orders = 'https://statistics-api.wildberries.ru/api/v1/supplier/orders' # GET

# @shared_task
def get_and_save_advertisings_stats():

    for jwt_advertisings in jwts_advertisings:

        headers_advertisings = {
            'Authorization':jwt_advertisings
        }

        cab_num = jwts_advertisings.index(jwt_advertisings) + 1

        random_uuid = uuid.uuid4()
        uuid_string = str(random_uuid)
        search_advertIds = []
        rack_advertIds = []

        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        date_start_str = yesterday.strftime('%Y-%m-%d')
        date_end_str = yesterday.strftime('%Y-%m-%d')

        orders_data = get_orders_data(date_start_str, headers_advertisings)
        avg_spp_by_date_article = calculate_avg_spp(orders_data)

        all_campaigns_response = requests.get(url_all_campaigns, headers=headers_advertisings)
        if all_campaigns_response.status_code != 200:
            logger.info(f"Статус ошибки: {all_campaigns_response.status_code}")
            return None
        all_campaigns_list = all_campaigns_response.json().get('adverts', [])

        for active_campaign in all_campaigns_list:
            if active_campaign['status'] == 9:
                if active_campaign['type'] == 9: # Поисковые кампании
                    for ids in active_campaign['advert_list']:
                        search_advertIds.append(ids['advertId'])
                elif active_campaign['type'] == 8: # Кампании на полке
                    for ids in active_campaign['advert_list']:
                        rack_advertIds.append(ids['advertId'])

        id_list = []

        for advert_id in search_advertIds:
            id_list.append(str(advert_id))
        
        for advert_id in rack_advertIds:
            id_list.append(str(advert_id))

        response = []

        for i in range(0, len(id_list), 100):

            batch = id_list[i:i+100]

            params_stats_response = {
                "ids": ','.join(batch),
                "beginDate": date_start_str,
                "endDate": date_end_str
            }
            
            results = requests.get(url_info_campaign_stats, headers=headers_advertisings, params=params_stats_response)
            time.sleep(60)
            
            if results.status_code == 200:
                response.extend(results.json())
            else:
                logger.warning(f'Ошибка №{results.status_code} при получении статистики: {results.json()}')
                return None

        search_campaign = []
        if search_advertIds:
            search_campaign = make_batched_requests(url_info_campaign_nmID, search_advertIds)

        rack_campaign = []
        if rack_advertIds:
            rack_campaign = make_batched_requests(url_info_campaign_nmID, rack_advertIds)

        # Собираем все артикулы для связи
        all_articles = set()
        article_advert_map = {}  # Маппинг артикул -> advertId
        
        for camp in search_campaign:
            if 'unitedParams' in camp and camp['unitedParams']:
                article_num = camp['unitedParams'][0]['nms'][0]
                all_articles.add(article_num)
                article_advert_map[camp['advertId']] = article_num
        
        for camp in rack_campaign:
            if 'autoParams' in camp:
                article_num = camp['autoParams']['nms'][0]
                all_articles.add(article_num)
                article_advert_map[camp['advertId']] = article_num

        for resp in response:
            advert_id = resp['advertId']
            if advert_id in article_advert_map:
                resp['article_number'] = article_advert_map[advert_id]

        params_for_creaete_report = {
                "id": uuid_string,
                "reportType": "DETAIL_HISTORY_REPORT",
                "userReportName": "Card report",
                "params": {
                    "nmIDs": [],
                    "startDate": date_start_str,
                    "endDate": date_end_str,
                    "timezone": "Europe/Moscow",
                    "aggregationLevel": "day",
                    "skipDeletedNm": False
                    }
            }
        
        create_response = requests.post(url_create_report, headers=headers_advertisings, json=params_for_creaete_report)
        if create_response.status_code != 200:
            logger.warning(f"Ошибка при создании отчета: {create_response.status_code}")
            logger.warning(f"Детали ошибки: {create_response.json().get('detail', 'Неизвестная ошибка')}")
            return None
        
        time.sleep(10)

        url_get_report = f'https://seller-analytics-api.wildberries.ru/api/v2/nm-report/downloads/file/{uuid_string}' # GET
        response_report = requests.get(url_get_report, headers=headers_advertisings)
        if response_report.status_code != 200:
            logger.warning(f"Ошибка при получении отчета: {response_report.status_code}")
            logger.warning(f"Детали ошибки: {response_report.json().get('detail', 'Неизвестная ошибка')}")
            report_json = None
        else:
            report_json = process_zip_report(response=response_report)
            logger.info(f"Данные отчета: {report_json[:1] if report_json else 'None'}")

        processed_data = process_api_data(
            response=response, 
            search_advertId=search_advertIds, 
            rack_advertId=rack_advertIds,
            report_data=report_json,
            all_articles=list(all_articles)
        )

        processed_data['response'] = response
        processed_data['report_data'] = report_json
        processed_data['search_advertId'] = search_advertIds
        processed_data['rack_advertId'] = rack_advertIds

        processed_data_with_spp = add_spp_to_processed_data(processed_data, avg_spp_by_date_article)

        # Сохраняем данные в модель Statics для всех дат
        save_to_statics_model(processed_data_with_spp, avg_spp_by_date_article, cab_num)

# @shared_task
def export_statistics_to_google_sheets():
    """Задача для экспорта статистики в Google Sheets"""
    try:
        # Используем безопасный метод
        success = sheets_exporter.export_statistics_to_sheets_safe(days_back=7)
        if success:
            logger.info("Данные успешно экспортированы в Google Sheets с заголовками")
        else:
            logger.warning("Не удалось экспортировать данные в Google Sheets")
        return success
    except Exception as e:
        logger.error(f"Ошибка при экспорте в Google Sheets: {e}")
        return False


def get_orders_data(date_from, headers_advertisings):
    """Получает данные о заказах с statistics API"""
    try:
        params = {
            "dateFrom": date_from
        }
        
        response = requests.get(url_orders, headers=headers_advertisings, params=params)
        
        if response.status_code == 200:
            orders = response.json()
            logger.info(f"Успешно получены данные о заказах: {len(orders)} записей")
            return orders
        else:
            logger.warning(f"Ошибка при получении заказов: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Ошибка в get_orders_data: {e}")
        return []
    
def calculate_avg_spp(orders_data):
    """Рассчитывает среднее значение SPP по датам и артикулам"""
    spp_by_date_article = defaultdict(list)
    
    for order in orders_data:
        try:
            # Извлекаем дату из поля date
            order_datetime = datetime.datetime.fromisoformat(order['date'].replace('Z', '+00:00'))
            order_date = order_datetime.strftime('%Y-%m-%d')
            nm_id = order['nmId']
            spp = order.get('spp', 0)
            
            if spp > 0:  # Учитываем только заказы с SPP
                spp_by_date_article[(order_date, nm_id)].append(spp)
                
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Ошибка при обработке заказа: {e}")
            continue
    
    # Рассчитываем среднее SPP для каждой комбинации дата-артикул
    avg_spp_results = {}
    for (date_str, article), spp_values in spp_by_date_article.items():
        if spp_values:
            avg_spp = sum(spp_values) / len(spp_values)
            avg_spp_results[(date_str, str(article))] = round(avg_spp, 2)
    
    logger.info(f"Рассчитано средних SPP для {len(avg_spp_results)} комбинаций дата-артикул")
    return avg_spp_results

def add_spp_to_processed_data(processed_data, avg_spp_data):
    """Добавляет данные о среднем SPP в processed_data для каждой даты"""
    daily_stats = processed_data.get('daily_stats', {})
    
    for date_str in processed_data.get('dates', []):
        date_stats = daily_stats.get(date_str, {})
        
        # Добавляем SPP для каждой категории (all, search, rack)
        for category in ['all', 'search', 'rack']:
            category_stats = date_stats.get(category, {})
            article_numbers = category_stats.get('article_numbers', [])
            
            # Рассчитываем средневзвешенное SPP для всех артикулов категории
            spp_values = []
            for article in article_numbers:
                spp_value = avg_spp_data.get((date_str, str(article)), 0)
                if spp_value > 0:
                    spp_values.append(spp_value)
            
            if spp_values:
                avg_spp_category = sum(spp_values) / len(spp_values)
                category_stats['avg_spp'] = round(avg_spp_category, 2)
            else:
                category_stats['avg_spp'] = 0
        
        # Также добавляем общее SPP для даты
        date_stats['avg_spp'] = date_stats.get('all', {}).get('avg_spp', 0)
    
    # Добавляем общие данные о SPP
    processed_data['avg_spp_data'] = avg_spp_data
    
    return processed_data

def save_to_statics_model(processed_data, avg_spp_data, cab_num):
    """Сохраняет данные в модель Statics для всех дат и всех артикулов"""
    try:
        dates = processed_data.get('dates', [])
        
        for date_str in dates:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Получаем все артикулы для этой даты
            daily_stats = processed_data.get('daily_stats', {}).get(date_str, {})
            all_articles = daily_stats.get('all', {}).get('article_numbers', [])
            
            logger.info(f"Обрабатываем дату {date_str}, артикулы: {all_articles}")
            
            for article in all_articles:
                article_str = str(article)
                # Получаем статистику для конкретного артикула и даты
                article_stats = get_article_stats_for_date(processed_data, article_str, date_str)
                
                if article_stats:
                    # Получаем среднее SPP для этой даты и артикула
                    avg_spp = avg_spp_data.get((date_str, article_str), 0)
                    article_stats['avg_spp'] = avg_spp
                    
                    # Логируем полученные данные для отладки
                    logger.info(f"Данные для артикула {article_str} на {date_str}: "
                               f"views={article_stats['views_PK']}, "
                               f"clicks={article_stats['clicks_PK']}, "
                               f"sum={article_stats['adv_expenses']}")
                    
                    # Проверяем, существует ли уже запись
                    existing_record = Statics.objects.filter(
                        cab_num=cab_num,
                        date=date_obj,
                        article_number=article_str
                    ).first()
                    
                    if existing_record:
                        update_existing_record(existing_record, article_stats)
                        logger.info(f"Обновлена запись для артикула {article_str} на дату {date_str}")
                    else:
                        create_new_record(date_obj, article_str, article_stats, cab_num)
                        logger.info(f"Создана запись для артикула {article_str} на дату {date_str}")
                else:
                    logger.warning(f"Не удалось получить статистику для артикула {article_str} на дату {date_str}")
    
    except Exception as e:
        logger.error(f"Ошибка при сохранении в модель Statics: {e}")
        import traceback
        logger.error(traceback.format_exc())

def get_article_stats_for_date(processed_data, article_number, date_str):
    """Извлекает статистику для конкретного артикула и даты"""
    # Получаем данные из response для конкретного артикула
    article_stats = defaultdict(int)
    article_search_stats = defaultdict(int)
    article_rack_stats = defaultdict(int)
    
    # Проходим по всем advert из response и собираем данные только для нужного артикула
    for advert in processed_data.get('response', []):
        if str(advert.get('article_number')) != article_number:
            continue
            
        advert_id = advert['advertId']
        
        # Ищем данные для этой даты
        for day in advert.get('days', []):
            day_date = day['date'].split('T')[0]
            if day_date != date_str:
                continue
                
            # Определяем тип кампании
            advert_type = 'search' if advert_id in processed_data.get('search_advertId', []) else 'rack'
            
            if advert_type == 'search':
                article_search_stats['views'] += day.get('views', 0)
                article_search_stats['clicks'] += day.get('clicks', 0)
                article_search_stats['sum'] += day.get('sum', 0)
                article_search_stats['orders'] += day.get('orders', 0)
                article_search_stats['sum_price'] += day.get('sum_price', 0)
                article_search_stats['addToCartCount'] += day.get('addToCartCount', 0)
                article_search_stats['ordersCount'] += day.get('ordersCount', 0)
                article_search_stats['ordersSumRub'] += day.get('ordersSumRub', 0)
                article_search_stats['atbs'] += day.get('atbs', 0)
                article_search_stats['canceled'] += day.get('canceled', 0)
            else:
                article_rack_stats['views'] += day.get('views', 0)
                article_rack_stats['clicks'] += day.get('clicks', 0)
                article_rack_stats['sum'] += day.get('sum', 0)
                article_rack_stats['orders'] += day.get('orders', 0)
                article_rack_stats['sum_price'] += day.get('sum_price', 0)
                article_rack_stats['addToCartCount'] += day.get('addToCartCount', 0)
                article_rack_stats['ordersCount'] += day.get('ordersCount', 0)
                article_rack_stats['ordersSumRub'] += day.get('ordersSumRub', 0)
                article_rack_stats['atbs'] += day.get('atbs', 0)
                article_rack_stats['canceled'] += day.get('canceled', 0)
    
    # Суммируем общую статистику
    article_stats['views'] = article_search_stats['views'] + article_rack_stats['views']
    article_stats['clicks'] = article_search_stats['clicks'] + article_rack_stats['clicks']
    article_stats['sum'] = article_search_stats['sum'] + article_rack_stats['sum']
    article_stats['orders'] = article_search_stats['orders'] + article_rack_stats['orders']
    article_stats['sum_price'] = article_search_stats['sum_price'] + article_rack_stats['sum_price']
    article_stats['addToCartCount'] = article_search_stats['addToCartCount'] + article_rack_stats['addToCartCount']
    article_stats['ordersCount'] = article_search_stats['ordersCount'] + article_rack_stats['ordersCount']
    article_stats['ordersSumRub'] = article_search_stats['ordersSumRub'] + article_rack_stats['ordersSumRub']
    article_stats['atbs'] = article_search_stats['atbs'] + article_rack_stats['atbs']
    article_stats['canceled'] = article_search_stats['canceled'] + article_rack_stats['canceled']
    
    # Получаем данные из отчета для конкретного артикула
    report_stats = defaultdict(int)
    for item in processed_data.get('report_data', []):
        dt_value = item.get('dt')
        if isinstance(dt_value, str):
            if 'T' in dt_value:
                item_date_str = dt_value.split('T')[0]
            else:
                item_date_str = dt_value
        elif hasattr(dt_value, 'strftime'):
            item_date_str = dt_value.strftime('%Y-%m-%d')
        else:
            continue
        
        if item_date_str == date_str and str(item.get('nmID')) == article_number:
            report_stats['openCardCount'] = item.get('openCardCount', 0)
            report_stats['addToCartCount'] = item.get('addToCartCount', 0)
            report_stats['ordersCount'] = item.get('ordersCount', 0)
            report_stats['ordersSumRub'] = item.get('ordersSumRub', 0)
            report_stats['buyoutsCount'] = item.get('buyoutsCount', 0)
            report_stats['buyoutsSumRub'] = item.get('buyoutsSumRub', 0)
            break
    
    return {
        'article_number': article_number,
        'adv_expenses': int(article_stats['sum']),
        'clicks_PK': int(article_stats['clicks']),
        'views_PK': int(article_stats['views']),
        'total_num_orders': int(report_stats['ordersCount']),
        'total_sum_orders': int(report_stats['ordersSumRub']),
        'total_clicks': int(report_stats['openCardCount']),
        'total_basket': int(report_stats['addToCartCount']),
        'basket_PK': int(article_stats['atbs']),
        'orders_num_PK': int(article_stats['orders']),
        'orders_sum_PK': int(article_stats['sum_price']),
        
        # Данные для поисковых кампаний
        'views_AYK': int(article_search_stats['views']),
        'clicks_AYK': int(article_search_stats['clicks']),
        'basket_AYK': int(article_search_stats['atbs']),
        'orders_AYK': int(article_search_stats['orders']),
        'cost_AYK': int(article_search_stats['sum']),
        
        # Данные для кампаний на полке
        'views_APK': int(article_rack_stats['views']),
        'clicks_APK': int(article_rack_stats['clicks']),
        'basket_APK': int(article_rack_stats['atbs']),
        'orders_APK': int(article_rack_stats['orders']),
        'cost_APK': int(article_rack_stats['sum']),
        
        # # Данные из отчета
        # 'openCardCount': report_stats['openCardCount'],
        # 'buyoutsCount': report_stats['buyoutsCount'],
        # 'buyoutsSumRub': report_stats['buyoutsSumRub']
    }

def update_existing_record(record, stats):
    """Обновляет существующую запись в базе данных"""
    record.adv_expenses = stats['adv_expenses']
    record.clicks_PK = stats['clicks_PK']
    record.views_PK = stats['views_PK']
    record.total_num_orders = stats['total_num_orders']
    record.total_sum_orders = stats['total_sum_orders']
    record.total_clicks = stats['total_clicks']
    record.total_basket = stats['total_basket']
    record.basket_PK = stats['basket_PK']
    record.orders_num_PK = stats['orders_num_PK']
    record.orders_sum_PK = stats['orders_sum_PK']
    record.views_AYK = stats['views_AYK']
    record.clicks_AYK = stats['clicks_AYK']
    record.basket_AYK = stats['basket_AYK']
    record.orders_AYK = stats['orders_AYK']
    record.cost_AYK = stats['cost_AYK']
    record.views_APK = stats['views_APK']
    record.clicks_APK = stats['clicks_APK']
    record.basket_APK = stats['basket_APK']
    record.orders_APK = stats['orders_APK']
    record.cost_APK = stats['cost_APK']
    record.avg_spp = stats.get('avg_spp', 0)
    record.save()

def create_new_record(date_obj, article_number, stats, cab_num):
    """Создает новую запись в базе данных"""
    Statics.objects.create(
        cab_num=cab_num,
        date=date_obj,
        article_number=article_number,
        adv_expenses=stats['adv_expenses'],
        clicks_PK=stats['clicks_PK'],
        views_PK=stats['views_PK'],
        total_num_orders=stats['total_num_orders'],
        total_sum_orders=stats['total_sum_orders'],
        total_clicks=stats['total_clicks'],
        total_basket=stats['total_basket'],
        basket_PK=stats['basket_PK'],
        orders_num_PK=stats['orders_num_PK'],
        orders_sum_PK=stats['orders_sum_PK'],
        views_AYK=stats['views_AYK'],
        clicks_AYK=stats['clicks_AYK'],
        basket_AYK=stats['basket_AYK'],
        orders_AYK=stats['orders_AYK'],
        cost_AYK=stats['cost_AYK'],
        views_APK=stats['views_APK'],
        clicks_APK=stats['clicks_APK'],
        basket_APK=stats['basket_APK'],
        orders_APK=stats['orders_APK'],
        cost_APK=stats['cost_APK'],
        avg_spp=stats.get('avg_spp', 0)
    )