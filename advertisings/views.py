import time
from django.shortcuts import render
from django.utils.dateparse import parse_date
import requests
import os
from dotenv import load_dotenv
import logging
from .forms import CampaignAnalysisForm, KeywordsAnalysisForm
import pandas as pd
import zipfile
from io import BytesIO
import uuid
from django.core.cache import cache
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('advertisings_views')

load_dotenv()
jwt_advertisings = os.getenv('jwt_advertisings_cab1')

headers_advertisings = {
        'Authorization':jwt_advertisings
    }

url_all_campaigns = 'https://advert-api.wildberries.ru/adv/v1/promotion/count' # GET
url_info_campaign_nmID = 'https://advert-api.wildberries.ru/adv/v1/promotion/adverts' # POST
url_info_campaign_stats = 'https://advert-api.wildberries.ru/adv/v3/fullstats' # GET
url_create_report = 'https://seller-analytics-api.wildberries.ru/api/v2/nm-report/downloads' # POST
url_keywords_stats = 'https://seller-analytics-api.wildberries.ru/api/v2/search-report/product/search-texts' # POST
url_keywords_stats_2 = 'https://advert-api.wildberries.ru/adv/v0/stats/keywords' # GET

def advertisings_analysis(request):
    if request.method == 'POST':
        form = CampaignAnalysisForm(request.POST)
        if form.is_valid():

            search_advertIds = []
            rack_advertIds = []
            article_number = form.cleaned_data.get('article', '').strip()
            date_start = form.cleaned_data.get('date_start')
            date_end = form.cleaned_data.get('date_end')

            date_start_str = date_start.strftime('%Y-%m-%d')
            date_end_str = date_end.strftime('%Y-%m-%d')

            cache_key = f"report_{date_start_str}_{date_end_str}"
            
            cached_report_uuid = cache.get(cache_key)
            
            if cached_report_uuid:
                uuid_string = cached_report_uuid
                logger.info(f"Используем закешированный отчет с UUID: {uuid_string}")
            else:
                random_uuid = uuid.uuid4()
                uuid_string = str(random_uuid)
                logger.info(f"Создаем новый отчет с UUID: {uuid_string}")

            all_campaigns_response = requests.get(url_all_campaigns, headers=headers_advertisings)
            if all_campaigns_response.status_code != 200:
                return render(request, 'advertisings/campaign_analysis.html', {
                    'form': form,
                    'error': f'Ошибка №{all_campaigns_response.status_code} при получении данных о кампаниях'
                })
            all_campaigns_list = all_campaigns_response.json().get('adverts', [])

            for active_campaign in all_campaigns_list:
                if active_campaign['status'] == 7 or active_campaign['status'] == 9 or active_campaign['status'] == 11:
                    if active_campaign['type'] == 9: # Поисковые кампании
                        for ids in active_campaign['advert_list']:
                            search_advertIds.append(ids['advertId'])
                    elif active_campaign['type'] == 8: # Кампании на полке
                        for ids in active_campaign['advert_list']:
                            rack_advertIds.append(ids['advertId'])

            search_campaign = []
            if search_advertIds:
                search_campaign = make_batched_requests(url_info_campaign_nmID, search_advertIds)

            rack_campaign = []
            if rack_advertIds:
                rack_campaign = make_batched_requests(url_info_campaign_nmID, rack_advertIds)

            search_advertId = []
            rack_advertId = []

            for camp in search_campaign:
                if camp['unitedParams'][0]['nms'][0] == int(article_number):
                    search_advertId.append(camp['advertId'])
            for camp in rack_campaign:
                if camp['autoParams']['nms'][0] == int(article_number):
                    rack_advertId.append(camp['advertId'])

            id_list = []

            for advert_id in search_advertId:
                id_list.append(str(advert_id))
            
            for advert_id in rack_advertId:
                id_list.append(str(advert_id))

            params = {
                "ids": ','.join(id_list),
                "beginDate": date_start_str,
                "endDate": date_end_str
            }
            
            stats_response = requests.get(url_info_campaign_stats, headers=headers_advertisings, params=params)
            
            if stats_response.status_code != 200:
                logger.warning(f'Ошибка №{stats_response.status_code} при получении статистики: {stats_response.json()}')
                return render(request, 'advertisings/campaign_analysis.html', {
                    'form': form,
                    'error': f'Ошибка №{stats_response.status_code} при получении статистики'
                })
            
            response = stats_response.json()
            
            if not cached_report_uuid:

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
                else:
                    # Кешируем на 48 часов (столько хранится отчет в базе WB API)
                    cache.set(cache_key, uuid_string, 48 * 60 * 60)
                    time.sleep(2)
                    logger.info(f"Отчет создан и закеширован с ключом: {cache_key}")

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
                search_advertId=search_advertId, 
                rack_advertId=rack_advertId,
                report_data=report_json,
                article_number=article_number
            )
    
            context = {
                'form': form,
                'stats_data': processed_data,
                'total_interval': f"{date_start_str} — {date_end_str}",
                'art_prod': article_number
            }
            
            return render(request, 'advertisings/campaign_analysis.html', context)
    form = CampaignAnalysisForm()
    context = {'form': form}
    return render(request, 'advertisings/campaign_analysis.html', context)

