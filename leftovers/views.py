from django.shortcuts import render
from .tasks import get_stocks_data_async, get_orders_data_async, get_needs_data_async, get_turnover_data_async
from .forms import StocksOrdersForm
from celery.result import AsyncResult
import datetime
import logging
from django.http import JsonResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('leftovers_views')

task_results_cache = {}
unmapped_regions_set = set()

def stocks_orders_report_async(request):
    """
    Асинхронная версия с автоматическим обновлением данных на одной странице
    """
    if request.method == 'POST':
        form = StocksOrdersForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data.get('report_type')
            cab_num = int(form.cleaned_data.get('cab_num'))
            
            # Автоматически рассчитываем даты
            today = datetime.datetime.now().date()
            date_from = today - datetime.timedelta(days=14)
            date_to = today - datetime.timedelta(days=1)
            
            # Для AJAX запросов - запускаем задачу и возвращаем task_id
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Запускаем асинхронную задачу
                if report_type == 'stocks' or report_type == 'stocks_by_cluster':
                    task = get_stocks_data_async.delay(cab_num)
                elif report_type == 'orders':
                    task = get_orders_data_async.delay(cab_num)
                elif report_type == 'needs':
                    task = get_needs_data_async.delay(cab_num)
                elif report_type == 'turnover':
                    task = get_turnover_data_async.delay(cab_num)
                else:
                    return JsonResponse({
                        'status': 'error',
                        'error': 'Неизвестный тип отчета'
                    })
                
                # Сохраняем информацию о задаче в сессии
                task_info = {
                    'task_id': task.id,
                    'report_type': report_type,
                    'cab_num': cab_num,
                    'date_from': date_from.strftime('%Y-%m-%d'),
                    'date_to': date_to.strftime('%Y-%m-%d'),
                }
                
                request.session['current_task'] = task_info
                request.session.modified = True
                
                logger.info(f"Запущена AJAX задача {task.id} для отчета {report_type}, кабинет {cab_num}")
                
                return JsonResponse({
                    'status': 'processing',
                    'task_id': task.id,
                    'message': 'Запущен процесс получения данных...'
                })
            else:
                # Обычный POST запрос
                return _handle_sync_post(request, form, report_type, cab_num, date_from, date_to)
        else:
            error_msg = 'Пожалуйста, исправьте ошибки в форме'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'error': error_msg})
            else:
                context = {'form': form, 'error': error_msg}
                return render(request, 'leftovers/stocks_orders_report.html', context)
    
    else:
        # GET запрос - просто показываем форму
        form = StocksOrdersForm()
        context = {'form': form}
        
        # Если есть данные в сессии от предыдущего успешного запроса, показываем их
        if 'current_task' in request.session:
            task_info = request.session['current_task']
            task_id = task_info.get('task_id')
            
            if task_id:
                task_result = AsyncResult(task_id)
                if task_result.ready() and task_result.successful():
                    result_data = task_result.result
                    report_type = task_info.get('report_type')
                    cab_num = task_info.get('cab_num')
                    date_from = task_info.get('date_from')
                    
                    report_data = prepare_report_data(result_data, report_type, cab_num)
                    
                    if report_data:
                        context.update({
                            'report_type': report_type,
                            'cab_num': cab_num,
                            'report_data': report_data,
                            'date_from': task_info.get('date_from'),
                            'date_to': task_info.get('date_to'),
                        })
        
        return render(request, 'leftovers/stocks_orders_report.html', context)

def _handle_sync_post(request, form, report_type, cab_num, date_from, date_to):
    """Обработка синхронного POST запроса"""
    if report_type == 'stocks' or report_type == 'stocks_by_cluster':
        task = get_stocks_data_async.delay(cab_num)
    elif report_type == 'orders':
        task = get_orders_data_async.delay(cab_num)
    elif report_type == 'needs':
        task = get_needs_data_async.delay(cab_num)
    elif report_type == 'turnover':
        task = get_turnover_data_async.delay(cab_num)
    
    task_info = {
        'task_id': task.id,
        'report_type': report_type,
        'cab_num': cab_num,
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d'),
        'status': 'processing'
    }
    
    request.session['current_task'] = task_info
    request.session.modified = True
    
    context = {
        'form': form,
        'report_type': report_type,
        'cab_num': cab_num,
        'task_ids': [task.id],
        'processing': True,
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d'),
    }
    return render(request, 'leftovers/stocks_orders_report.html', context)

def prepare_report_data(raw_data, report_type, cab_num):
    """
    Подготавливает данные для отображения в отчете
    """
    try:
        logger.info(f"Подготовка отчета {report_type} для кабинета {cab_num}")
        
        if report_type == 'stocks':
            return get_stocks_report_data(raw_data)
        elif report_type == 'stocks_by_cluster':
            return get_stocks_by_cluster_report_data(raw_data)
        elif report_type == 'orders':
            return get_orders_report_data(raw_data)
        elif report_type == 'needs':
            stocks_data = raw_data.get('stocks_data', [])
            orders_data = raw_data.get('orders_data', [])
            return get_needs_report_data(stocks_data, orders_data)
        elif report_type == 'turnover':
            stocks_data = raw_data.get('stocks_data', [])
            orders_data = raw_data.get('orders_data', [])
            return get_turnover_report_data(stocks_data, orders_data)
        return None
    except Exception as e:
        logger.error(f"Ошибка при подготовке отчета: {e}")
        return None
    
