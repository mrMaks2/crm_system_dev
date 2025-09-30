from django.shortcuts import render
import requests
from .forms import ProductCardForm
import os
from dotenv import load_dotenv
import logging
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt  # Добавьте этот импорт

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('product_cards_views')

load_dotenv()
jwt_advertisings_cab1 = os.getenv('jwt_advertisings_cab1_1')
jwt_advertisings_cab2 = os.getenv('jwt_advertisings_cab2')
jwt_advertisings_cab3 = os.getenv('jwt_advertisings_cab3')

jwts_advertisings = {'cab_1': jwt_advertisings_cab1, 'cab_2': jwt_advertisings_cab2, 'cab_3': jwt_advertisings_cab3}

url_product_list = 'https://content-api.wildberries.ru/content/v2/get/cards/list'
url_update_product_card = 'https://content-api.wildberries.ru/content/v2/cards/update'
url_upload_media = 'https://content-api.wildberries.ru/content/v3/media/file'
url_save_media = 'https://content-api.wildberries.ru/content/v3/media/save'

def product_cards(request):
    context = {'form': ProductCardForm()}
    
    if request.method == 'POST':
        form = ProductCardForm(request.POST)
        if form.is_valid():
            article_number = form.cleaned_data.get('article', '').strip()
            cab_num = form.cleaned_data.get('cabinet')

            headers_product_card = {
                'Authorization': jwts_advertisings[cab_num]
            }

            # Получение данных карточки товара
            params = {
                "settings": {
                    "filter": {
                        "textSearch": article_number,
                        "withPhoto": -1
                    }
                }
            }

            try:
                stats_response = requests.post(url_product_list, headers=headers_product_card, json=params)
                if stats_response.status_code != 200:
                    logger.warning(f'Ошибка №{stats_response.status_code} при получении статистики: {stats_response.json()}')
                    context['error'] = f'Ошибка №{stats_response.status_code} при получении данных карточки товара'
                    return render(request, 'product_cards/product_cards.html', context)
                
                response_data = stats_response.json()
                
                if 'cards' in response_data and response_data['cards']:
                    product_card = response_data['cards'][0]
                    context['product_card'] = product_card
                    context['product_data_json'] = json.dumps(product_card, ensure_ascii=False)
                    context['cabinet'] = cab_num
                else:
                    context['error'] = 'Карточка товара не найдена'
                    
            except Exception as e:
                logger.error(f'Ошибка при запросе: {e}')
                context['error'] = f'Ошибка при выполнении запроса: {e}'

        context['form'] = form

    return render(request, 'product_cards/product_cards.html', context)