def make_batched_requests(url, advert_ids):
    results = []
    for i in range(0, len(advert_ids), 50):
        batch = advert_ids[i:i+50]
        response = requests.post(url, headers=headers_advertisings, json=batch)
        if response.status_code == 200:
            results.extend(response.json())
        else:
            logger.warning(f"Ошибка при запросе пакета {i//50 + 1}: {response.status_code}")
    return results

def process_api_data(response, search_advertId, rack_advertId, report_data=None, article_number=None, all_articles=None):
    
    # Группируем данные по датам
    dates_data = {}
    
    # Собираем все уникальные даты
    all_dates = set()
    for advert in response:
        for day in advert['days']:
            date_str = day['date'].split('T')[0]
            all_dates.add(date_str)
    
    # Сортируем даты в обратном порядке
    sorted_dates = sorted(all_dates, reverse=True)
    
    # Создаем структуру данных для каждой даты
    for date_str in sorted_dates:
        search_adverts = {advert_id: None for advert_id in search_advertId}
        rack_adverts = {advert_id: None for advert_id in rack_advertId}
        
        dates_data[date_str] = {
            'date': date_str,
            'day_name': get_day_name(date_str),
            'adverts': {
                'search': search_adverts,
                'rack': rack_adverts
            }
        }
    
    # Заполняем данные для каждого advertId в зависимости от РК
    for advert in response:
        advert_id = advert['advertId']
        advert_type = 'search' if advert_id in search_advertId else 'rack'
        
        for day in advert['days']:
            date_str = day['date'].split('T')[0]
            if date_str in dates_data:
                dates_data[date_str]['adverts'][advert_type][advert_id] = day
    
    # Обрабатываем данные из отчета
    report_stats = {}
    if report_data and article_number:
        article_num = int(article_number)
        for item in report_data:
            if item['nmID'] == article_num:
                # Обрабатываем разные форматы даты
                dt_value = item['dt']
                if isinstance(dt_value, str):
                    if 'T' in dt_value:
                        date_str = dt_value.split('T')[0]
                    else:
                        date_str = dt_value
                elif hasattr(dt_value, 'strftime'):
                    date_str = dt_value.strftime('%Y-%m-%d')
                else:
                    continue
                    
                report_stats[date_str] = {
                    'openCardCount': item.get('openCardCount', 0),
                    'addToCartCount': item.get('addToCartCount', 0),
                    'ordersCount': item.get('ordersCount', 0),
                    'ordersSumRub': item.get('ordersSumRub', 0),
                    'buyoutsCount': item.get('buyoutsCount', 0),
                    'buyoutsSumRub': item.get('buyoutsSumRub', 0)
                }
    elif article_number == None:
        for item in report_data:
            dt_value = item['dt']
            if isinstance(dt_value, str):
                if 'T' in dt_value:
                    date_str = dt_value.split('T')[0]
                else:
                    date_str = dt_value
            elif hasattr(dt_value, 'strftime'):
                date_str = dt_value.strftime('%Y-%m-%d')
                
            report_stats[date_str] = {
                'openCardCount': item.get('openCardCount', 0),
                'addToCartCount': item.get('addToCartCount', 0),
                'ordersCount': item.get('ordersCount', 0),
                'ordersSumRub': item.get('ordersSumRub', 0),
                'buyoutsCount': item.get('buyoutsCount', 0),
                'buyoutsSumRub': item.get('buyoutsSumRub', 0)
            }

    # Создаем структуру для ежедневной статистики - ИНИЦИАЛИЗИРУЕМ ПРЕЖДЕ ЧЕМ ИСПОЛЬЗОВАТЬ
    daily_stats = {}
    totals = {
        'all': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0,
                'openCardCount': 0, 'addToCartCount': 0, 'ordersCount': 0, 'ordersSumRub': 0,
                'buyoutsCount': 0, 'buyoutsSumRub': 0, 'atbs': 0, 'canceled': 0},
        'search': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0,
                  'openCardCount': 0, 'addToCartCount': 0, 'ordersCount': 0, 'ordersSumRub': 0,
                  'buyoutsCount': 0, 'buyoutsSumRub': 0, 'atbs': 0, 'canceled': 0},
        'rack': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0,
                'openCardCount': 0, 'addToCartCount': 0, 'ordersCount': 0, 'ordersSumRub': 0,
                'buyoutsCount': 0, 'buyoutsSumRub': 0, 'atbs': 0, 'canceled': 0}
    }

    # Инициализируем daily_stats для каждой даты
    for date_str in sorted_dates:
        daily_stats[date_str] = {
            'all': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0,
                   'openCardCount': 0, 'addToCartCount': 0, 'ordersCount': 0, 'ordersSumRub': 0,
                   'buyoutsCount': 0, 'buyoutsSumRub': 0, 'atbs': 0, 'canceled': 0,
                   'article_numbers': []},
            'search': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0,
                     'openCardCount': 0, 'addToCartCount': 0, 'ordersCount': 0, 'ordersSumRub': 0,
                     'buyoutsCount': 0, 'buyoutsSumRub': 0, 'atbs': 0, 'canceled': 0,
                     'article_numbers': []},
            'rack': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0,
                   'openCardCount': 0, 'addToCartCount': 0, 'ordersCount': 0, 'ordersSumRub': 0,
                   'buyoutsCount': 0, 'buyoutsSumRub': 0, 'atbs': 0, 'canceled': 0,
                   'article_numbers': []}
        }

    date_articles = defaultdict(set)
    
    # Заполняем article_number для каждого advertId
    for advert in response:
        advert_id = advert['advertId']
        article_num = advert.get('article_number')
        
        if article_num:
            for day in advert['days']:
                date_str = day['date'].split('T')[0]
                date_articles[date_str].add(article_num)
    
    # Добавляем article_number в daily_stats
    for date_str in sorted_dates:
        articles_for_date = list(date_articles.get(date_str, []))
        
        # Если переданы все артикулы, используем их
        if all_articles and not articles_for_date:
            articles_for_date = all_articles
        
        # Теперь daily_stats[date_str] гарантированно существует
        daily_stats[date_str]['all']['article_numbers'] = articles_for_date
        daily_stats[date_str]['search']['article_numbers'] = articles_for_date
        daily_stats[date_str]['rack']['article_numbers'] = articles_for_date
    
    for date_str in sorted_dates:
        date_info = dates_data[date_str]
        
        # Суммируем данные по всем поисковым кампаниям
        search_views = 0
        search_clicks = 0
        search_sum = 0
        search_orders = 0
        search_sum_price = 0
        search_atbs = 0
        search_canceled = 0
        
        for advert_data in date_info['adverts']['search'].values():
            if advert_data:
                search_views += advert_data.get('views', 0)
                search_clicks += advert_data.get('clicks', 0)
                search_sum += advert_data.get('sum', 0)
                search_orders += advert_data.get('orders', 0)
                search_sum_price += advert_data.get('sum_price', 0)
                search_atbs += advert_data.get('atbs', 0)
                search_canceled += advert_data.get('canceled', 0)
        
        # Суммируем данные по всем кампаниям на полке
        rack_views = 0
        rack_clicks = 0
        rack_sum = 0
        rack_orders = 0
        rack_sum_price = 0
        rack_atbs = 0
        rack_canceled = 0
        
        for advert_data in date_info['adverts']['rack'].values():
            if advert_data:
                rack_views += advert_data.get('views', 0)
                rack_clicks += advert_data.get('clicks', 0)
                rack_sum += advert_data.get('sum', 0)
                rack_orders += advert_data.get('orders', 0)
                rack_sum_price += advert_data.get('sum_price', 0)
                rack_atbs += advert_data.get('atbs', 0)
                rack_canceled += advert_data.get('canceled', 0)
        
        # Данные из отчета
        report_data_day = report_stats.get(date_str, {})
        open_card_count = report_data_day.get('openCardCount', 0)
        add_to_cart_count = report_data_day.get('addToCartCount', 0)
        orders_count = report_data_day.get('ordersCount', 0)
        orders_sum_rub = report_data_day.get('ordersSumRub', 0)
        buyouts_count = report_data_day.get('buyoutsCount', 0)
        buyouts_sum_rub = report_data_day.get('buyoutsSumRub', 0)
        
        # Общие данные за день
        all_views = rack_views + search_views
        all_clicks = rack_clicks + search_clicks
        all_sum = rack_sum + search_sum
        all_orders = rack_orders + search_orders
        all_sum_price = rack_sum_price + search_sum_price
        all_atbs = rack_atbs + search_atbs
        all_canceled = rack_canceled + search_canceled
        
        # Рассчитываем метрики за сутки
        rack_ctr = (rack_clicks / rack_views * 100) if rack_views > 0 else 0
        search_ctr = (search_clicks / search_views * 100) if search_views > 0 else 0
        all_ctr = (all_clicks / all_views * 100) if all_views > 0 else 0
        
        rack_cpc = (rack_sum / rack_clicks) if rack_clicks > 0 else 0
        search_cpc = (search_sum / search_clicks) if search_clicks > 0 else 0
        all_cpc = (all_sum / all_clicks) if all_clicks > 0 else 0
        
        rack_cr = (rack_orders / rack_clicks * 100) if rack_clicks > 0 else 0
        search_cr = (search_orders / search_clicks * 100) if search_clicks > 0 else 0
        all_cr = (all_orders / all_clicks * 100) if all_clicks > 0 else 0
        
        # Рассчитываем CPO
        rack_cpo = (rack_sum / rack_orders) if rack_orders > 0 else 0
        search_cpo = (search_sum / search_orders) if search_orders > 0 else 0
        all_cpo = (all_sum / all_orders) if all_orders > 0 else 0
        
        # Рассчитываем метрики из отчета
        cr1 = (add_to_cart_count / open_card_count * 100) if open_card_count > 0 else 0
        cr2 = (orders_count / add_to_cart_count * 100) if add_to_cart_count > 0 else 0
        drrz = (all_sum / orders_sum_rub * 100) if orders_sum_rub > 0 else 0
        
        rack_data = {
            'views': rack_views,
            'clicks': rack_clicks,
            'ctr': round(rack_ctr, 2),
            'cpc': round(rack_cpc, 2),
            'cpo': round(rack_cpo, 2),
            'sum': round(rack_sum, 2),
            'orders': rack_orders,
            'cr': round(rack_cr, 2),
            'sum_price': round(rack_sum_price, 2),
            'openCardCount': open_card_count,
            'addToCartCount': add_to_cart_count,
            'ordersCount': orders_count,
            'ordersSumRub': round(orders_sum_rub, 2),
            'buyoutsCount': buyouts_count,
            'buyoutsSumRub': round(buyouts_sum_rub, 2),
            'cr1': round(cr1, 2),
            'cr2': round(cr2, 2),
            'drrz': round(drrz, 2),
            'atbs': rack_atbs,
            'canceled': rack_canceled
        }
        
        search_data = {
            'views': search_views,
            'clicks': search_clicks,
            'ctr': round(search_ctr, 2),
            'cpc': round(search_cpc, 2),
            'cpo': round(search_cpo, 2),
            'sum': round(search_sum, 2),
            'orders': search_orders,
            'cr': round(search_cr, 2),
            'sum_price': round(search_sum_price, 2),
            'openCardCount': open_card_count,
            'addToCartCount': add_to_cart_count,
            'ordersCount': orders_count,
            'ordersSumRub': round(orders_sum_rub, 2),
            'buyoutsCount': buyouts_count,
            'buyoutsSumRub': round(buyouts_sum_rub, 2),
            'cr1': round(cr1, 2),
            'cr2': round(cr2, 2),
            'drrz': round(drrz, 2),
            'atbs': search_atbs,
            'canceled': search_canceled
        }
        
        all_data = {
            'views': all_views,
            'clicks': all_clicks,
            'ctr': round(all_ctr, 2),
            'cpc': round(all_cpc, 2),
            'cpo': round(all_cpo, 2),
            'sum': round(all_sum, 2),
            'orders': all_orders,
            'cr': round(all_cr, 2),
            'sum_price': round(all_sum_price, 2),
            'openCardCount': open_card_count,
            'addToCartCount': add_to_cart_count,
            'ordersCount': orders_count,
            'ordersSumRub': round(orders_sum_rub, 2),
            'buyoutsCount': buyouts_count,
            'buyoutsSumRub': round(buyouts_sum_rub, 2),
            'cr1': round(cr1, 2),
            'cr2': round(cr2, 2),
            'drrz': round(drrz, 2),
            'atbs': all_atbs,
            'canceled': all_canceled
        }
        
        # Обновляем daily_stats вместо перезаписи
        daily_stats[date_str]['all'].update(all_data)
        daily_stats[date_str]['search'].update(search_data)
        daily_stats[date_str]['rack'].update(rack_data)
        
        # Обновляем общие итоги
        for key in ['views', 'clicks', 'sum', 'orders', 'sum_price', 
                   'openCardCount', 'addToCartCount', 'ordersCount', 'ordersSumRub',
                   'buyoutsCount', 'buyoutsSumRub', 'atbs', 'canceled']:
            totals['all'][key] += all_data[key]
            totals['search'][key] += search_data[key]
            totals['rack'][key] += rack_data[key]
    
    # Рассчитываем метрики за весь интервал
    # CTR, CPC, CR, CPO
    all_ctr_total = (totals['all']['clicks'] / totals['all']['views'] * 100) if totals['all']['views'] > 0 else 0
    all_cpc_total = (totals['all']['sum'] / totals['all']['clicks']) if totals['all']['clicks'] > 0 else 0
    all_cr_total = (totals['all']['orders'] / totals['all']['clicks'] * 100) if totals['all']['clicks'] > 0 else 0
    all_cpo_total = (totals['all']['sum'] / totals['all']['orders']) if totals['all']['orders'] > 0 else 0
    
    search_ctr_total = (totals['search']['clicks'] / totals['search']['views'] * 100) if totals['search']['views'] > 0 else 0
    search_cpc_total = (totals['search']['sum'] / totals['search']['clicks']) if totals['search']['clicks'] > 0 else 0
    search_cr_total = (totals['search']['orders'] / totals['search']['clicks'] * 100) if totals['search']['clicks'] > 0 else 0
    search_cpo_total = (totals['search']['sum'] / totals['search']['orders']) if totals['search']['orders'] > 0 else 0
    
    rack_ctr_total = (totals['rack']['clicks'] / totals['rack']['views'] * 100) if totals['rack']['views'] > 0 else 0
    rack_cpc_total = (totals['rack']['sum'] / totals['rack']['clicks']) if totals['rack']['clicks'] > 0 else 0
    rack_cr_total = (totals['rack']['orders'] / totals['rack']['clicks'] * 100) if totals['rack']['clicks'] > 0 else 0
    rack_cpo_total = (totals['rack']['sum'] / totals['rack']['orders']) if totals['rack']['orders'] > 0 else 0
    
    # Метрики из отчета для всего интервала
    all_cr1_total = (totals['all']['addToCartCount'] / totals['all']['openCardCount'] * 100) if totals['all']['openCardCount'] > 0 else 0
    all_cr2_total = (totals['all']['ordersCount'] / totals['all']['addToCartCount'] * 100) if totals['all']['addToCartCount'] > 0 else 0
    all_drrz_total = (totals['all']['sum'] / totals['all']['ordersSumRub'] * 100) if totals['all']['ordersSumRub'] > 0 else 0
    
    search_cr1_total = (totals['search']['addToCartCount'] / totals['search']['openCardCount'] * 100) if totals['search']['openCardCount'] > 0 else 0
    search_cr2_total = (totals['search']['ordersCount'] / totals['search']['addToCartCount'] * 100) if totals['search']['addToCartCount'] > 0 else 0
    search_drrz_total = (totals['search']['sum'] / totals['search']['ordersSumRub'] * 100) if totals['search']['ordersSumRub'] > 0 else 0
    
    rack_cr1_total = (totals['rack']['addToCartCount'] / totals['rack']['openCardCount'] * 100) if totals['rack']['openCardCount'] > 0 else 0
    rack_cr2_total = (totals['rack']['ordersCount'] / totals['rack']['addToCartCount'] * 100) if totals['rack']['addToCartCount'] > 0 else 0
    rack_drrz_total = (totals['rack']['sum'] / totals['rack']['ordersSumRub'] * 100) if totals['rack']['ordersSumRub'] > 0 else 0
    
    # Добавляем рассчитанные метрики к итогам
    totals['all'].update({
        'ctr': round(all_ctr_total, 2),
        'cpc': round(all_cpc_total, 2),
        'cr': round(all_cr_total, 2),
        'cpo': round(all_cpo_total, 2),
        'cr1': round(all_cr1_total, 2),
        'cr2': round(all_cr2_total, 2),
        'drrz': round(all_drrz_total, 2),
        'sum': round(totals['all']['sum'], 2),
        'sum_price': round(totals['all']['sum_price'], 2),
        'ordersSumRub': round(totals['all']['ordersSumRub'], 2),
        'buyoutsSumRub': round(totals['all']['buyoutsSumRub'], 2)
    })
    
    totals['search'].update({
        'ctr': round(search_ctr_total, 2),
        'cpc': round(search_cpc_total, 2),
        'cr': round(search_cr_total, 2),
        'cpo': round(search_cpo_total, 2),
        'cr1': round(search_cr1_total, 2),
        'cr2': round(search_cr2_total, 2),
        'drrz': round(search_drrz_total, 2),
        'sum': round(totals['search']['sum'], 2),
        'sum_price': round(totals['search']['sum_price'], 2),
        'ordersSumRub': round(totals['search']['ordersSumRub'], 2),
        'buyoutsSumRub': round(totals['search']['buyoutsSumRub'], 2)
    })
    
    totals['rack'].update({
        'ctr': round(rack_ctr_total, 2),
        'cpc': round(rack_cpc_total, 2),
        'cr': round(rack_cr_total, 2),
        'cpo': round(rack_cpo_total, 2),
        'cr1': round(rack_cr1_total, 2),
        'cr2': round(rack_cr2_total, 2),
        'drrz': round(rack_drrz_total, 2),
        'sum': round(totals['rack']['sum'], 2),
        'sum_price': round(totals['rack']['sum_price'], 2),
        'ordersSumRub': round(totals['rack']['ordersSumRub'], 2),
        'buyoutsSumRub': round(totals['rack']['buyoutsSumRub'], 2)
    })
    
    return {
        'dates': sorted_dates,
        'dates_data': dates_data,
        'daily_stats': daily_stats,
        'totals': totals,
        'all_articles': list(all_articles) if all_articles else []
    }