def get_stocks_by_cluster_report_data(stocks_data):
    """Подготавливает данные для отчета по остаткам по кластерам"""
    
    # Кластеры в правильном порядке (такие же как в оборачиваемости)
    clusters = [
        'Центральный',
        'Приволжский',
        'Южный + Северо-Кавказский',
        'Уральский',
        'Северо-Западный',
        'Казахстан',
        'Дальневосточный + Сибирский',
        'Беларусь',
        'Армения',
        'Грузия',
        'Узбекистан',
        'Кыргызстан'
    ]
    
    report_data = {}
    total_row = {
        'supplier_article': 'ИТОГО',
        'subject': '',
        'clusters': {cluster: 0 for cluster in clusters},
        'total': 0
    }
    
    for stock_item in stocks_data:
        try:
            nm_id = stock_item['nmId']
            warehouse_name = stock_item['warehouseName']
            supplier_article = stock_item['supplierArticle']
            subject = stock_item.get('subject', '')
            quantity = stock_item.get('quantity', 0)
            
            if nm_id not in report_data:
                report_data[nm_id] = {
                    'supplier_article': supplier_article,
                    'subject': subject,
                    'clusters': {cluster: 0 for cluster in clusters},
                    'total': 0
                }
            
            # Определяем кластер для склада
            cluster = get_cluster_by_warehouse(warehouse_name)
            
            if cluster in clusters:
                report_data[nm_id]['clusters'][cluster] += quantity
                report_data[nm_id]['total'] += quantity
                
                # Добавляем в итоговую строку
                total_row['clusters'][cluster] += quantity
                total_row['total'] += quantity
                
        except Exception as e:
            continue
    
    # Добавляем итоговую строку в report_data
    report_data['total'] = total_row
    
    return {
        'report_data': report_data,
        'clusters': clusters
    }



def get_turnover_report_data(stocks_data, orders_data):
    """
    Подготавливает данные для отчета по оборачиваемости с объединенными регионами
    """
    # Получаем данные по остаткам и заказам
    stocks_report = get_stocks_report_data(stocks_data)
    orders_report = get_orders_report_data(orders_data)  # Используем обновленную функцию
    
    # Используем объединенные регионы
    clusters = get_merged_regions()
    
    report_data = {}
    total_row = {
        'supplier_article': 'ИТОГО',
        'subject': '',
        'clusters': {cluster: {'stocks': 0, 'orders': 0, 'turnover': 0} for cluster in clusters},
        'total_stocks': 0,
        'total_orders': 0,
        'total_turnover': 0
    }
    
    # Собираем все nm_id из обоих отчетов
    all_nm_ids = set(stocks_report['report_data'].keys()) | set(orders_report['report_data'].keys())
    
    for nm_id in all_nm_ids:
        if nm_id == 'total':  # Пропускаем итоговую строку
            continue
            
        stock_info = stocks_report['report_data'].get(nm_id, {
            'supplier_article': '',
            'subject': '',
            'warehouses': {wh: 0 for wh in stocks_report['all_warehouses']},
            'total': 0
        })
        
        order_info = orders_report['report_data'].get(nm_id, {
            'supplier_article': '',
            'regions': {region: 0 for region in orders_report['regions']},
            'total': 0
        })
        
        # Используем артикул из любого доступного источника
        supplier_article = stock_info.get('supplier_article') or order_info.get('supplier_article', '')
        subject = stock_info.get('subject', '')
        
        # Рассчитываем оборачиваемость по объединенным кластерам
        cluster_data = calculate_turnover_by_cluster(stock_info, order_info, clusters)
        
        # Считаем общие итоги
        total_stocks = sum(data['stocks'] for data in cluster_data.values())
        total_orders = sum(data['orders'] for data in cluster_data.values())
        try:
            if total_orders > 0:
                total_daily_orders = total_orders / 14
                total_turnover = total_stocks / total_daily_orders if total_daily_orders > 0 else 0
            else:
                total_turnover = 0
        except ZeroDivisionError:
            total_turnover = 0
        
        report_data[nm_id] = {
            'supplier_article': supplier_article,
            'subject': subject,
            'clusters': cluster_data,
            'total_stocks': total_stocks,
            'total_orders': total_orders,
            'total_turnover': round(total_turnover, 0)
        }
        
        # Добавляем в итоговую строку
        for cluster, data in cluster_data.items():
            total_row['clusters'][cluster]['stocks'] += data['stocks']
            total_row['clusters'][cluster]['orders'] += data['orders']
            try:
                if total_row['clusters'][cluster]['orders']:
                    total_row_orders = total_row['clusters'][cluster]['orders'] / 14
                    total_row['clusters'][cluster]['turnover'] = round(total_row['clusters'][cluster]['stocks'] / total_row_orders if total_row_orders > 0 else 0, 0)
                else:
                    total_row['clusters'][cluster]['turnover'] = 0
            except ZeroDivisionError:
                total_row['clusters'][cluster]['turnover'] = 0
        
        total_row['total_stocks'] += total_stocks
        total_row['total_orders'] += total_orders
        try:
            if total_row['total_orders'] > 0:
                total_row_total_orders = total_row['total_orders'] / 14
                total_row['total_turnover'] = round(total_row['total_stocks'] / total_row_total_orders if total_row_total_orders > 0 else 0, 0)
            else:
                total_row['total_turnover'] = 0
        except ZeroDivisionError:
            total_row['total_turnover'] = 0
    
    # Добавляем итоговую строку в report_data
    report_data['total'] = total_row
    
    return {
        'report_data': report_data,
        'clusters': clusters
    }

