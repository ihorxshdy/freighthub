"""
API для работы с фотографиями заказов
Фотофиксация этапов загрузки и выгрузки груза
"""
from flask import jsonify, request, send_file
import os
import sqlite3
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid

# Разрешенные расширения файлов
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'heic', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
PHOTOS_DIR = '/app/data/photos'

def allowed_file(filename):
    """Проверка допустимости файла"""
    if not filename:
        return True  # Если имени нет, считаем что это фото с камеры
    if '.' not in filename:
        return True  # Если нет расширения, тоже разрешаем (фото с камеры)
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def setup_photo_routes(app, get_db_connection):
    """Регистрация маршрутов для фотографий"""
    
    # Создаем директорию для фото если не существует
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    
    @app.route('/api/orders/<int:order_id>/photos/loading', methods=['POST'])
    def upload_loading_photos(order_id):
        """Загрузка фотографий загрузки груза"""
        return upload_photos(order_id, 'loading')
    
    @app.route('/api/orders/<int:order_id>/photos/unloading', methods=['POST'])
    def upload_unloading_photos(order_id):
        """Загрузка фотографий выгрузки груза"""
        return upload_photos(order_id, 'unloading')
    
    def upload_photos(order_id, photo_type):
        """Общая функция загрузки фото"""
        print(f"[PHOTO UPLOAD] Order: {order_id}, Type: {photo_type}")
        print(f"[PHOTO UPLOAD] Headers: {dict(request.headers)}")
        print(f"[PHOTO UPLOAD] Files: {request.files}")
        print(f"[PHOTO UPLOAD] Form: {request.form}")
        
        # Пытаемся получить telegram_id из заголовков или FormData
        telegram_id = request.headers.get('telegram_id') or request.form.get('telegram_id')
        if not telegram_id:
            print("[PHOTO UPLOAD] ERROR: No telegram_id in headers or form")
            return jsonify({'error': 'telegram_id header required'}), 400
        
        try:
            telegram_id = int(telegram_id)
            print(f"[PHOTO UPLOAD] Telegram ID: {telegram_id}")
        except (ValueError, TypeError) as e:
            print(f"[PHOTO UPLOAD] ERROR: Invalid telegram_id: {telegram_id}, error: {e}")
            return jsonify({'error': 'Invalid telegram_id format'}), 400
        
        conn = get_db_connection()
        
        try:
            # Получаем пользователя
            user = conn.execute(
                'SELECT id, role FROM users WHERE telegram_id = ?',
                (telegram_id,)
            ).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            user_id = user['id']
            user_role = user['role']
            
            # Проверяем заказ и права доступа
            order = conn.execute(
                '''SELECT o.*, u.telegram_id as customer_telegram_id 
                   FROM orders o 
                   JOIN users u ON o.customer_id = u.id 
                   WHERE o.id = ?''',
                (order_id,)
            ).fetchone()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            # Проверяем что пользователь - водитель этого заказа
            if user_role != 'driver' or order['winner_driver_id'] != user_id:
                return jsonify({'error': 'Access denied. Only assigned driver can upload photos'}), 403
            
            # Проверяем статус заказа
            if order['status'] != 'in_progress':
                return jsonify({'error': 'Order must be in progress'}), 400
            
            # Для выгрузки проверяем что загрузка уже подтверждена
            if photo_type == 'unloading' and not order['loading_confirmed_at']:
                return jsonify({'error': 'Loading must be confirmed before unloading'}), 400
            
            # Получаем файлы
            if 'photos' not in request.files:
                return jsonify({'error': 'No photos provided'}), 400
            
            files = request.files.getlist('photos')
            
            if not files or len(files) == 0:
                return jsonify({'error': 'At least one photo required'}), 400
            
            if len(files) > 5:
                return jsonify({'error': 'Maximum 5 photos allowed'}), 400
            
            # Создаем директорию для заказа
            order_dir = os.path.join(PHOTOS_DIR, str(order_id), photo_type)
            os.makedirs(order_dir, exist_ok=True)
            
            photo_ids = []
            
            for file in files:
                if not file:
                    continue
                
                # Проверяем content-type если filename пустой
                content_type = file.content_type or 'image/jpeg'
                
                # Определяем расширение
                if file.filename and '.' in file.filename:
                    ext = file.filename.rsplit('.', 1)[1].lower()
                else:
                    # Если filename пустой или без расширения, определяем по content_type
                    ext_map = {
                        'image/jpeg': 'jpg',
                        'image/jpg': 'jpg',
                        'image/png': 'png',
                        'image/heic': 'heic',
                        'image/webp': 'webp'
                    }
                    ext = ext_map.get(content_type, 'jpg')
                
                if ext not in ALLOWED_EXTENSIONS:
                    return jsonify({'error': f'Invalid file type: {ext}'}), 400
                
                # Генерируем уникальное имя файла
                filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(order_dir, filename)
                
                # Сохраняем файл
                file.save(filepath)
                
                # Сохраняем запись в БД
                cursor = conn.execute(
                    '''INSERT INTO order_photos 
                       (order_id, photo_type, file_path, uploaded_by, uploaded_at)
                       VALUES (?, ?, ?, ?, ?)''',
                    (order_id, photo_type, filepath, user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                photo_ids.append(cursor.lastrowid)
            
            # Обновляем временную метку подтверждения в заказе
            if photo_type == 'loading':
                conn.execute(
                    'UPDATE orders SET loading_confirmed_at = ? WHERE id = ?',
                    (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id)
                )
            elif photo_type == 'unloading':
                conn.execute(
                    'UPDATE orders SET unloading_confirmed_at = ? WHERE id = ?',
                    (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_id)
                )
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'photo_ids': photo_ids,
                'count': len(photo_ids),
                'type': photo_type
            })
            
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()
    
    @app.route('/api/orders/<int:order_id>/photos', methods=['GET'])
    def get_order_photos(order_id):
        """Получение списка фотографий заказа"""
        print(f"[GET PHOTOS] Order: {order_id}")
        # Flask normalizes headers to Title-Case, so we need to use the normalized form
        telegram_id = request.headers.get('Telegram-Id')
        print(f"[GET PHOTOS] telegram_id from header: {telegram_id}")
        
        if not telegram_id:
            print("[GET PHOTOS] ERROR: No telegram_id")
            return jsonify({'error': 'telegram_id header required'}), 400
        
        telegram_id = int(telegram_id)
        conn = get_db_connection()
        
        try:
            # Проверяем что пользователь - участник заказа
            user = conn.execute(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_id,)
            ).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            order = conn.execute(
                '''SELECT customer_id, winner_driver_id FROM orders WHERE id = ?''',
                (order_id,)
            ).fetchone()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            # Проверяем доступ
            if user['id'] != order['customer_id'] and user['id'] != order['winner_driver_id']:
                return jsonify({'error': 'Access denied'}), 403
            
            # Получаем фотографии
            photos = conn.execute(
                '''SELECT p.id, p.photo_type, p.file_path, p.uploaded_at,
                          u.name as uploaded_by_name
                   FROM order_photos p
                   JOIN users u ON p.uploaded_by = u.id
                   WHERE p.order_id = ?
                   ORDER BY p.uploaded_at ASC''',
                (order_id,)
            ).fetchall()
            
            # Группируем по типу
            result = {
                'loading': [],
                'unloading': []
            }
            
            for photo in photos:
                photo_data = {
                    'id': photo['id'],
                    'url': f'/api/photos/{photo["id"]}',
                    'uploaded_at': photo['uploaded_at'],
                    'uploaded_by': photo['uploaded_by_name']
                }
                result[photo['photo_type']].append(photo_data)
            
            return jsonify(result)
            
        finally:
            conn.close()
    
    @app.route('/api/photos/<int:photo_id>', methods=['GET'])
    def get_photo(photo_id):
        """Получение файла фотографии"""
        # Flask normalizes headers to Title-Case
        telegram_id = request.headers.get('Telegram-Id')
        if not telegram_id:
            return jsonify({'error': 'telegram_id header required'}), 400
        
        telegram_id = int(telegram_id)
        conn = get_db_connection()
        
        try:
            # Получаем информацию о фото
            photo = conn.execute(
                '''SELECT p.*, o.customer_id, o.winner_driver_id
                   FROM order_photos p
                   JOIN orders o ON p.order_id = o.id
                   WHERE p.id = ?''',
                (photo_id,)
            ).fetchone()
            
            if not photo:
                return jsonify({'error': 'Photo not found'}), 404
            
            # Проверяем пользователя
            user = conn.execute(
                'SELECT id FROM users WHERE telegram_id = ?',
                (telegram_id,)
            ).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Проверяем доступ
            if user['id'] != photo['customer_id'] and user['id'] != photo['winner_driver_id']:
                return jsonify({'error': 'Access denied'}), 403
            
            # Проверяем существование файла
            if not os.path.exists(photo['file_path']):
                return jsonify({'error': 'File not found'}), 404
            
            return send_file(photo['file_path'], mimetype='image/jpeg')
            
        finally:
            conn.close()
