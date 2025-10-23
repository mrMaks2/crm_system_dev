import os
import datetime
from celery import shared_task
from dotenv import load_dotenv
import logging
import time
from advertisings.tasks import make_request_with_retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('leftovers.tasks')

load_dotenv()
jwt_advertisings_cab1 = os.getenv('jwt_advertisings_cab1')
jwt_advertisings_cab2 = os.getenv('jwt_advertisings_cab2')
jwt_advertisings_cab3 = os.getenv('jwt_advertisings_cab3')

jwts_advertisings = [jwt_advertisings_cab1, jwt_advertisings_cab2, jwt_advertisings_cab3]

url_orders = 'https://statistics-api.wildberries.ru/api/v1/supplier/orders'
url_stocks = 'https://statistics-api.wildberries.ru/api/v1/supplier/stocks'

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def get_turnover_data_async(self, cab_num):
    """
    Асинхронная задача для получения данных об оборачиваемости
    """
    try:
        # Автоматически рассчитываем даты: с 14 дней назад по вчера
        today = datetime.datetime.now().date()
        date_from = today - datetime.timedelta(days=14)
        date_from_str = date_from.strftime('%Y-%m-%d')
        
        logger.info(f"Асинхронное получение данных для оборачиваемости кабинета {cab_num}")
        
        # Получаем оба типа данных
        stocks_data = get_stocks_data(cab_num, date_from_str)
        orders_data = get_orders_data(cab_num, date_from_str)
        
        logger.info(f"Для оборачиваемости получено: {len(stocks_data)} остатков, {len(orders_data)} заказов")
        
        return {
            'stocks_data': stocks_data,
            'orders_data': orders_data
        }
        
    except Exception as exc:
        logger.error(f"Ошибка в асинхронной задаче получения оборачиваемости: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {'stocks_data': [], 'orders_data': []}

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def get_stocks_data_async(self, cab_num):
    """
    Асинхронная задача для получения данных об остатках
    """
    try:
        # Автоматически рассчитываем даты: с 14 дней назад по вчера
        today = datetime.datetime.now().date()
        date_from = today - datetime.timedelta(days=14)
        date_from_str = date_from.strftime('%Y-%m-%d')
        
        logger.info(f"Асинхронное получение остатков для кабинета {cab_num} с {date_from_str}")
        
        stocks_data = get_stocks_data(cab_num, date_from_str)
        logger.info(f"Успешно получено {len(stocks_data)} записей об остатках")
        return stocks_data
        
    except Exception as exc:
        logger.error(f"Ошибка в асинхронной задаче получения остатков: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return []

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def get_orders_data_async(self, cab_num):
    """
    Асинхронная задача для получения данных о заказах
    """
    try:
        # Автоматически рассчитываем даты: с 14 дней назад по вчера
        today = datetime.datetime.now().date()
        date_from = today - datetime.timedelta(days=14)
        date_from_str = date_from.strftime('%Y-%m-%d')
        
        logger.info(f"Асинхронное получение заказов для кабинета {cab_num} с {date_from_str}")
        
        orders_data = get_orders_data(cab_num, date_from_str)
        logger.info(f"Успешно получено {len(orders_data)} записей о заказах")
        return orders_data
        
    except Exception as exc:
        logger.error(f"Ошибка в асинхронной задаче получения заказов: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return []

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def get_needs_data_async(self, cab_num):
    """
    Асинхронная задача для получения данных о потребностях (остатки + заказы)
    """
    try:
        # Автоматически рассчитываем даты: с 14 дней назад по вчера
        today = datetime.datetime.now().date()
        date_from = today - datetime.timedelta(days=14)
        date_from_str = date_from.strftime('%Y-%m-%d')
        
        logger.info(f"Асинхронное получение данных для потребностей кабинета {cab_num}")
        
        # Получаем оба типа данных
        stocks_data = get_stocks_data(cab_num, date_from_str)
        orders_data = get_orders_data(cab_num, date_from_str)
        
        logger.info(f"Для потребностей получено: {len(stocks_data)} остатков, {len(orders_data)} заказов")
        
        return {
            'stocks_data': stocks_data,
            'orders_data': orders_data
        }
        
    except Exception as exc:
        logger.error(f"Ошибка в асинхронной задаче получения потребностей: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {'stocks_data': [], 'orders_data': []}

# Синхронные функции остаются без изменений
def get_stocks_data(cab_num, date_from_str):
    """
    Синхронная функция для получения данных об остатках
    """
    try:
        logger.info(f"Получение остатков для кабинета {cab_num}")
        
        # Проверяем валидность JWT токена
        if cab_num > len(jwts_advertisings) or not jwts_advertisings[cab_num - 1]:
            logger.error(f"Неверный кабинет или JWT токен для кабинета {cab_num}")
            return []
            
        jwt_token = jwts_advertisings[cab_num - 1]
        
        headers = {'Authorization': jwt_token}
        
        all_stocks_data = []
        date_from = date_from_str
        request_count = 0
        max_requests = 10
        
        while request_count < max_requests:
            request_count += 1
            
            params = {
                "dateFrom": date_from,
            }
            
            logger.info(f"Запрос остатков {request_count} с dateFrom: {date_from}")
            
            response = make_request_with_retry(
                url_stocks,
                method='GET',
                headers=headers,
                params=params,
                api_retry_delay=10
            )
            
            if response.status_code != 200:
                logger.warning(f"Ошибка при получении остатков: {response.status_code} - {response.text}")
                break
            
            stocks_batch = response.json()
            
            if not stocks_batch:
                logger.info("Получен пустой ответ - все данные выгружены")
                break
            
            if len(stocks_batch) == 0:
                logger.info("Получен пустой массив - все остатки выгружены")
                break
            
            logger.info(f"Получено {len(stocks_batch)} записей об остатках в батче {request_count}")
            all_stocks_data.extend(stocks_batch)
            
            # Если получено меньше записей, значит это последний батч
            if len(stocks_batch) < 50000:
                logger.info(f"Получен последний батч ({len(stocks_batch)} записей)")
                break
            
            # Задержка между запросами
            time.sleep(1)
        
        logger.info(f"Всего получено {len(all_stocks_data)} записей об остатках для кабинета {cab_num}")
        return all_stocks_data
        
    except Exception as exc:
        logger.error(f"Ошибка при получении остатков: {exc}")
        return []

def get_orders_data(cab_num, date_from_str):
    """
    Синхронная функция для получения данных о заказах
    """
    try:
        logger.info(f"Получение заказов для кабинета {cab_num}")
        
        if cab_num > len(jwts_advertisings) or not jwts_advertisings[cab_num - 1]:
            logger.error(f"Неверный кабинет или JWT токен для кабинета {cab_num}")
            return []
            
        jwt_token = jwts_advertisings[cab_num - 1]
        
        headers = {'Authorization': jwt_token}
        
        all_orders_data = []
        last_change_date = date_from_str
        request_count = 0
        max_requests = 10
        
        while request_count < max_requests:
            request_count += 1
            
            params = {
                "dateFrom": last_change_date,
            }
            
            logger.info(f"Запрос заказов {request_count} с dateFrom: {last_change_date}")
            
            response = make_request_with_retry(
                url_orders,
                method='GET',
                headers=headers,
                params=params,
                api_retry_delay=10
            )
            
            if response.status_code != 200:
                logger.warning(f"Ошибка при получении заказов: {response.status_code} - {response.text}")
                break
            
            orders_batch = response.json()
            
            if not orders_batch or not isinstance(orders_batch, list):
                logger.info("Получен пустой ответ или все данные выгружены")
                break
            
            if len(orders_batch) == 0:
                logger.info("Получен пустой массив - все заказы выгружены")
                break
            
            logger.info(f"Получено {len(orders_batch)} записей о заказах в батче {request_count}")
            all_orders_data.extend(orders_batch)
            
            # Если получено меньше записей, значит это последний батч
            if len(orders_batch) < 50000:
                logger.info(f"Получен последний батч ({len(orders_batch)} записей)")
                break
            
            # Получаем последнюю дату изменения для следующего запроса
            last_record = orders_batch[-1]
            last_change_date = last_record.get('lastChangeDate', '')
            
            if not last_change_date:
                logger.warning("Не удалось получить lastChangeDate из последней записи")
                break
            
            logger.info(f"Следующий запрос с lastChangeDate: {last_change_date}")
            
            # Задержка между запросами
            time.sleep(1)
        
        logger.info(f"Всего получено {len(all_orders_data)} записей о заказах для кабинета {cab_num}")
        return all_orders_data
        
    except Exception as exc:
        logger.error(f"Ошибка при получении заказов: {exc}")
        return []