def calculate_turnover_by_cluster(stock_info, order_info, clusters):
    """
    Рассчитывает оборачиваемость по объединенным кластерам
    """
    cluster_data = {}
    
    # Распределяем остатки по объединенным кластерам
    region_stocks = distribute_stocks_to_merged_regions(stock_info, clusters)
    
    for cluster in clusters:
        # А - остатки в кластере
        stocks_in_cluster = region_stocks.get(cluster, 0)
        
        # В - заказы в кластере
        orders_in_cluster = order_info['regions'].get(cluster, 0)
        
        # Рассчитываем оборачиваемость: =ЕСЛИОШИБКА(А/(В/14);0)
        try:
            if orders_in_cluster > 0:
                daily_orders = orders_in_cluster / 14
                turnover = stocks_in_cluster / daily_orders if daily_orders > 0 else 0
            else:
                turnover = 0
        except ZeroDivisionError:
            turnover = 0
        
        cluster_data[cluster] = {
            'stocks': stocks_in_cluster,
            'orders': orders_in_cluster,
            'turnover': round(turnover, 0)
        }
    
    return cluster_data

def distribute_stocks_to_merged_regions(stock_info, merged_regions):
    """
    Распределяет остатки по складам на объединенные регионы
    """
    region_stocks = {region: 0 for region in merged_regions}
    
    # Маппинг складов на объединенные регионы
    warehouse_to_merged_region = {
        # Центральный + Беларусь
        'Рязань (Тюшевское)': 'Центральный + Беларусь',
        'Сабурово': 'Центральный + Беларусь',
        'Владимир': 'Центральный + Беларусь',
        'Тула': 'Центральный + Беларусь',
        'Котовск': 'Центральный + Беларусь',
        'Электросталь': 'Центральный + Беларусь',
        'Воронеж': 'Центральный + Беларусь',
        'Обухово': 'Центральный + Беларусь',
        'Коледино': 'Центральный + Беларусь',
        'Белая дача': 'Центральный + Беларусь',
        'Подольск': 'Центральный + Беларусь',
        'Щербинка': 'Центральный + Беларусь',
        'Чехов 1': 'Центральный + Беларусь',
        'Чехов 2': 'Центральный + Беларусь',
        'Белые Столбы': 'Центральный + Беларусь',
        'Минск': 'Центральный + Беларусь',
        
        # Приволжский
        'Кузнецк СГТ': 'Приволжский',
        'Пенза': 'Приволжский',
        'Самара (Новосемейкино)': 'Приволжский',
        'Сарапул': 'Приволжский',
        'Казань': 'Приволжский',
        
        # Южный + Северо-Кавказский + Армения + Азербайджан
        'Волгоград': 'Южный + Северо-Кавказский + Армения + Азербайджан',
        'Невинномысск': 'Южный + Северо-Кавказский + Армения + Азербайджан',
        'Краснодар': 'Южный + Северо-Кавказский + Армения + Азербайджан',
        'СЦ Ереван': 'Южный + Северо-Кавказский + Армения + Азербайджан',
        
        # Уральский + Казахстан + Узбекистан + Кыргызстан
        'Челябинск СГТ': 'Уральский + Казахстан + Узбекистан + Кыргызстан',
        'Екатеринбург - Испытателей 14г': 'Уральский + Казахстан + Узбекистан + Кыргызстан',
        'Екатеринбург - Перспективный 12': 'Уральский + Казахстан + Узбекистан + Кыргызстан',
        'Атакент': 'Уральский + Казахстан + Узбекистан + Кыргызстан',
        'Актобе': 'Уральский + Казахстан + Узбекистан + Кыргызстан',
        'Астана Карагандинское шоссе': 'Уральский + Казахстан + Узбекистан + Кыргызстан',
        'Ташкент': 'Уральский + Казахстан + Узбекистан + Кыргызстан',
        
        # Северо-Западный
        'Санкт-Петербург СГТ': 'Северо-Западный',
        'СПБ Шушары': 'Северо-Западный',
        'Санкт-Петербург Уткина Заводь': 'Северо-Западный',
        
        # Дальневосточный + Сибирский
        'Хабаровск': 'Дальневосточный + Сибирский',
        'Новосибирск': 'Дальневосточный + Сибирский'
    }
    
    # Распределяем остатки по объединенным регионам
    for warehouse, stock in stock_info['warehouses'].items():
        if warehouse in warehouse_to_merged_region:
            region = warehouse_to_merged_region[warehouse]
            if region in region_stocks:
                region_stocks[region] += stock
    
    return region_stocks

def get_stocks_report_data(stocks_data):
    """Подготавливает данные для отчета по остаткам"""
    
    # Обновленная структура складов по кластерам в правильном порядке
    warehouses_structure = {
        'Центральный': [
            'Рязань (Тюшевское)', 'Сабурово', 'Владимир', 'Тула', 'Котовск', 
            'Электросталь', 'Воронеж', 'Обухово', 'Коледино', 'Белая дача', 
            'Подольск', 'Щербинка', 'Чехов 1', 'Чехов 2', 'Белые Столбы'
        ],
        'Приволжский': ['Кузнецк СГТ', 'Пенза', 'Самара (Новосемейкино)', 'Сарапул', 'Казань'],
        'Южный + Северо-Кавказский': ['Волгоград', 'Невинномысск', 'Краснодар'],
        'Уральский': ['Челябинск СГТ', 'Екатеринбург - Испытателей 14г', 'Екатеринбург - Перспективный 12'],
        'Северо-Западный': ['Санкт-Петербург СГТ', 'СПБ Шушары', 'Санкт-Петербург Уткина Заводь'],
        'Казахстан': ['Атакент', 'Актобе', 'Астана Карагандинское шоссе'],
        'Дальневосточный + Сибирский': ['Хабаровск', 'Новосибирск'],
        'Беларусь': ['Минск'],
        'Армения': ['СЦ Ереван'],
        'Грузия': ['СЦ Тбилиси 3 Бонд'],
        'Узбекистан': ['Ташкент']
    }
    
    # Собираем все склады в плоский список для заголовков
    all_warehouses = []
    warehouse_groups = []
    for group_name, warehouses in warehouses_structure.items():
        warehouse_groups.append({
            'name': group_name,
            'warehouses': warehouses,
            'colspan': len(warehouses)
        })
        all_warehouses.extend(warehouses)
    
    report_data = {}
    total_row = {
        'supplier_article': 'ИТОГО',
        'subject': '',
        'warehouses': {wh: 0 for wh in all_warehouses},
        'total': 0
    }
    
    for stock_item in stocks_data:
        try:
            nm_id = stock_item['nmId']
            warehouse_name = stock_item['warehouseName']
            supplier_article = stock_item['supplierArticle']
            subject = stock_item.get('subject', '')
            quantity = stock_item.get('quantity', 0)
            
            if nm_id not in report_data:
                report_data[nm_id] = {
                    'supplier_article': supplier_article,
                    'subject': subject,
                    'warehouses': {wh: 0 for wh in all_warehouses},
                    'total': 0
                }
            
            if warehouse_name in all_warehouses:
                report_data[nm_id]['warehouses'][warehouse_name] = quantity
                report_data[nm_id]['total'] += quantity
                
                # Добавляем в итоговую строку
                total_row['warehouses'][warehouse_name] += quantity
                total_row['total'] += quantity
                
        except Exception as e:
            continue
    
    # Добавляем итоговую строку в report_data
    report_data['total'] = total_row
    
    return {
        'report_data': report_data,
        'warehouses_structure': warehouses_structure,
        'warehouse_groups': warehouse_groups,
        'all_warehouses': all_warehouses
    }