def get_day_name(date_str):
    date_obj = parse_date(date_str)
    days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    return days[date_obj.weekday()]

def process_zip_report(response):
    logger.info(f"Content-Type: {response.headers.get('content-type')}")
    logger.info(f"Content length: {len(response.content)}")
    logger.info(f"First 100 bytes: {response.content[:100]}")
    
    try:
        # Проверяем, является ли content ZIP файлом по сигнатуре
        if len(response.content) >= 4 and response.content[:4] == b'PK\x03\x04':
            logger.info("Обнаружена ZIP сигнатура")
            
            # Сохраняем временный файл для отладки
            with open('/tmp/debug.zip', 'wb') as f:
                f.write(response.content)
            
            try:
                with zipfile.ZipFile(BytesIO(response.content), 'r') as zip_ref:
                    # Логируем содержимое архива
                    file_list = zip_ref.namelist()
                    logger.info(f"Файлы в архиве: {file_list}")
                    
                    csv_files = [f for f in file_list if f.endswith('.csv')]
                    
                    if not csv_files:
                        logger.warning("CSV файл не найден в архиве")
                        return None
                    
                    # Пробуем прочитать каждый CSV файл
                    for csv_file in csv_files:
                        try:
                            logger.info(f"Пытаемся прочитать файл: {csv_file}")
                            with zip_ref.open(csv_file) as f:
                                # Читаем первые несколько строк для логирования
                                content = f.read(500)
                                logger.info(f"Первые 500 байт CSV: {content}")
                                
                                # Возвращаемся к началу файла
                                f.seek(0)
                                
                                # Пробуем разные кодировки
                                try:
                                    df = pd.read_csv(f, encoding='utf-8')
                                except UnicodeDecodeError:
                                    f.seek(0)
                                    df = pd.read_csv(f, encoding='cp1251')
                                except Exception as e:
                                    logger.error(f"Ошибка при чтении CSV: {e}")
                                    continue
                                
                                # Предобработка данных
                                if 'dt' in df.columns:
                                    df['dt'] = pd.to_datetime(df['dt'])
                                
                                df = df.where(pd.notnull(df), None)
                                result_json = df.to_dict(orient='records')
                                
                                logger.info(f"Успешно обработано {len(result_json)} записей")
                                return result_json
                                
                        except Exception as e:
                            logger.error(f"Ошибка при обработке файла {csv_file}: {e}")
                            continue
                    
                    logger.error("Не удалось прочитать ни один CSV файл")
                    return None
                    
            except zipfile.BadZipFile as e:
                logger.error(f"Файл не является ZIP архивом: {e}")
                # Пробуем прочитать как CSV напрямую
                return read_csv_directly(response.content)
                
        else:
            logger.info("ZIP сигнатура не обнаружена, пробуем прочитать как CSV напрямую")
            return read_csv_directly(response.content)
            
    except Exception as e:
        logger.error(f"Общая ошибка при обработке отчета: {e}")
        return None

