"""
Flask приложение для Telegram Mini App
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sqlite3
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Импорт локальной конфигурации
from truck_config import TRUCK_CATEGORIES, DATABASE_PATH, SECRET_KEY
from webhook_client import notify_new_order  # Webhook уведомления

app = Flask(__name__)
CORS(app)

# Конфигурация
app.config['SECRET_KEY'] = SECRET_KEY

def get_db_connection():
    """Создание подключения к БД"""
    # Создаём папку для БД если не существует
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    
    # Инициализируем БД если таблиц нет
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        # Таблиц нет - инициализируем БД
        from init_db import init_database
        conn.close()
        init_database()
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
    
    return conn

def dict_from_row(row):
    """Преобразование Row в dict"""
    return dict(zip(row.keys(), row)) if row else None

# === МАРШРУТЫ ===

@app.route('/')
def index():
    """Главная страница Mini App"""
    import time
    # Передаём timestamp для cache busting
    return render_template('index.html', version=int(time.time()))

# === API ENDPOINTS ===

@app.route('/api/user', methods=['GET'])
def get_user():
    """Получение данных пользователя по telegram_id"""
    telegram_id = request.args.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400
    
    conn = get_db_connection()
    
    # Сначала проверим сколько вообще пользователей в БД
    total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()
    logger.info(f"Total users in DB: {total_users['count']}")
    
    # Покажем всех пользователей для отладки
    all_users = conn.execute('SELECT telegram_id, name, role FROM users LIMIT 10').fetchall()
    logger.info(f"Users in DB: {[dict(u) for u in all_users]}")
    
    user = conn.execute(
        'SELECT * FROM users WHERE telegram_id = ?',
        (telegram_id,)
    ).fetchone()
    conn.close()
    
    if user:
        logger.info(f"User found: {dict(user)}")
        return jsonify(dict_from_row(user))
    
    logger.error(f"User NOT found for telegram_id={telegram_id}")
    return jsonify({
        'error': 'User not found',
        'telegram_id': telegram_id,
        'total_users_in_db': total_users['count'],
        'hint': 'Register via Telegram bot first'
    }), 404

@app.route('/api/register', methods=['POST'])
def register_user():
    """
    Регистрация нового пользователя (НЕ ИСПОЛЬЗУЕТСЯ)
    Регистрация происходит только через бота!
    Этот endpoint оставлен для совместимости, но всегда возвращает ошибку.
    """
    return jsonify({
        'error': 'Registration only available through Telegram bot',
        'message': 'Регистрация доступна только через Telegram бота'
    }), 403

@app.route('/api/truck-types', methods=['GET'])
def get_truck_types():
    """Получение полного списка типов грузовиков с группировкой"""
    from truck_config import TRUCK_TYPES
    
    # Формируем иерархическую структуру для frontend
    result = []
    
    for category_id, category_data in TRUCK_CATEGORIES.items():
        category = {
            'id': category_id,
            'name': category_data['name'],
            'types': []
        }
        
        # Если есть подтипы
        if 'subtypes' in category_data:
            for subtype_id, subtype_name in category_data['subtypes'].items():
                # Проверяем есть ли под-подтипы
                if 'sub_subtypes' in category_data and subtype_id in category_data['sub_subtypes']:
                    # Добавляем под-подтипы
                    for sub_subtype_id, sub_subtype_name in category_data['sub_subtypes'][subtype_id].items():
                        category['types'].append({
                            'id': sub_subtype_id,
                            'name': f"{subtype_name} - {sub_subtype_name}",
                            'full_name': TRUCK_TYPES.get(sub_subtype_id, sub_subtype_name)
                        })
                else:
                    # Добавляем как конечный тип
                    category['types'].append({
                        'id': subtype_id,
                        'name': subtype_name,
                        'full_name': TRUCK_TYPES.get(subtype_id, subtype_name)
                    })
        
        result.append(category)
    
    return jsonify(result)

# === ЗАКАЗЧИК - Управление заказами ===

@app.route('/api/customer/orders', methods=['GET'])
def get_customer_orders():
    """Получение всех заказов заказчика, сгруппированных по статусам"""
    telegram_id = request.args.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400
    
    conn = get_db_connection()
    
    # Получаем ID пользователя
    user = conn.execute(
        'SELECT id FROM users WHERE telegram_id = ?',
        (telegram_id,)
    ).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    # Получаем все заказы с контактами водителя (для завершенных)
    orders = conn.execute(
        '''SELECT o.*, 
                  COUNT(DISTINCT b.id) as bids_count,
                  MIN(b.price) as min_bid_price,
                  winner.name as winner_name,
                  winner.phone_number as winner_phone,
                  winner.telegram_id as winner_telegram_id
           FROM orders o
           LEFT JOIN bids b ON o.id = b.order_id
           LEFT JOIN users winner ON o.winner_driver_id = winner.id
           WHERE o.customer_id = ?
           GROUP BY o.id
           ORDER BY o.created_at DESC''',
        (user['id'],)
    ).fetchall()
    
    conn.close()
    
    # Группируем по статусам
    result = {
        'searching': [],    # Идет поиск исполнителей (active + есть предложения)
        'created': [],      # Созданные заявки (active + нет предложений)
        'in_progress': [],  # В процессе выполнения
        'closed': []        # Завершенные/отмененные заявки
    }
    
    for order in orders:
        order_data = dict_from_row(order)
        status = order_data['status']
        
        if status == 'closed':
            result['closed'].append(order_data)
        elif status == 'in_progress':
            result['in_progress'].append(order_data)
        elif status == 'active':
            if order_data['bids_count'] > 0:
                result['searching'].append(order_data)
            else:
                result['created'].append(order_data)
        elif status in ('completed', 'cancelled', 'no_offers'):
            # Legacy статусы - переводим в closed
            result['closed'].append(order_data)
    
    return jsonify(result)

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Создание новой заявки"""
    telegram_id = request.args.get('telegram_id')
    data = request.json
    
    logger.info(f"Create order request: telegram_id={telegram_id}, data={data}")
    
    if not telegram_id:
        logger.error("Error: telegram_id missing")
        return jsonify({'error': 'telegram_id required'}), 400
    
    required_fields = ['pickup_location', 'delivery_location', 'description', 'truck_type_id']
    if not all(field in data for field in required_fields):
        missing = [f for f in required_fields if f not in data]
        logger.error(f"Error: Missing fields: {missing}")
        return jsonify({'error': 'Missing required fields', 'missing': missing}), 400
    
    try:
        conn = get_db_connection()
        logger.info(f"DB connected: {DATABASE_PATH}")
        
        # Получаем ID пользователя (по схеме БД бота - используем id, не telegram_id)
        user = conn.execute(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_id,)
        ).fetchone()
        
        if not user:
            conn.close()
            logger.error(f"Error: User not found for telegram_id={telegram_id}")
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"User found: id={user['id']}")
        
        # Expires_at - через 15 минут от создания
        from datetime import timedelta
        expires_at = (datetime.now() + timedelta(minutes=15)).isoformat()
        
        # Создаем заказ по схеме БД бота
        cursor = conn.execute(
            '''INSERT INTO orders (
                customer_id, truck_type, cargo_description, delivery_address,
                status, created_at, expires_at,
                pickup_address, pickup_time, delivery_time, max_price, delivery_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                user['id'],  # customer_id - это users.id
                data['truck_type_id'],  # truck_type - строка вида "manipulator_5t"
                data['description'],  # cargo_description
                data['delivery_location'],  # delivery_address
                'active',
                datetime.now().isoformat(),
                expires_at,
                data.get('pickup_location'),  # pickup_address
                data.get('pickup_time'),  # pickup_time
                data.get('delivery_time'),  # delivery_time
                data.get('price', 0),  # max_price
                data.get('delivery_date')  # delivery_date
            )
        )
        
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logger.info(f"Order created: id={order_id}")
        
        # Отправляем webhook уведомление боту
        try:
            logger.info(f"Sending webhook to bot...")
            notify_new_order(
                order_id=order_id,
                truck_type=data['truck_type_id'],  # Передаём ID, а не название
                cargo_description=data['description'],
                delivery_address=data['delivery_location'],
                max_price=data.get('price', 0),
                pickup_address=data.get('pickup_location'),
                pickup_time=data.get('pickup_time'),
                delivery_time=data.get('delivery_time'),
                delivery_date=data.get('delivery_date')
            )
            logger.info(f"Webhook sent successfully")
        except Exception as e:
            logger.info(f"Webhook error (non-critical): {e}")
            import traceback
            traceback.print_exc()
            # Не прерываем выполнение, если webhook не сработал
        
        return jsonify({'id': order_id, 'message': 'Order created successfully'})
    
    except Exception as e:
        logger.error(f"Fatal error creating order: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@app.route('/api/orders/<int:order_id>/bids', methods=['GET'])
def get_order_bids(order_id):
    """Получение всех предложений по заказу (по схеме БД бота)"""
    conn = get_db_connection()
    
    bids = conn.execute(
        '''SELECT b.*, u.name, u.phone_number
           FROM bids b
           JOIN users u ON b.driver_id = u.id
           WHERE b.order_id = ?
           ORDER BY b.price ASC''',
        (order_id,)
    ).fetchall()
    
    conn.close()
    
    return jsonify([dict_from_row(bid) for bid in bids])

# === ВОДИТЕЛЬ - Управление предложениями ===

@app.route('/api/driver/orders', methods=['GET'])
def get_driver_orders():
    """Получение заказов для водителя, сгруппированных по статусам"""
    telegram_id = request.args.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400
    
    conn = get_db_connection()
    
    # Получаем ID пользователя
    user = conn.execute(
        'SELECT id FROM users WHERE telegram_id = ?',
        (telegram_id,)
    ).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    result = {
        'open': [],         # Открытые заявки (можно сделать предложение)
        'my_bids': [],      # Заявки с моими предложениями
        'won': [],          # Выигранные заявки (пока аукцион активен)
        'in_progress': [],  # В процессе выполнения
        'closed': []        # Закрытые заявки
    }
    
    # Получаем открытые заявки (без предложений от этого водителя)
    open_orders = conn.execute(
        '''SELECT o.*, 
                  COUNT(DISTINCT b.id) as bids_count,
                  MIN(b.price) as min_bid_price
           FROM orders o
           LEFT JOIN bids b ON o.id = b.order_id
           WHERE o.status = 'active'
             AND o.id NOT IN (
                 SELECT order_id FROM bids WHERE driver_id = ?
             )
           GROUP BY o.id
           ORDER BY o.created_at DESC
           LIMIT 50''',
        (user['id'],)
    ).fetchall()
    
    # Заявки с предложениями от водителя (аукцион еще идет)
    my_bids_orders = conn.execute(
        '''SELECT o.*, b.price as my_bid_price, b.id as bid_id,
                  COUNT(DISTINCT b2.id) as total_bids,
                  MIN(b2.price) as min_bid_price
           FROM orders o
           JOIN bids b ON o.id = b.order_id
           LEFT JOIN bids b2 ON o.id = b2.order_id
           WHERE b.driver_id = ? 
             AND o.status = 'active'
           GROUP BY o.id
           ORDER BY o.created_at DESC''',
        (user['id'],)
    ).fetchall()
    
    # Выигранные заявки (аукцион завершен, этот водитель победитель, но еще не начата работа)
    # Оставляем пустым - они сразу переходят в in_progress
    won_orders = []
    
    # В процессе выполнения (где этот водитель - исполнитель)
    in_progress_orders = conn.execute(
        '''SELECT o.*, b.price as my_bid_price, u.name as customer_name, 
                  u.phone_number as customer_phone, u.telegram_id as customer_telegram_id,
                  u.username as customer_username
           FROM orders o
           JOIN bids b ON o.id = b.order_id
           JOIN users u ON o.customer_id = u.id
           WHERE o.winner_driver_id = ? 
             AND o.status = 'in_progress'
           ORDER BY o.created_at DESC''',
        (user['id'],)
    ).fetchall()
    
    # Закрытые заявки
    closed_orders = conn.execute(
        '''SELECT o.*, b.price as my_bid_price
           FROM orders o
           LEFT JOIN bids b ON o.id = b.order_id AND b.driver_id = ?
           WHERE o.status = 'closed'
             AND b.id IS NOT NULL
           ORDER BY o.created_at DESC
           LIMIT 20''',
        (user['id'],)
    ).fetchall()
    
    conn.close()
    
    result['open'] = [dict_from_row(order) for order in open_orders]
    result['my_bids'] = [dict_from_row(order) for order in my_bids_orders]
    result['won'] = [dict_from_row(order) for order in won_orders]
    result['in_progress'] = [dict_from_row(order) for order in in_progress_orders]
    result['closed'] = [dict_from_row(order) for order in closed_orders]
    
    return jsonify(result)

@app.route('/api/bids', methods=['POST'])
def create_bid():
    """Создание предложения на заказ"""
    telegram_id = request.args.get('telegram_id')
    data = request.json
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id required'}), 400
    
    required_fields = ['order_id', 'price']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    
    # Получаем ID пользователя
    user = conn.execute(
        'SELECT id FROM users WHERE telegram_id = ?',
        (telegram_id,)
    ).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'User not found'}), 404
    
    # Проверяем, существует ли уже предложение
    existing = conn.execute(
        'SELECT id FROM bids WHERE order_id = ? AND driver_id = ?',
        (data['order_id'], user['id'])
    ).fetchone()
    
    if existing:
        conn.close()
        return jsonify({'error': 'Bid already exists'}), 400
    
    # Создаем предложение
    cursor = conn.execute(
        '''INSERT INTO bids (order_id, driver_id, price)
           VALUES (?, ?, ?)''',
        (
            data['order_id'],
            user['id'],
            data['price']
        )
    )
    
    bid_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'id': bid_id, 'message': 'Bid created successfully'})

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order_details(order_id):
    """Получение детальной информации о заказе"""
    conn = get_db_connection()
    
    order = conn.execute(
        '''SELECT o.*, u.first_name, u.last_name, u.username, u.phone
           FROM orders o
           JOIN users u ON o.customer_id = u.id
           WHERE o.id = ?''',
        (order_id,)
    ).fetchone()
    
    conn.close()
    
    if order:
        return jsonify(dict_from_row(order))
    return jsonify({'error': 'Order not found'}), 404

@app.route('/api/orders/<int:order_id>/confirm-completion', methods=['POST'])
def confirm_order_completion(order_id):
    """Подтверждение выполнения заказа одной из сторон"""
    data = request.json
    telegram_id = data.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id is required'}), 400
    
    conn = get_db_connection()
    
    # Получаем заказ
    order = conn.execute(
        '''SELECT o.*, 
                  c.telegram_id as customer_telegram_id,
                  d.telegram_id as driver_telegram_id,
                  d.name as driver_name,
                  c.name as customer_name
           FROM orders o
           JOIN users c ON o.customer_id = c.id
           LEFT JOIN users d ON o.winner_driver_id = d.id
           WHERE o.id = ?''',
        (order_id,)
    ).fetchone()
    
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    if order['status'] != 'in_progress':
        conn.close()
        return jsonify({'error': 'Order is not in progress'}), 400
    
    # Определяем, кто подтверждает
    is_customer = (telegram_id == order['customer_telegram_id'])
    is_driver = (telegram_id == order['driver_telegram_id'])
    
    if not is_customer and not is_driver:
        conn.close()
        return jsonify({'error': 'You are not a participant of this order'}), 403
    
    # Обновляем подтверждение
    if is_customer:
        conn.execute('UPDATE orders SET customer_confirmed = TRUE WHERE id = ?', (order_id,))
        confirmer_role = 'customer'
        other_telegram_id = order['driver_telegram_id']
        other_name = order['driver_name']
    else:
        conn.execute('UPDATE orders SET driver_confirmed = TRUE WHERE id = ?', (order_id,))
        confirmer_role = 'driver'
        other_telegram_id = order['customer_telegram_id']
        other_name = order['customer_name']
    
    conn.commit()
    
    # Проверяем, подтвердили ли обе стороны
    updated_order = conn.execute(
        'SELECT customer_confirmed, driver_confirmed FROM orders WHERE id = ?',
        (order_id,)
    ).fetchone()
    
    both_confirmed = updated_order['customer_confirmed'] and updated_order['driver_confirmed']
    
    if both_confirmed:
        # Обе стороны подтвердили - переводим в closed
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', ('closed', order_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Order completed and closed',
            'status': 'closed',
            'both_confirmed': True
        })
    else:
        conn.close()
        
        # Отправляем уведомление второй стороне через webhook
        # TODO: Implement webhook notification
        
        return jsonify({
            'success': True,
            'message': f'Confirmation recorded from {confirmer_role}',
            'status': 'in_progress',
            'both_confirmed': False,
            'awaiting_confirmation_from': 'driver' if confirmer_role == 'customer' else 'customer'
        })

@app.route('/api/orders/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """Отмена заказа одной из сторон"""
    data = request.json
    telegram_id = data.get('telegram_id')
    
    if not telegram_id:
        return jsonify({'error': 'telegram_id is required'}), 400
    
    conn = get_db_connection()
    
    # Получаем заказ
    order = conn.execute(
        '''SELECT o.*, 
                  c.telegram_id as customer_telegram_id,
                  c.id as customer_user_id,
                  d.telegram_id as driver_telegram_id,
                  d.id as driver_user_id
           FROM orders o
           JOIN users c ON o.customer_id = c.id
           LEFT JOIN users d ON o.winner_driver_id = d.id
           WHERE o.id = ?''',
        (order_id,)
    ).fetchone()
    
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    if order['status'] != 'in_progress':
        conn.close()
        return jsonify({'error': 'Order is not in progress'}), 400
    
    # Определяем, кто отменяет
    is_customer = (telegram_id == order['customer_telegram_id'])
    is_driver = (telegram_id == order['driver_telegram_id'])
    
    if not is_customer and not is_driver:
        conn.close()
        return jsonify({'error': 'You are not a participant of this order'}), 403
    
    # Получаем user_id отменяющего
    cancelled_by_user_id = order['customer_user_id'] if is_customer else order['driver_user_id']
    
    # Отменяем заказ
    conn.execute(
        '''UPDATE orders 
           SET status = ?, cancelled_by = ?, cancelled_at = CURRENT_TIMESTAMP 
           WHERE id = ?''',
        ('closed', cancelled_by_user_id, order_id)
    )
    conn.commit()
    conn.close()
    
    # TODO: Отправить уведомление второй стороне через webhook
    
    return jsonify({
        'success': True,
        'message': 'Order cancelled',
        'status': 'closed',
        'cancelled_by': 'customer' if is_customer else 'driver'
    })

@app.route('/api/orders/<int:order_id>/select-winner', methods=['POST'])
def select_auction_winner(order_id):
    """Ручной выбор исполнителя заказчиком (досрочное завершение аукциона)"""
    data = request.json
    telegram_id = data.get('telegram_id')
    bid_id = data.get('bid_id')
    
    if not telegram_id or not bid_id:
        return jsonify({'error': 'telegram_id and bid_id are required'}), 400
    
    conn = get_db_connection()
    
    # Получаем заказ
    order = conn.execute(
        '''SELECT o.*, c.telegram_id as customer_telegram_id
           FROM orders o
           JOIN users c ON o.customer_id = c.id
           WHERE o.id = ?''',
        (order_id,)
    ).fetchone()
    
    if not order:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404
    
    # Проверяем, что пользователь - заказчик этой заявки
    if telegram_id != order['customer_telegram_id']:
        conn.close()
        return jsonify({'error': 'Only order creator can select winner'}), 403
    
    # Проверяем, что заявка активна
    if order['status'] != 'active':
        conn.close()
        return jsonify({'error': 'Order is not active'}), 400
    
    # Получаем информацию о выбранной ставке
    bid = conn.execute(
        '''SELECT b.*, d.telegram_id as driver_telegram_id, d.username as driver_username,
                  d.phone_number as driver_phone, d.name as driver_name
           FROM bids b
           JOIN users d ON b.driver_id = d.id
           WHERE b.id = ? AND b.order_id = ?''',
        (bid_id, order_id)
    ).fetchone()
    
    if not bid:
        conn.close()
        return jsonify({'error': 'Bid not found'}), 404
    
    # Обновляем заказ: устанавливаем победителя и статус in_progress
    conn.execute(
        '''UPDATE orders 
           SET status = 'in_progress', 
               winner_driver_id = ?,
               winning_price = ?
           WHERE id = ?''',
        (bid['driver_id'], bid['price'], order_id)
    )
    conn.commit()
    
    # Получаем данные заказчика
    customer = conn.execute(
        'SELECT username, phone_number FROM users WHERE telegram_id = ?',
        (telegram_id,)
    ).fetchone()
    
    conn.close()
    
    # Отправляем уведомление выбранному водителю через webhook
    try:
        from webhook_client import notify_auction_complete
        
        notify_auction_complete(
            order_id=order_id,
            winner_telegram_id=bid['driver_telegram_id'],
            winner_user_id=bid['driver_id'],
            winner_username=bid['driver_username'],
            winning_price=bid['price'],
            cargo_description=order['cargo_description'],
            delivery_address=order['delivery_address'],
            customer_user_id=telegram_id,
            customer_username=customer['username'] if customer else None,
            customer_phone=customer['phone_number'] if customer else '',
            driver_phone=bid['driver_phone']
        )
    except Exception as e:
        logger.error(f"Failed to send webhook notification: {e}")
    
    return jsonify({
        'success': True,
        'message': 'Winner selected, order moved to in_progress',
        'winner': {
            'driver_id': bid['driver_id'],
            'driver_name': bid['driver_name'],
            'price': bid['price']
        }
    })

@app.route('/api/debug/db-info', methods=['GET'])
def debug_db_info():
    """Debug endpoint для проверки БД"""
    try:
        conn = get_db_connection()
        
        # Проверяем путь к БД
        db_path = DATABASE_PATH
        
        # Считаем пользователей
        users_count = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count']
        
        # Получаем список всех пользователей
        users = conn.execute('SELECT telegram_id, name, role, phone_number FROM users').fetchall()
        users_list = [dict(u) for u in users]
        
        # Считаем заказы
        orders_count = conn.execute('SELECT COUNT(*) as count FROM orders').fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'database_path': db_path,
            'users_count': users_count,
            'users': users_list,
            'orders_count': orders_count,
            'status': 'ok'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'database_path': DATABASE_PATH
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