def get_orders_report_data(orders_data):
    """Подготавливает данные для отчета по заказам с объединенными регионами"""
    
    # Используем объединенные регионы
    regions = get_merged_regions()
    
    report_data = {}
    total_row = {
        'supplier_article': 'ИТОГО',
        'regions': {region: 0 for region in regions},
        'total': 0
    }
    
    for order_item in orders_data:
        try:
            if order_item.get('isCancel', False):
                continue

            nm_id = order_item['nmId']
            supplier_article = order_item.get('supplierArticle', '')
            region_name = order_item.get('regionName', '')
            
            if nm_id not in report_data:
                report_data[nm_id] = {
                    'supplier_article': supplier_article,
                    'regions': {region: 0 for region in regions},
                    'total': 0
                }
            
            # Используем объединенные регионы
            merged_region = map_region_to_merged(region_name)
            
            if merged_region in regions:
                report_data[nm_id]['regions'][merged_region] += 1
                report_data[nm_id]['total'] += 1
                
                # Добавляем в итоговую строку
                total_row['regions'][merged_region] += 1
                total_row['total'] += 1
                
        except Exception as e:
            continue
    
    # Добавляем итоговую строку в report_data
    report_data['total'] = total_row
    
    return {
        'report_data': report_data,
        'regions': regions
    }

def get_needs_report_data(stocks_data, orders_data, period_multiplier=3):
    """Подготавливает данные для отчета по потребностям с объединенными регионами"""
    
    # Получаем данные по остаткам и заказам для расчета потребностей
    stocks_report = get_stocks_report_data(stocks_data)
    orders_report = get_orders_report_data(orders_data)  # Используем обновленную функцию
    
    # Объединяем данные для расчета потребностей
    report_data = {}
    total_row = {
        'supplier_article': 'ИТОГО',
        'subject': '',
        'needs': {region: 0 for region in orders_report['regions']},
        'needs_total': 0
    }
    
    # Собираем все nm_id из обоих отчетов
    all_nm_ids = set(stocks_report['report_data'].keys()) | set(orders_report['report_data'].keys())
    
    for nm_id in all_nm_ids:
        if nm_id == 'total':  # Пропускаем итоговую строку
            continue
            
        stock_info = stocks_report['report_data'].get(nm_id, {
            'supplier_article': '',
            'subject': '',
            'warehouses': {wh: 0 for wh in stocks_report['all_warehouses']},
            'total': 0
        })
        
        order_info = orders_report['report_data'].get(nm_id, {
            'supplier_article': '',
            'regions': {region: 0 for region in orders_report['regions']},
            'total': 0
        })
        
        # Используем артикул из любого доступного источника
        supplier_article = stock_info.get('supplier_article') or order_info.get('supplier_article', '')
        subject = stock_info.get('subject', '')
        
        # Рассчитываем потребности с учетом периода
        needs = calculate_needs(
            stock_info, 
            order_info, 
            orders_report['regions'],  # Используем объединенные регионы
            period_multiplier
        )
        
        # Считаем общую потребность
        needs_total = sum(needs.values())
        
        report_data[nm_id] = {
            'supplier_article': supplier_article,
            'subject': subject,
            'needs': needs,
            'needs_total': needs_total,
        }
        
        # Добавляем в итоговую строку
        for region, need in needs.items():
            total_row['needs'][region] += need
        total_row['needs_total'] += needs_total
    
    # Добавляем итоговую строку в report_data
    report_data['total'] = total_row
    
    return {
        'report_data': report_data,
        'regions': orders_report['regions']  # Используем объединенные регионы
    }

def calculate_needs(stock_info, order_info, regions, period_multiplier=1):
    needs = {}
    
    region_stocks = distribute_stocks_to_regions(stock_info, regions)
    
    for region in regions:
        region_orders = order_info['regions'].get(region, 0)
        region_stock = region_stocks.get(region, 0)
        N = period_multiplier
        
        # 1. Товар с активными продажами, но недостаточными остатками
        if (region_orders > 10 and 
            region_stock > 10 and 
            region_stock < region_orders * N):
            need = region_orders * N - region_stock
        
        # 2. Критически мало остатков - добиваем до минимального уровня
        elif region_stock < 10:
            if region_orders < 50:
                # Мало продаж - добиваем до страхового запаса 50
                need = 50 - region_stock
            else:
                # Высокие продажи - планируем на период
                need = region_orders * N
        
        # 3. Товар новый или с низкими продажами, но есть потенциал
        elif region_orders > 0 and region_stock < 50:
            # Есть продажи, но мало остатков - планируем на период
            need = region_orders * N
        
        # 4. Товар новый с нулевыми остатками - минимальный заказ
        elif region_orders == 0 and region_stock == 0:
            need = 50  # Минимальный стартовый запас
        
        else:
            need = 0
        
        needs[region] = max(0, int(need))
    
    return needs

