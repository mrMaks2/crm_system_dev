from datetime import datetime
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
            article_number = form.cleaned_data.get('article', '').strip()
            date_start = form.cleaned_data.get('date_start')
            date_end = form.cleaned_data.get('date_end')

            date_start_str = date_start.strftime('%Y-%m-%d')
            date_end_str = date_end.strftime('%Y-%m-%d')

            all_campaigns_response = requests.get(url_all_campaigns, headers=headers_advertisings)
            if all_campaigns_response.status_code != 200:
                return render(request, 'advertisings/campaign_analysis.html', {
                    'form': form,
                    'error': f'Ошибка №{all_campaigns_response.status_code} при получении данных о кампаниях'
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
                    'error': f'Ошибка №{stats_response.status_code} при получении статистики'
                })
            
            response = stats_response.json()

            params_for_creaete_report = {
                    "id": uuid_string,
                    "reportType": "DETAIL_HISTORY_REPORT",
                    "userReportName": "Card report",
                    "params": {
                        "nmIDs": [int(article_number)],
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
                logger.warning(f"Детали ошибки: {create_response.json()['detail']}")

            time.sleep(2)

            response_report = requests.get(url_get_report, headers=headers_advertisings)
            if response_report.status_code != 200:
                logger.warning(f"Ошибка при получении отчета: {response_report.status_code}")
                logger.warning(f"Текст ответа: {response_report.text}")
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

def process_api_data(response, search_advertId, rack_advertId, report_data=None, article_number=None):
    
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
    
    # Обрабатываем данные из отчета
    report_stats = {}
    # В process_api_data:
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
    
    # Создаем структуру для ежедневной статистики
    daily_stats = {}
    totals = {
        'all': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0,
                'openCardCount': 0, 'addToCartCount': 0, 'ordersCount': 0, 'ordersSumRub': 0,
                'buyoutsCount': 0, 'buyoutsSumRub': 0},
        'search': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0,
                  'openCardCount': 0, 'addToCartCount': 0, 'ordersCount': 0, 'ordersSumRub': 0,
                  'buyoutsCount': 0, 'buyoutsSumRub': 0},
        'rack': {'views': 0, 'clicks': 0, 'sum': 0, 'orders': 0, 'sum_price': 0,
                'openCardCount': 0, 'addToCartCount': 0, 'ordersCount': 0, 'ordersSumRub': 0,
                'buyoutsCount': 0, 'buyoutsSumRub': 0}
    }
    
    for date_str in sorted_dates:
        date_info = dates_data[date_str]
        advert1_data = date_info['adverts'][rack_advertId] or {}
        advert2_data = date_info['adverts'][search_advertId] or {}
        report_data_day = report_stats.get(date_str, {})
        
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
        
        # Данные из отчета
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
        
        # Рассчитываем новые метрики из отчета
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
            'drrz': round(drrz, 2)
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
            'drrz': round(drrz, 2)
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
            'drrz': round(drrz, 2)
        }
        
        daily_stats[date_str] = {
            'all': all_data,
            'search': search_data,
            'rack': rack_data
        }
        
        # Обновляем общие итоги
        for key in ['views', 'clicks', 'sum', 'orders', 'sum_price', 
                   'openCardCount', 'addToCartCount', 'ordersCount', 'ordersSumRub',
                   'buyoutsCount', 'buyoutsSumRub']:
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
    
    # Новые метрики из отчета
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
        'totals': totals
    }

def get_day_name(date_str):
    """Получаем название дня недели на русском"""
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
                                # Читаем первые несколько строк для отладки
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