def read_csv_directly(content):
    """Прямое чтение CSV без ZIP"""
    try:
        # Пробуем разные кодировки
        try:
            df = pd.read_csv(BytesIO(content), encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(BytesIO(content), encoding='cp1251')
        
        logger.info(f"Прямое чтение CSV, колонки: {df.columns.tolist()}")
        logger.info(f"Первые строки данных: {df.head(2).to_dict()}")
        
        # Предобработка данных
        if 'dt' in df.columns:
            df['dt'] = pd.to_datetime(df['dt'])
        
        df = df.where(pd.notnull(df), None)
        result_json = df.to_dict(orient='records')
        
        logger.info(f"Успешно обработано {len(result_json)} записей")
        return result_json
        
    except Exception as e:
        logger.error(f"Ошибка при прямом чтении CSV: {e}")
        return None

def keywords_analysis(request):
    if request.method == 'POST':
        form = KeywordsAnalysisForm(request.POST)
        if form.is_valid():

            search_advertIds = []
            rack_advertIds = []
            keywords = {
                "keywords": []
            }

            advertising_type = form.cleaned_data.get('my_dropdown')
            article_number = form.cleaned_data.get('article', '').strip()
            date_start = form.cleaned_data.get('date_start')
            date_end = form.cleaned_data.get('date_end')

            date_start_str = date_start.strftime('%Y-%m-%d')
            date_end_str = date_end.strftime('%Y-%m-%d')

            params_keywords_stats = {
                                        "currentPeriod": {
                                            "start": date_start_str,
                                            "end": date_end_str
                                        
                                        },
                                        "nmIds": [int(article_number)],
                                        "topOrderBy": "openCard",
                                        "orderBy": {
                                            "field": "openCard",
                                            "mode": "desc"
                                        },
                                        "limit": 100
                                    }

            keywords_response = requests.post(url_keywords_stats, headers=headers_advertisings, json=params_keywords_stats)
            
            if keywords_response.status_code != 200:
                return render(request, 'advertisings/keywords_analysis.html', {
                    'form': form,
                    'error': f'Ошибка №{keywords_response.status_code} при получении статистики ключевых слов'
                })

            keywords_data = keywords_response.json()

            all_campaigns_response = requests.get(url_all_campaigns, headers=headers_advertisings)
            if all_campaigns_response.status_code != 200:
                return render(request, 'advertisings/campaign_analysis.html', {
                    'form': form,
                    'error': f'Ошибка №{all_campaigns_response.status_code} при получении данных о кампаниях'
                })
            all_campaigns_list = all_campaigns_response.json().get('adverts', [])

            for active_campaign in all_campaigns_list:
                if advertising_type == 'search' and active_campaign['type'] == 9: # Поисковые кампании
                    for ids in active_campaign['advert_list']:
                        search_advertIds.append(ids['advertId'])
                elif advertising_type == 'rack' and active_campaign['type'] == 8: # Кампании на полке
                    for ids in active_campaign['advert_list']:
                        rack_advertIds.append(ids['advertId'])

            search_advertId = []
            rack_advertId = []

            if search_advertIds:
                search_campaign = make_batched_requests(url_info_campaign_nmID, search_advertIds)
                for camp in search_campaign:
                    if 'unitedParams' in camp and camp['unitedParams'] and camp['unitedParams'][0]['nms'][0] == int(article_number):
                        search_advertId.append(camp['advertId'])
            
            if rack_advertIds:
                rack_campaign = make_batched_requests(url_info_campaign_nmID, rack_advertIds)
                for camp in rack_campaign:
                    if 'autoParams' in camp and camp['autoParams']['nms'][0] == int(article_number):
                        rack_advertId.append(camp['advertId'])

            advertIds = []
            if advertising_type == 'search':
                advertIds = search_advertId
            elif advertising_type == 'rack':
                advertIds = rack_advertId

            logger.info(f"Итоговое advertIds для артикула {article_number}: {advertIds}")

            if advertIds:
                for advert_id in advertIds:
                    params_keywords_stats_2 = {
                        "advert_id": advert_id,
                        "from": date_start_str,
                        "to": date_end_str
                    }

                    keywords_response_2 = requests.get(url_keywords_stats_2, headers=headers_advertisings, params=params_keywords_stats_2)
                    time.sleep(0.25)

                    if keywords_response_2.status_code == 200:
                        keywords_data_2 = keywords_response_2.json().get('keywords', [])
                        keywords['keywords'].extend(keywords_data_2)
                        logger.info(f"Добавлено {len(keywords_data_2)} ключевых слов из advert_id {advert_id}")
                    else:
                        logger.warning(f"Ошибка {keywords_response_2.status_code} для advert_id {advert_id}")
            else:
                logger.warning("Не найдено подходящих advertIds")
            
            processed_keywords = process_keywords_data(
                keywords_data=keywords_data,
                keywords_data_2=keywords
            )
            
            context = {
                'form': form,
                'keywords_data': processed_keywords,
                'total_interval': f"{date_start_str} — {date_end_str}",
                'art_prod': article_number
            }
            
            return render(request, 'advertisings/keywords_analysis.html', context)
    form = KeywordsAnalysisForm()
    context = {'form': form}
    return render(request, 'advertisings/keywords_analysis.html', context)
        
def process_keywords_data(keywords_data, keywords_data_2):

    keywords_stats = defaultdict(lambda: {
        'frequency': 0,
        'views': 0,
        'clicks': 0,
        'ctr': 0,
        'cpc': 0,
        'sum': 0,
        'open_card_count': 0,
        'add_to_cart_count': 0,
        'cr1': 0,
        'orders_count': 0,
        'cr2': 0,
        'avg_position': 0,
        'visibility': 0
    })

    for day_data in keywords_data_2.get('keywords', []):
        for keyword_stat in day_data.get('stats', []):
            keyword = keyword_stat['keyword']
            keywords_stats[keyword]['views'] += keyword_stat.get('views', 0)
            keywords_stats[keyword]['clicks'] += keyword_stat.get('clicks', 0)
            keywords_stats[keyword]['sum'] += keyword_stat.get('sum', 0)

    for keyword, stats in keywords_stats.items():
        if stats['views'] > 0:
            stats['ctr'] = (stats['clicks'] / stats['views'] * 100)
        if stats['clicks'] > 0:
            stats['cpc'] = (stats['sum'] / stats['clicks'])

    for keyword_data in keywords_data.get('data', {}).get('items', []):
        keyword = keyword_data['text']
        if keywords_stats[keyword]:
            keywords_stats[keyword]['frequency'] = keyword_data['frequency']['current']
            keywords_stats[keyword]['avg_position'] = keyword_data['avgPosition']['current']
            keywords_stats[keyword]['open_card_count'] = keyword_data['openCard']['current']
            keywords_stats[keyword]['add_to_cart_count'] = keyword_data['addToCart']['current']
            keywords_stats[keyword]['cr1'] = keyword_data['openToCart']['current']
            keywords_stats[keyword]['orders_count'] = keyword_data['orders']['current']
            keywords_stats[keyword]['cr2'] = keyword_data['cartToOrder']['current']
            keywords_stats[keyword]['visibility'] = keyword_data['visibility']['current']

    sorted_keywords = sorted(
        keywords_stats.items(),
        key=lambda x: x[1]['open_card_count'],
        reverse=True
    )

    total_sum = sum(stats['sum'] for _, stats in sorted_keywords)

    for keyword, stats in sorted_keywords:
        if total_sum > 0:
            stats['cost_percent'] = (stats['sum'] / total_sum * 100)
        else:
            stats['cost_percent'] = 0
    
    return {
        'keywords': sorted_keywords,
        'total_sum': total_sum
    }