def get_cluster_by_warehouse(warehouse_name):
    """
    Определяет кластер по названию склада
    """
    warehouse_to_cluster = {
        # Центральный
        'Рязань (Тюшевское)': 'Центральный',
        'Сабурово': 'Центральный',
        'Владимир': 'Центральный',
        'Тула': 'Центральный',
        'Котовск': 'Центральный',
        'Электросталь': 'Центральный',
        'Воронеж': 'Центральный',
        'Обухово': 'Центральный',
        'Коледино': 'Центральный',
        'Белая дача': 'Центральный',
        'Подольск': 'Центральный',
        'Щербинка': 'Центральный',
        'Чехов 1': 'Центральный',
        'Чехов 2': 'Центральный',
        'Белые Столбы': 'Центральный',
        
        # Приволжский
        'Кузнецк СГТ': 'Приволжский',
        'Пенза': 'Приволжский',
        'Самара (Новосемейкино)': 'Приволжский',
        'Сарапул': 'Приволжский',
        'Казань': 'Приволжский',
        
        # Южный + Северо-Кавказский
        'Волгоград': 'Южный + Северо-Кавказский',
        'Невинномысск': 'Южный + Северо-Кавказский',
        'Краснодар': 'Южный + Северо-Кавказский',
        
        # Уральский
        'Челябинск СГТ': 'Уральский',
        'Екатеринбург - Испытателей 14г': 'Уральский',
        'Екатеринбург - Перспективный 12': 'Уральский',
        
        # Северо-Западный
        'Санкт-Петербург СГТ': 'Северо-Западный',
        'СПБ Шушары': 'Северо-Западный',
        'Санкт-Петербург Уткина Заводь': 'Северо-Западный',
        
        # Казахстан
        'Атакент': 'Казахстан',
        'Актобе': 'Казахстан',
        'Астана Карагандинское шоссе': 'Казахстан',
        
        # Дальневосточный + Сибирский
        'Хабаровск': 'Дальневосточный + Сибирский',
        'Новосибирск': 'Дальневосточный + Сибирский',
        
        # Беларусь
        'Минск': 'Беларусь',
        
        # Армения
        'СЦ Ереван': 'Армения',
        
        # Грузия
        'СЦ Тбилиси 3 Бонд': 'Грузия',
        
        # Узбекистан
        'Ташкент': 'Узбекистан'
    }
    
    return warehouse_to_cluster.get(warehouse_name, 'Центральный')

def distribute_stocks_to_regions(stock_info, regions):
    """
    Распределяет остатки по складам на регионы в правильном порядке
    """
    region_stocks = {region: 0 for region in regions}
    
    # Маппинг складов на регионы в правильном порядке
    warehouse_to_region = {
        # Центральный
        'Рязань (Тюшевское)': 'Центральный',
        'Сабурово': 'Центральный',
        'Владимир': 'Центральный',
        'Тула': 'Центральный',
        'Котовск': 'Центральный',
        'Электросталь': 'Центральный',
        'Воронеж': 'Центральный',
        'Обухово': 'Центральный',
        'Коледино': 'Центральный',
        'Белая дача': 'Центральный',
        'Подольск': 'Центральный',
        'Щербинка': 'Центральный',
        'Чехов 1': 'Центральный',
        'Чехов 2': 'Центральный',
        'Белые Столбы': 'Центральный',
        
        # Приволжский
        'Кузнецк СГТ': 'Приволжский',
        'Пенза': 'Приволжский',
        'Самара (Новосемейкино)': 'Приволжский',
        'Сарапул': 'Приволжский',
        'Казань': 'Приволжский',
        
        # Южный + Северо-Кавказский
        'Волгоград': 'Южный + Северо-Кавказский',
        'Невинномысск': 'Южный + Северо-Кавказский',
        'Краснодар': 'Южный + Северо-Кавказский',
        
        # Уральский
        'Челябинск СГТ': 'Уральский',
        'Екатеринбург - Испытателей 14г': 'Уральский',
        'Екатеринбург - Перспективный 12': 'Уральский',
        
        # Северо-Западный
        'Санкт-Петербург СГТ': 'Северо-Западный',
        'СПБ Шушары': 'Северо-Западный',
        'Санкт-Петербург Уткина Заводь': 'Северо-Западный',
        
        # Казахстан
        'Атакент': 'Казахстан',
        'Актобе': 'Казахстан',
        'Астана Карагандинское шоссе': 'Казахстан',
        
        # Дальневосточный + Сибирский
        'Хабаровск': 'Дальневосточный + Сибирский',
        'Новосибирск': 'Дальневосточный + Сибирский',
        
        # Беларусь
        'Минск': 'Беларусь',
        
        # Армения
        'СЦ Ереван': 'Армения',
        
        # Грузия
        'СЦ Тбилиси 3 Бонд': 'Грузия',
        
        # Узбекистан
        'Ташкент': 'Узбекистан'
    }
    
    # Распределяем остатки по регионам
    for warehouse, stock in stock_info['warehouses'].items():
        if warehouse in warehouse_to_region:
            region = warehouse_to_region[warehouse]
            if region in region_stocks:
                region_stocks[region] += stock
    
    return region_stocks

