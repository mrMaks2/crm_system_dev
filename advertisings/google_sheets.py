# google_sheets.py
import gspread
from google.oauth2.service_account import Credentials
import os
from .models import Statics
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('google_sheets')

class GoogleSheetsExporter:
    def __init__(self):
        # Несколько вариантов пути к файлу
        possible_paths = [
            r'C:\crm_system\invertible-pipe-472411-t0-06a8dea828be.json',
            'C:/crm_system/invertible-pipe-472411-t0-06a8dea828be.json',
            os.path.join('C:', 'crm_system', 'invertible-pipe-472411-t0-06a8dea828be.json'),
            os.path.join(os.getcwd(), 'invertible-pipe-472411-t0-06a8dea828be.json')
        ]
        
        self.SERVICE_ACCOUNT_FILE = None
        for path in possible_paths:
            if os.path.exists(path):
                self.SERVICE_ACCOUNT_FILE = path
                break
        
        if not self.SERVICE_ACCOUNT_FILE:
            logger.error("JSON файл не найден ни по одному из путей")
            raise FileNotFoundError("Не удалось найти файл с учетными данными")
        
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.SPREADSHEET_ID = '1gvmqGGTld7wehYoW-g4XOdgsnUj3aUfRnnJY0LQf9Rw'
        self.credentials = None
        self.client = None
        self.setup_credentials()

    def setup_credentials(self):
        """Настройка аутентификации"""
        try:
            creds = Credentials.from_service_account_file(
                self.SERVICE_ACCOUNT_FILE, 
                scopes=self.SCOPES
            )
            self.client = gspread.authorize(creds)
            logger.info("Успешная аутентификация в Google Sheets")
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            raise

    def get_headers(self):
        """Возвращает заголовки столбцов"""
        return [
            'Номер кабинета', 'Дата', 'Артикул товара', 'Среднее значение СПП',
            'Рекламные расходы', 'Клики по РК', 'Показы по РК',
            'Общее количество заказов', 'Общая сумма заказов', 'Клики всего',
            'Корзина всего', 'Корзина из РК', 'Количество заказов с РК',
            'Сумма заказов с РК', 'Количество выкупов', 'Сумма выкупов',
            'АУК показы', 'АУК клики', 'АУК корзина', 'АУК заказы', 'АУК затраты',
            'АРК показы', 'АРК клики', 'АРК корзина', 'АРК заказы', 'АРК затраты'
        ]

    def prepare_data_for_export(self, statistics):
        """Подготовка данных для экспорта"""
        data = []
        
        # Добавляем данные
        for stat in statistics:
            row = [
                stat.cab_num or '',
                stat.date.strftime('%Y-%m-%d') if stat.date else '',
                stat.article_number or '',
                stat.avg_spp or 0,
                stat.adv_expenses or 0,
                stat.clicks_PK or 0,
                stat.views_PK or 0,
                stat.total_num_orders or 0,
                stat.total_sum_orders or 0,
                stat.total_clicks or 0,
                stat.total_basket or 0,
                stat.basket_PK or 0,
                stat.orders_num_PK or 0,
                stat.orders_sum_PK or 0,
                stat.buyouts_num or 0,
                stat.buyouts_sum or 0,
                stat.views_AYK or 0,
                stat.clicks_AYK or 0,
                stat.basket_AYK or 0,
                stat.orders_AYK or 0,
                stat.cost_AYK or 0,
                stat.views_APK or 0,
                stat.clicks_APK or 0,
                stat.basket_APK or 0,
                stat.orders_APK or 0,
                stat.cost_APK or 0
            ]
            data.append(row)
        
        return data

    def clear_and_setup_sheet(self, worksheet):
        """Очистка и настройка листа с заголовками"""
        try:
            # Полностью очищаем лист
            worksheet.clear()
            
            # Добавляем заголовки
            headers = self.get_headers()
            worksheet.update('A1', [headers])
            
            # Форматируем заголовки (жирный шрифт)
            worksheet.format('A1:Z1', {
                'textFormat': {
                    'bold': True,
                    'fontSize': 11
                },
                'backgroundColor': {
                    'red': 0.9,
                    'green': 0.9,
                    'blue': 0.9
                },
                'horizontalAlignment': 'CENTER'
            })
            
            logger.info("Заголовки успешно добавлены и отформатированы")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при настройке листа: {e}")
            return False
        
    def export_statistics_to_sheets_safe(self, days_back=30):
        """Безопасный экспорт с проверкой заголовков"""
        try:
            spreadsheet = self.client.open_by_key(self.SPREADSHEET_ID)
            
            # Получаем данные
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days_back)
            
            statistics = Statics.objects.filter(
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date', 'cab_num', 'article_number')
            
            if not statistics.exists():
                logger.warning("Нет данных для экспорта")
                return True
            
            cab_nums = statistics.values_list('cab_num', flat=True).distinct()
        
            for cab_num in cab_nums:
                sheet_name = f"Выгрузка из БД каб {cab_num}"
                try:
                    worksheet = spreadsheet.worksheet(sheet_name)
                except gspread.WorksheetNotFound:
                    worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="30")
                    
                # Очищаем и настраиваем лист с заголовками
                if not self.clear_and_setup_sheet(worksheet):
                    continue
            
            # Проверяем, есть ли заголовки
                existing_headers = worksheet.row_values(1)
                expected_headers = self.get_headers()
                
                if not existing_headers or existing_headers != expected_headers:
                    # Добавляем или обновляем заголовки
                    worksheet.update('A1', [expected_headers])
                    logger.info("Заголовки добавлены/обновлены")
                
                # Получаем следующую свободную строку
                next_row = len(worksheet.get_all_values()) + 1

                data_to_export = self.prepare_data_for_export(statistics.filter(cab_num=cab_num))
                
                if data_to_export:
                    # Записываем данные начиная со следующей свободной строки
                    worksheet.update(f'A{next_row}', data_to_export)
                    logger.info(f"Добавлено {len(data_to_export)} строк начиная с {next_row}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при безопасном экспорте: {e}")
            return False

    def auto_resize_columns(self, worksheet):
        """Автоматическая корректирование ширины столбцов"""
        try:
            # Получаем все значения
            all_values = worksheet.get_all_values()
            
            if not all_values:
                return
            
            # Определяем максимальную длину для каждого столбца
            col_widths = []
            for col_idx in range(len(all_values[0])):
                max_length = 0
                for row in all_values:
                    if col_idx < len(row):
                        cell_value = str(row[col_idx])
                        max_length = max(max_length, len(cell_value))
                # Добавляем немного запаса
                col_widths.append(min(max_length + 2, 50))  # Максимум 50 символов
            
            # Устанавливаем ширину столбцов
            for col_idx, width in enumerate(col_widths, 1):
                worksheet.update_column_properties(
                    col_idx,
                    {
                        'pixelSize': width * 8  # Примерная ширина в пикселях
                    }
                )
                
        except Exception as e:
            logger.warning(f"Не удалось автоматически скорректировать ширину столбцов: {e}")

# Создаем экземпляр экспортера
sheets_exporter = GoogleSheetsExporter()