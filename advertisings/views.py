import time
from django.shortcuts import render
from django.utils.dateparse import parse_date
import requests
import os
from dotenv import load_dotenv
import logging
from .forms import CampaignAnalysisForm
import pandas as pd
import zipfile
from io import BytesIO
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('advertisings_views')

load_dotenv()
jwt_advertisings = os.getenv('jwt_advertisings')

headers_advertisings = {
        'Authorization':jwt_advertisings
    }

url_all_campaigns = 'https://advert-api.wildberries.ru/adv/v1/promotion/count' # GET
url_info_campaign_nmID = 'https://advert-api.wildberries.ru/adv/v1/promotion/adverts' # POST
url_info_campaign_stats = 'https://advert-api.wildberries.ru/adv/v2/fullstats' # POST
url_create_report = 'https://seller-analytics-api.wildberries.ru/api/v2/nm-report/downloads' # POST

def advertisings_analysis(request):
    if request.method == 'POST':
        form = CampaignAnalysisForm(request.POST)
        if form.is_valid():

            random_uuid = uuid.uuid4()
            uuid_string = str(random_uuid)
            url_get_report = f'https://seller-analytics-api.wildberries.ru/api/v2/nm-report/downloads/file/{uuid_string}' # GET
            search_advertIds = []
            rack_advertIds = []
            article_number = form.cleaned_data.get('article')
            date_start = form.cleaned_data.get('date_start')
            date_end = form.cleaned_data.get('date_end')

            date_start_str = date_start.strftime('%Y-%m-%d')
            date_end_str = date_end.strftime('%Y-%m-%d')

            all_campaigns_response = requests.get(url_all_campaigns, headers=headers_advertisings)
            if all_campaigns_response.status_code != 200:
                return render(request, 'advertisings/campaign_analysis.html', {
                    'form': form,
                    'error': 'Ошибка при получении данных о кампаниях'
                })
            all_campaigns_list = all_campaigns_response.json().get('adverts', [])

            for active_campaign in all_campaigns_list:
                if active_campaign['status'] == 9:
                    if active_campaign['type'] == 9: # Поисковые кампании
                        for ids in active_campaign['advert_list']:
                            search_advertIds.append(ids['advertId'])
                    elif active_campaign['type'] == 8: # Кампании на полке
                        for ids in active_campaign['advert_list']:
                            rack_advertIds.append(ids['advertId'])

            search_campaign_response = requests.post(url_info_campaign_nmID, headers=headers_advertisings, json=search_advertIds)
            search_campaign = search_campaign_response.json() if search_campaign_response.status_code == 200 else []

            rack_campaign_response = requests.post(url_info_campaign_nmID, headers=headers_advertisings, json=rack_advertIds)
            rack_campaign = rack_campaign_response.json() if rack_campaign_response.status_code == 200 else []

            search_advertId = None
            rack_advertId = None

            for camp in search_campaign:
                if camp['unitedParams'][0]['nms'][0] == int(article_number):
                    search_advertId = camp['advertId']
            for camp in rack_campaign:
                if camp['autoParams']['nms'][0] == int(article_number):
                    rack_advertId = camp['advertId']
            params = [
                        {
                            "id": search_advertId,
                            "interval": {
                                "begin" : date_start_str,
                                "end" : date_end_str
                                }
                        },
                        {
                            "id": rack_advertId,
                            "interval": {
                                "begin" : date_start_str,
                                "end" : date_end_str
                                }
                        }
                    ]
            stats_response = requests.post(url_info_campaign_stats, headers=headers_advertisings, json=params)
            
            if stats_response.status_code != 200:
                return render(request, 'advertisings/campaign_analysis.html', {
                    'form': form,
                    'error': 'Ошибка при получении статистики'
                })
            
            response = stats_response.json()
            
            processed_data = process_api_data(response=response, search_advertId=search_advertId, rack_advertId=rack_advertId)

            params_for_creaete_report = {
                    "id": uuid_string,
                    "reportType": "DETAIL_HISTORY_REPORT",
                    "userReportName": "Card report",
                    "params": {
                        "nmIDs": [article_number],
                        "startDate": date_start_str,
                        "endDate": date_end_str,
                        "timezone": "Europe/Moscow",
                        "aggregationLevel": "day",
                        "skipDeletedNm": 'false'
                        }
                }
            
            request.post(url_create_report, headers=headers_advertisings, json=params_for_creaete_report)

            time.sleep(2)

            response_report = request.get(url_get_report, headers=headers_advertisings)

            report_json = process_zip_report(response=response_report)
    
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