def map_region_to_excel(region_name):
    """
    Сопоставляет название региона из API с названием для Excel отчета
    """
    # Если регион пустой, возвращаем Центральный по умолчанию
    if not region_name:
        return 'Центральный'
    
    # Приводим к нижнему регистру для сравнения
    region_lower = region_name.lower()
    
    # Точные соответствия для федеральных округов и стран
    exact_mapping = {
        # Федеральные округа
        'москва': 'Центральный',
        'московская область': 'Центральный',
        'центральный федеральный округ': 'Центральный',
        'приволжский федеральный округ': 'Приволжский',
        'южный федеральный округ': 'Южный + Северо-Кавказский',
        'северо-кавказский федеральный округ': 'Южный + Северо-Кавказский',
        'уральский федеральный округ': 'Уральский',
        'северо-западный федеральный округ': 'Северо-Западный',
        'дальневосточный федеральный округ': 'Дальневосточный + Сибирский',
        'сибирский федеральный округ': 'Дальневосточный + Сибирский',
        
        # Страны
        'казахстан': 'Казахстан',
        'беларусь': 'Беларусь',
        'армения': 'Армения',
        'грузия': 'Грузия',
        'узбекистан': 'Узбекистан',
        'кыргызстан': 'Кыргызстан',
        
        # Склады
        'рязань (тюшевское)': 'Центральный',
        'невинномысск': 'Южный + Северо-Кавказский',
        'новосибирск': 'Дальневосточный + Сибирский',
        'белые столбы': 'Центральный',
        'тула': 'Центральный',
        'котовск': 'Центральный',
        'владимир': 'Центральный',
        'екатеринбург - перспективный 12': 'Уральский',
        'санкт-петербург уткина заводь': 'Северо-Западный',
        'самара (новосемейкино)': 'Приволжский',
        'сц ереван': 'Армения',
        'чашниково': 'Центральный',
        'астана карагандинское шоссе': 'Казахстан',
        'коледино': 'Центральный',
        'краснодар': 'Южный + Северо-Кавказский',
        'чехов 1': 'Центральный',
        'сарапул': 'Приволжский',
        'волгоград': 'Южный + Северо-Кавказский',
        'казань': 'Приволжский',
        'актобе': 'Казахстан',
        'воронеж': 'Центральный',
        'атакент': 'Казахстан',
        'электросталь': 'Центральный',
        'екатеринбург - испытателей 14г': 'Уральский',
        'сц чебоксары 2': 'Приволжский',
        'минск': 'Беларусь',
        'ташкент': 'Узбекистан',
        'тбилиси': 'Грузия',
        'ереван': 'Армения',
        'севастополь': 'Южный + Северо-Кавказский',

        # Кыргызстан
        'кыргызстан': 'Кыргызстан',
        'киргиз': 'Кыргызстан',
        'бишкек': 'Кыргызстан',
        'город бишкек': 'Кыргызстан',
        'город республиканского подчинения бишкек': 'Кыргызстан',
        'чуйская область': 'Кыргызстан',
        'иссык-кульская область': 'Кыргызстан',  # Добавлено
        'ошская область': 'Кыргызстан',  # Добавлено
    }
    
    # Сначала проверяем точное соответствие
    if region_lower in exact_mapping:
        return exact_mapping[region_lower]
    
    # Маппинг областей/республик по федеральным округам
    region_to_district = {
        # Центральный федеральный округ
        'белгородская область': 'Центральный',
        'брянская область': 'Центральный',
        'владимирская область': 'Центральный',
        'воронежская область': 'Центральный',
        'ивановская область': 'Центральный',
        'калужская область': 'Центральный',
        'костромская область': 'Центральный',
        'курская область': 'Центральный',
        'липецкая область': 'Центральный',
        'московская область': 'Центральный',
        'орловская область': 'Центральный',
        'рязанская область': 'Центральный',
        'смоленская область': 'Центральный',
        'тамбовская область': 'Центральный',
        'тверская область': 'Центральный',
        'тульская область': 'Центральный',
        'ярославская область': 'Центральный',
        'город москва': 'Центральный',
        
        # Северо-Западный федеральный округ
        'архангельская область': 'Северо-Западный',
        'вологодская область': 'Северо-Западный',
        'калининградская область': 'Северо-Западный',
        'ленинградская область': 'Северо-Западный',
        'мурманская область': 'Северо-Западный',
        'новгородская область': 'Северо-Западный',
        'псковская область': 'Северо-Западный',
        'республика карелия': 'Северо-Западный',
        'республика коми': 'Северо-Западный',
        'город санкт-петербург': 'Северо-Западный',
        'ненецкий автономный округ': 'Северо-Западный',
        
        # Южный федеральный округ
        'астраханская область': 'Южный + Северо-Кавказский',
        'волгоградская область': 'Южный + Северо-Кавказский',
        'краснодарский край': 'Южный + Северо-Кавказский',
        'республика адыгея': 'Южный + Северо-Кавказский',
        'республика калмыкия': 'Южный + Северо-Кавказский',
        'ростовская область': 'Южный + Северо-Кавказский',
        'город севастополь': 'Южный + Северо-Кавказский',
        
        # Северо-Кавказский федеральный округ
        'кабардино-балкарская республика': 'Южный + Северо-Кавказский',
        'карачаево-черкесская республика': 'Южный + Северо-Кавказский',
        'республика дагестан': 'Южный + Северо-Кавказский',
        'республика ингушетия': 'Южный + Северо-Кавказский',
        'республика северная осетия — алания': 'Южный + Северо-Кавказский',
        'ставропольский край': 'Южный + Северо-Кавказский',
        'чеченская республика': 'Южный + Северо-Кавказский',
        
        # Приволжский федеральный округ
        'кировская область': 'Приволжский',
        'нижегородская область': 'Приволжский',
        'оренбургская область': 'Приволжский',
        'пензенская область': 'Приволжский',
        'пермский край': 'Приволжский',
        'республика башкортостан': 'Приволжский',
        'республика марий эл': 'Приволжский',
        'республика мордовия': 'Приволжский',
        'республика татарстан': 'Приволжский',
        'самарская область': 'Приволжский',
        'саратовская область': 'Приволжский',
        'удмуртская республика': 'Приволжский',
        'ульяновская область': 'Приволжский',
        'чувашская республика': 'Приволжский',
        
        # Уральский федеральный округ
        'курганская область': 'Уральский',
        'свердловская область': 'Уральский',
        'тюменская область': 'Уральский',
        'челябинская область': 'Уральский',
        'ханты-мансийский автономный округ': 'Уральский',
        'ямало-ненецкий автономный округ': 'Уральский',
        
        # Сибирский федеральный округ
        'алтайский край': 'Дальневосточный + Сибирский',
        'забайкальский край': 'Дальневосточный + Сибирский',
        'иркутская область': 'Дальневосточный + Сибирский',
        'кемеровская область': 'Дальневосточный + Сибирский',
        'красноярский край': 'Дальневосточный + Сибирский',
        'новосибирская область': 'Дальневосточный + Сибирский',
        'омская область': 'Дальневосточный + Сибирский',
        'республика алтай': 'Дальневосточный + Сибирский',
        'республика бурятия': 'Дальневосточный + Сибирский',
        'республика тыва': 'Дальневосточный + Сибирский',
        'республика хакасия': 'Дальневосточный + Сибирский',
        'томская область': 'Дальневосточный + Сибирский',
        
        # Дальневосточный федеральный округ
        'амурская область': 'Дальневосточный + Сибирский',
        'еврейская автономная область': 'Дальневосточный + Сибирский',
        'камчатский край': 'Дальневосточный + Сибирский',
        'магаданская область': 'Дальневосточный + Сибирский',
        'приморский край': 'Дальневосточный + Сибирский',
        'республика саха (якутия)': 'Дальневосточный + Сибирский',
        'сахалинская область': 'Дальневосточный + Сибирский',
        'хабаровский край': 'Дальневосточный + Сибирский',
        'чукотский автономный округ': 'Дальневосточный + Сибирский',
        
        # Беларусь
        'брестская область': 'Беларусь',
        'витебская область': 'Беларусь',
        'гомельская область': 'Беларусь',
        'гродненская область': 'Беларусь',
        'минская область': 'Беларусь',
        'могилёвская область': 'Беларусь',
        
        # Казахстан
        'акмолинская область': 'Казахстан',
        'актюбинская область': 'Казахстан',
        'алматинская область': 'Казахстан',
        'алматы': 'Казахстан',
        'астана': 'Казахстан',
        'атырауская область': 'Казахстан',
        'восточно-казахстанская область': 'Казахстан',
        'жамбылская область': 'Казахстан',
        'западно-казахстанская область': 'Казахстан',
        'карагандинская область': 'Казахстан',
        'костанайская область': 'Казахстан',
        'кызылординская область': 'Казахстан',
        'мангистауская область': 'Казахстан',
        'павлодарская область': 'Казахстан',
        'северо-казахстанская область': 'Казахстан',
        'туркестанская область': 'Казахстан',
        'область улытау': 'Казахстан',
        
        # Армения
        'арагацотнская область': 'Армения',
        'араратская область': 'Армения',
        'армавирская область': 'Армения',
        'гехаркуникская область': 'Армения',
        'котайкская область': 'Армения',
        'лорийская область': 'Армения',
        'сиунская область': 'Армения',
        'тавушская область': 'Армения',
        'вайоцдзорская область': 'Армения',
        'шушинская область': 'Армения',
        
        # Грузия
        'тбилиси': 'Грузия',
        
        # Узбекистан
        'ташкент': 'Узбекистан',
        
        # Кыргызстан
        'бишкек': 'Кыргызстан',
        'город бишкек': 'Кыргызстан',
        'город республиканского подчинения бишкек': 'Кыргызстан',
        'чуйская область': 'Кыргызстан',
        'иссык-кульская область': 'Кыргызстан',  # Добавлено
        'ошская область': 'Кыргызстан',  # Добавлено
        'нарынская область': 'Кыргызстан',  # Добавлено для полноты
        'таласская область': 'Кыргызстан',  # Добавлено для полноты
        'джалал-абадская область': 'Кыргызстан',  # Добавлено для полноты
        'баткенская область': 'Кыргызстан',  # Добавлено для полноты
    }
    
    # Проверяем маппинг областей
    for api_region, excel_region in region_to_district.items():
        if api_region in region_lower:
            return excel_region
    
    # Виртуальные склады
    if 'виртуальный' in region_lower:
        if 'москв' in region_lower or 'центральн' in region_lower:
            return 'Центральный'
        elif 'краснодар' in region_lower or 'крым' in region_lower or 'южн' in region_lower:
            return 'Южный + Северо-Кавказский'
        elif 'дальнегорск' in region_lower or 'якутск' in region_lower or 'красноярск' in region_lower or 'томск' in region_lower or 'братск' in region_lower:
            return 'Дальневосточный + Сибирский'
        else:
            return 'Центральный'  # по умолчанию для виртуальных складов
    
    # Если не нашли соответствие, пробуем определить по ключевым словам
    if 'москв' in region_lower or 'центральн' in region_lower:
        return 'Центральный'
    elif 'приволж' in region_lower:
        return 'Приволжский'
    elif 'южн' in region_lower or 'кавказ' in region_lower or 'крым' in region_lower:
        return 'Южный + Северо-Кавказский'
    elif 'урал' in region_lower:
        return 'Уральский'
    elif 'северо-запад' in region_lower or 'петербург' in region_lower:
        return 'Северо-Западный'
    elif 'казахстан' in region_lower or 'астана' in region_lower or 'актобе' in region_lower or 'алмат' in region_lower:
        return 'Казахстан'
    elif 'дальневосточн' in region_lower or 'сибирск' in region_lower:
        return 'Дальневосточный + Сибирский'
    elif 'беларусь' in region_lower or 'белорус' in region_lower:
        return 'Беларусь'
    elif 'армен' in region_lower:
        return 'Армения'
    elif 'груз' in region_lower:
        return 'Грузия'
    elif 'узбекистан' in region_lower:
        return 'Узбекистан'
    elif 'кыргызстан' in region_lower or 'киргиз' in region_lower:
        return 'Кыргызстан'
    
    # Если все равно не нашли, логируем и возвращаем "Центральный" как значение по умолчанию
    if region_name not in unmapped_regions_set:
        unmapped_regions_set.add(region_name)
        logger.warning(f"Не удалось определить регион: '{region_name}'")
    
    return 'Центральный'