@csrf_exempt  # Добавьте этот декоратор
def update_product_card(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            nmID = data.get('nmID')
            vendorCode = data.get('vendorCode')
            brand = data.get('brand', '')
            title = data.get('title', '')
            description = data.get('description', '')
            dimensions = data.get('dimensions', {})
            characteristics = data.get('characteristics', [])
            sizes = data.get('sizes', [])
            cabinet = data.get('cabinet')

            update_data = [{
                "nmID": nmID,
                "vendorCode": vendorCode,
                "brand": brand,
                "title": title,
                "description": description,
                "dimensions": dimensions,
                "characteristics": characteristics,
                "sizes": sizes
            }]

            headers = {
                'Authorization': jwts_advertisings[cabinet],
                'Content-Type': 'application/json'
            }

            update_response = requests.post(url_update_product_card, headers=headers, json=update_data)
            
            if update_response.status_code == 200:
                return JsonResponse({'success': True, 'message': 'Карточка товара успешно обновлена'})
            else:
                logger.error(f'Ошибка обновления: {update_response.status_code} - {update_response.text}')
                return JsonResponse({'success': False, 'message': f'Ошибка обновления: {update_response.status_code}'})
                
        except Exception as e:
            logger.error(f'Ошибка при обновлении: {e}')
            return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Неверный метод запроса'})

@csrf_exempt  # Добавьте этот декоратор
def upload_media_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            file = request.FILES['file']
            nm_id = request.POST.get('nmID')
            photo_number = request.POST.get('photoNumber')
            cabinet = request.POST.get('cabinet')
            
            # Проверяем размер файла
            if file.size > 32 * 1024 * 1024:  # 32 МБ
                return JsonResponse({'success': False, 'message': 'Размер файла превышает 32 МБ'})
            
            # Проверяем тип файла
            allowed_image_types = ['image/jpeg', 'image/png', 'image/bmp', 'image/gif', 'image/webp']
            allowed_video_types = ['video/mp4', 'video/quicktime']
            
            if file.content_type not in allowed_image_types + allowed_video_types:
                return JsonResponse({'success': False, 'message': 'Неподдерживаемый формат файла'})
            
            headers = {
                'Authorization': jwts_advertisings[cabinet],
                'X-Nm-Id': str(nm_id),
                'X-Photo-Number': str(photo_number)
            }
            
            files = {
                'uploadfile': (file.name, file, file.content_type)
            }
            
            upload_response = requests.post(url_upload_media, headers=headers, files=files)
            
            if upload_response.status_code == 200:
                return JsonResponse({
                    'success': True, 
                    'message': 'Файл успешно загружен',
                    'data': upload_response.json()
                })
            else:
                logger.error(f'Ошибка загрузки файла: {upload_response.status_code} - {upload_response.text}')
                return JsonResponse({
                    'success': False, 
                    'message': f'Ошибка загрузки файла: {upload_response.status_code}'
                })
                
        except Exception as e:
            logger.error(f'Ошибка при загрузке файла: {e}')
            return JsonResponse({'success': False, 'message': f'Ошибка: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Неверный метод запроса или файл не найден'})

@csrf_exempt
def reorder_images(request):
    if request.method == 'POST':
        try:
            nm_id = request.POST.get('nmID')
            cabinet = request.POST.get('cabinet')
            new_order_json = request.POST.get('newOrder')
            
            if not all([nm_id, cabinet, new_order_json]):
                return JsonResponse({
                    'success': False, 
                    'message': 'Недостаточно данных: nmID, cabinet, newOrder'
                })
            
            new_order = json.loads(new_order_json)
            
            # Получаем текущие данные карточки
            headers_product_card = {
                'Authorization': jwts_advertisings[cabinet]
            }
            
            params = {
                "settings": {
                    "filter": {
                        "textSearch": nm_id,
                        "withPhoto": -1
                    }
                }
            }
            
            # Получаем текущую карточку
            stats_response = requests.post(
                url_product_list, 
                headers=headers_product_card, 
                json=params,
                timeout=10
            )
            
            if stats_response.status_code != 200:
                return JsonResponse({
                    'success': False, 
                    'message': f'Ошибка получения карточки: {stats_response.status_code}'
                })
            
            response_data = stats_response.json()
            if not response_data.get('cards'):
                return JsonResponse({
                    'success': False, 
                    'message': 'Карточка не найдена'
                })
            
            product_card = response_data['cards'][0]
            photos = product_card.get('photos', [])
            
            if len(photos) <= 1:
                return JsonResponse({
                    'success': False, 
                    'message': 'Недостаточно изображений для изменения порядка'
                })
            
            # Проверяем, что новый порядок корректен
            if len(new_order) != len(photos):
                return JsonResponse({
                    'success': False, 
                    'message': f'Несоответствие количества изображений: было {len(photos)}, передано {len(new_order)}'
                })
            
            # ВАЖНО: Убеждаемся, что нет дубликатов в new_order
            # used_indices = set()
            # for reorder_item in new_order:
            #     old_index = reorder_item['oldIndex']
            #     if old_index in used_indices:
            #         return JsonResponse({
            #             'success': False, 
            #             'message': f'Обнаружен дубликат изображения с индексом {old_index}'
            #         })
            #     used_indices.add(old_index)
            
            # Создаем новый порядок ссылок на изображения (уникальные)
            image_urls = []
            seen_urls = set()  # Для отслеживания уникальных URL

            for reorder_item in new_order:
                old_index = reorder_item['oldIndex']
                if old_index < len(photos):
                    # Используем URL большого изображения
                    image_url = photos[old_index].get('big')
                    if not image_url:
                        # Если нет 'big', используем первую доступную ссылку
                        image_url = next((url for url in photos[old_index].values() if isinstance(url, str) and url.startswith('http')), None)
                    
                    if image_url:
                        # Проверяем на дубликаты URL
                        if image_url in seen_urls:
                            logger.warning(f'Пропущен дубликат URL: {image_url}')
                            continue
                            
                        image_urls.append(image_url)
                        seen_urls.add(image_url)
                        logger.info(f'Добавлено изображение {old_index} -> позиция {len(image_urls)}: {image_url}')
                    else:
                        return JsonResponse({
                            'success': False, 
                            'message': f'Не удалось получить ссылку для изображения {old_index}'
                        })
            
            # Проверяем, что остались изображения после фильтрации дубликатов
            if len(image_urls) == 0:
                return JsonResponse({
                    'success': False, 
                    'message': 'Не осталось изображений после фильтрации дубликатов'
                })
            
            if len(image_urls) != len(photos):
                logger.warning(f'После фильтрации дубликатов осталось {len(image_urls)} из {len(photos)} изображений')
            
            # Подготавливаем данные для API Wildberries
            save_data = {
                "nmId": int(nm_id),
                "data": image_urls
            }
            
            headers = {
                'Authorization': jwts_advertisings[cabinet],
                'Content-Type': 'application/json'
            }
            
            # URL для сохранения медиафайлов по ссылкам
            url_save_media = 'https://content-api.wildberries.ru/content/v3/media/save'
            
            logger.info(f'Отправка запроса на обновление порядка {len(image_urls)} изображений')
            logger.info(f'URLs: {image_urls}')
            
            # Отправляем запрос к Wildberries API
            save_response = requests.post(
                url_save_media,
                headers=headers,
                json=save_data,
                timeout=30
            )
            
            # Проверяем ответ от API
            if save_response.status_code == 200:
                response_data = save_response.json()
                logger.info('Порядок изображений успешно обновлен через API')
                return JsonResponse({
                    'success': True, 
                    'message': f'Порядок {len(image_urls)} изображений успешно обновлен',
                    'data': response_data
                })
            else:
                error_detail = save_response.text
                try:
                    error_json = save_response.json()
                    error_detail = str(error_json)
                except:
                    pass
                
                logger.error(f'Ошибка обновления порядка изображений: {save_response.status_code} - {error_detail}')
                
                return JsonResponse({
                    'success': False, 
                    'message': f'Ошибка обновления порядка изображений: {save_response.status_code}',
                    'detail': error_detail
                })
                
        except requests.exceptions.Timeout:
            logger.error('Таймаут при обновлении порядка изображений')
            return JsonResponse({
                'success': False, 
                'message': 'Таймаут при обновлении порядка изображений'
            })
        except requests.exceptions.ConnectionError:
            logger.error('Ошибка соединения при обновлении порядка изображений')
            return JsonResponse({
                'success': False, 
                'message': 'Ошибка соединения с сервером Wildberries'
            })
        except Exception as e:
            logger.error(f'Ошибка при изменении порядка изображений: {str(e)}')
            return JsonResponse({
                'success': False, 
                'message': f'Ошибка: {str(e)}'
            })
    
    return JsonResponse({
        'success': False, 
        'message': 'Неверный метод запроса'
    })