def process_api_data(response, search_advertId, rack_advertId):
    # Группируем данные по датам
    dates_data = {}
    
    # Собираем все уникальные даты
    all_dates = set()
    for advert in response:
        for day in advert['days']:
            date_str = day['date'].split('T')[0]
            all_dates.add(date_str)
    
    # Сортируем даты
    sorted_dates = sorted(all_dates, reverse=True)
    
    # Создаем структуру данных для каждой даты
    for date_str in sorted_dates:
        dates_data[date_str] = {
            'date': date_str,
            'day_name': get_day_name(date_str),
            'adverts': {
                rack_advertId: None,
                search_advertId: None
            }
        }
    
    # Заполняем данные для каждого advertId
    for advert in response:
        advert_id = advert['advertId']
        for day in advert['days']:
            date_str = day['date'].split('T')[0]
            if date_str in dates_data:
                dates_data[date_str]['adverts'][advert_id] = day
    
    # Создаем структуру для ежедневной статистики
    daily_stats = {}
    totals = {
        'all': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0},
        'search': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0},
        'rack': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0}
    }
    
    for date_str in sorted_dates:
        date_info = dates_data[date_str]
        advert1_data = date_info['adverts'][rack_advertId] or {}
        advert2_data = date_info['adverts'][search_advertId] or {}
        
        # Данные для полки
        rack_views = advert1_data.get('views', 0)
        rack_clicks = advert1_data.get('clicks', 0)
        rack_sum = advert1_data.get('sum', 0)
        rack_orders = advert1_data.get('orders', 0)
        rack_sum_price = advert1_data.get('sum_price', 0)
        
        # Данные для поиска
        search_views = advert2_data.get('views', 0)
        search_clicks = advert2_data.get('clicks', 0)
        search_sum = advert2_data.get('sum', 0)
        search_orders = advert2_data.get('orders', 0)
        search_sum_price = advert2_data.get('sum_price', 0)
        
        # Общие данные за день
        all_views = rack_views + search_views
        all_clicks = rack_clicks + search_clicks
        all_sum = rack_sum + search_sum
        all_orders = rack_orders + search_orders
        all_sum_price = rack_sum_price + search_sum_price
        
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
        
        # Рассчитываем CPO (Cost Per Order)
        rack_cpo = (rack_sum / rack_orders) if rack_orders > 0 else 0
        search_cpo = (search_sum / search_orders) if search_orders > 0 else 0
        all_cpo = (all_sum / all_orders) if all_orders > 0 else 0
        
        rack_data = {
            'views': rack_views,
            'clicks': rack_clicks,
            'ctr': round(rack_ctr, 2),
            'cpc': round(rack_cpc, 2),
            'cpo': round(rack_cpo, 2),
            'sum': round(rack_sum, 2),
            'orders': rack_orders,
            'cr': round(rack_cr, 2),
            'sum_price': round(rack_sum_price, 2)
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
            'sum_price': round(search_sum_price, 2)
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
            'sum_price': round(all_sum_price, 2)
        }
        
        daily_stats[date_str] = {
            'all': all_data,
            'search': search_data,
            'rack': rack_data
        }
        
        # Обновляем общие итоги (только суммы)
        totals['all']['views'] += all_views
        totals['all']['clicks'] += all_clicks
        totals['all']['sum'] += all_sum
        totals['all']['orders'] += all_orders
        totals['all']['sum_price'] += all_sum_price
        
        totals['search']['views'] += search_views
        totals['search']['clicks'] += search_clicks
        totals['search']['sum'] += search_sum
        totals['search']['orders'] += search_orders
        totals['search']['sum_price'] += search_sum_price
        
        totals['rack']['views'] += rack_views
        totals['rack']['clicks'] += rack_clicks
        totals['rack']['sum'] += rack_sum
        totals['rack']['orders'] += rack_orders
        totals['rack']['sum_price'] += rack_sum_price
    
    # Рассчитываем метрики за весь интервал
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
    
    # Добавляем рассчитанные метрики к итогам и округляем суммы
    totals['all']['ctr'] = round(all_ctr_total, 2)
    totals['all']['cpc'] = round(all_cpc_total, 2)
    totals['all']['cr'] = round(all_cr_total, 2)
    totals['all']['cpo'] = round(all_cpo_total, 2)
    totals['all']['sum'] = round(totals['all']['sum'], 2)
    totals['all']['sum_price'] = round(totals['all']['sum_price'], 2)
    
    totals['search']['ctr'] = round(search_ctr_total, 2)
    totals['search']['cpc'] = round(search_cpc_total, 2)
    totals['search']['cr'] = round(search_cr_total, 2)
    totals['search']['cpo'] = round(search_cpo_total, 2)
    totals['search']['sum'] = round(totals['search']['sum'], 2)
    totals['search']['sum_price'] = round(totals['search']['sum_price'], 2)
    
    totals['rack']['ctr'] = round(rack_ctr_total, 2)
    totals['rack']['cpc'] = round(rack_cpc_total, 2)
    totals['rack']['cr'] = round(rack_cr_total, 2)
    totals['rack']['cpo'] = round(rack_cpo_total, 2)
    totals['rack']['sum'] = round(totals['rack']['sum'], 2)
    totals['rack']['sum_price'] = round(totals['rack']['sum_price'], 2)
    
    return {
        'dates': sorted_dates,
        'dates_data': dates_data,
        'daily_stats': daily_stats,
        'totals': totals
    }

def get_day_name(date_str):
    """Получаем название дня недели на русском"""
    date_obj = parse_date(date_str)
    days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    return days[date_obj.weekday()]

def process_zip_report(response):
    
    # Обработка ZIP
    with zipfile.ZipFile(BytesIO(response.content), 'r') as zip_ref:
        csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
        
        if not csv_files:
            logger.warning("CSV файл не найден в архиве")
            return None
        
        with zip_ref.open(csv_files[0]) as csv_file:
            df = pd.read_csv(csv_file)
    
    # Предобработка данных
    # Конвертируем дату в datetime
    if 'dt' in df.columns:
        df['dt'] = pd.to_datetime(df['dt'])
    
    # Заменяем NaN на None для корректного JSON
    df = df.where(pd.notnull(df), None)
    
    # Конвертация в JSON
    result_json = df.to_dict(orient='records')
    
    return result_json