def get_merged_regions():
    """
    Возвращает список объединенных регионов для отчетов Заказы, Потребности, Оборачиваемость
    """
    return [
        'Центральный + Беларусь',
        'Приволжский',
        'Южный + Северо-Кавказский + Армения + Азербайджан',
        'Уральский + Казахстан + Узбекистан + Кыргызстан',
        'Северо-Западный',
        'Дальневосточный + Сибирский'
    ]

def map_region_to_merged(region_name):
    """
    Сопоставляет регион с объединенной группой
    """
    region_lower = region_name.lower() if region_name else ''
    
    # Центральный + Беларусь
    if any(keyword in region_lower for keyword in [
        'москва', 'московская', 'центральный', 'беларусь', 'белорус'
    ]):
        return 'Центральный + Беларусь'
    
    # Приволжский
    elif any(keyword in region_lower for keyword in [
        'приволжский', 'казань', 'самара', 'нижний', 'татарстан', 'башкортостан'
    ]):
        return 'Приволжский'
    
    # Южный + Северо-Кавказский + Армения + Азербайджан
    elif any(keyword in region_lower for keyword in [
        'южный', 'кавказский', 'крым', 'краснодар', 'ростов', 'армен', 'азербайджан'
    ]):
        return 'Южный + Северо-Кавказский + Армения + Азербайджан'
    
    # Уральский + Казахстан + Узбекистан + Кыргызстан
    elif any(keyword in region_lower for keyword in [
        'уральский', 'казахстан', 'узбекистан', 'кыргызстан', 'екатеринбург', 'челябинск'
    ]):
        return 'Уральский + Казахстан + Узбекистан + Кыргызстан'
    
    # Северо-Западный
    elif any(keyword in region_lower for keyword in [
        'северо-западный', 'петербург', 'ленинград'
    ]):
        return 'Северо-Западный'
    
    # Дальневосточный + Сибирский
    elif any(keyword in region_lower for keyword in [
        'дальневосточный', 'сибирский', 'новосибирск', 'иркутск', 'красноярск', 'хабаровск'
    ]):
        return 'Дальневосточный + Сибирский'
    
    # По умолчанию
    else:
        return 'Центральный + Беларусь'

def check_task_status(request, task_id):
    """
    Проверяет статус асинхронной задачи и возвращает HTML таблицы при завершении
    """
    try:
        task_result = AsyncResult(task_id)
        
        if task_result.ready():
            if task_result.successful():
                # Получаем результат задачи
                result_data = task_result.result
                
                # Получаем информацию о задаче из сессии
                task_info = request.session.get('current_task', {})
                report_type = task_info.get('report_type')
                cab_num = task_info.get('cab_num')
                date_from = task_info.get('date_from')
                date_to = task_info.get('date_to')
                
                # Подготавливаем данные для отображения
                report_data = prepare_report_data(result_data, report_type, cab_num)
                
                if report_data:
                    # Рендерим HTML таблицы
                    from django.template.loader import render_to_string
                    html_table = render_to_string('leftovers/stocks_orders_report_table.html', {
                        'report_type': report_type,
                        'cab_num': cab_num,
                        'report_data': report_data,
                        'date_from': date_from,
                        'date_to': date_to,
                    })
                    
                    # Очищаем сессию после успешного получения данных
                    if 'current_task' in request.session:
                        del request.session['current_task']
                        request.session.modified = True
                    
                    return JsonResponse({
                        'status': 'completed',
                        'html_table': html_table,
                        'report_type': report_type,
                        'cab_num': cab_num,
                        'message': 'Отчет успешно сформирован'
                    })
                else:
                    return JsonResponse({
                        'status': 'failed',
                        'error': 'Не удалось подготовить данные отчета'
                    })
            else:
                # Очищаем сессию при ошибке
                if 'current_task' in request.session:
                    del request.session['current_task']
                    request.session.modified = True
                    
                return JsonResponse({
                    'status': 'failed',
                    'error': str(task_result.result)
                })
        else:
            return JsonResponse({
                'status': 'processing',
                'message': f'Данные еще загружаются... (проверка {request.GET.get("attempt", 1)})'
            })
            
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса задачи: {e}")
        # Очищаем сессию при исключении
        if 'current_task' in request.session:
            del request.session['current_task']
            request.session.modified = True
            
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        })
    
def clear_task_session(request):
    """
    Очищает сессию от информации о задачах
    """
    if 'current_task' in request.session:
        del request.session['current_task']
        request.session.modified = True
    return JsonResponse({'status': 'cleared'})