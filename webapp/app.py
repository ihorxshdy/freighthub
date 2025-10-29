"""
Flask приложение для Telegram Mini App
"""
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import sqlite3
from datetime import datetime

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
    return render_template('index.html')

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
    print(f"📊 Total users in DB: {total_users['count']}")
    
    # Покажем всех пользователей для отладки
    all_users = conn.execute('SELECT telegram_id, name, role FROM users LIMIT 10').fetchall()
    print(f"👥 Users in DB: {[dict(u) for u in all_users]}")
    
    user = conn.execute(
        'SELECT * FROM users WHERE telegram_id = ?',
        (telegram_id,)
    ).fetchone()
    conn.close()
    
    if user:
        print(f"✅ User found: {dict(user)}")
        return jsonify(dict_from_row(user))
    
    print(f"❌ User NOT found for telegram_id={telegram_id}")
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
    
    # Получаем все заказы
    orders = conn.execute(
        '''SELECT o.*, 
                  COUNT(DISTINCT b.id) as bids_count,
                  MIN(b.bid_amount) as min_bid_price
           FROM orders o
           LEFT JOIN bids b ON o.id = b.order_id AND b.status = 'pending'
           WHERE o.customer_id = ?
           GROUP BY o.id
           ORDER BY o.created_at DESC''',
        (user['id'],)
    ).fetchall()
    
    conn.close()
    
    # Группируем по статусам
    result = {
        'searching': [],  # Идет поиск исполнителей
        'created': [],    # Созданные заявки (без предложений)
        'completed': []   # Завершенные заявки
    }
    
    for order in orders:
        order_data = dict_from_row(order)
        
        if order_data['status'] == 'completed' or order_data['status'] == 'cancelled':
            result['completed'].append(order_data)
        elif order_data['bids_count'] > 0:
            result['searching'].append(order_data)
        else:
            result['created'].append(order_data)
    
    return jsonify(result)

@app.route('/api/orders', methods=['POST'])
def create_order():
    """Создание новой заявки"""
    telegram_id = request.args.get('telegram_id')
    data = request.json
    
    print(f"📝 Create order request: telegram_id={telegram_id}, data={data}")
    
    if not telegram_id:
        print("❌ Error: telegram_id missing")
        return jsonify({'error': 'telegram_id required'}), 400
    
    required_fields = ['pickup_location', 'delivery_location', 'description', 'truck_type_id']
    if not all(field in data for field in required_fields):
        missing = [f for f in required_fields if f not in data]
        print(f"❌ Error: Missing fields: {missing}")
        return jsonify({'error': 'Missing required fields', 'missing': missing}), 400
    
    try:
        conn = get_db_connection()
        print(f"✅ DB connected: {DATABASE_PATH}")
        
        # Получаем ID пользователя (по схеме БД бота - используем id, не telegram_id)
        user = conn.execute(
            'SELECT id FROM users WHERE telegram_id = ?',
            (telegram_id,)
        ).fetchone()
        
        if not user:
            conn.close()
            print(f"❌ Error: User not found for telegram_id={telegram_id}")
            return jsonify({'error': 'User not found'}), 404
        
        print(f"✅ User found: id={user['id']}")
        
        # Expires_at - через 30 минут от создания (как в боте)
        from datetime import timedelta
        expires_at = (datetime.now() + timedelta(minutes=30)).isoformat()
        
        # Создаем заказ по схеме БД бота
        cursor = conn.execute(
            '''INSERT INTO orders (
                customer_id, truck_type, cargo_description, delivery_address,
                status, created_at, expires_at,
                pickup_address, pickup_time, delivery_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
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
                data.get('delivery_time')  # delivery_time
            )
        )
        
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"✅ Order created: id={order_id}")
        
        # Отправляем webhook уведомление боту
        try:
            # Получаем название типа грузовика
            from truck_config import TRUCK_TYPES
            truck_type_name = TRUCK_TYPES.get(data['truck_type_id'], data['truck_type_id'])
            
            print(f"📤 Sending webhook to bot...")
            notify_new_order(
                order_id=order_id,
                truck_type=truck_type_name,
                cargo_description=data['description'],
                delivery_address=data['delivery_location'],
                max_price=data.get('price', 0)
            )
            print(f"✅ Webhook sent successfully")
        except Exception as e:
            print(f"⚠️ Webhook error (non-critical): {e}")
            # Не прерываем выполнение, если webhook не сработал
        
        return jsonify({'id': order_id, 'message': 'Order created successfully'})
    
    except Exception as e:
        print(f"❌ Fatal error creating order: {e}")
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
        'open': [],       # Открытые заявки (можно сделать предложение)
        'my_bids': [],    # Заявки с моими предложениями
        'won': [],        # Выигранные заявки
        'closed': []      # Закрытые заявки
    }
    
    # Получаем открытые заявки (без предложений от этого водителя)
    open_orders = conn.execute(
        '''SELECT o.*, 
                  COUNT(DISTINCT b.id) as bids_count,
                  MIN(b.bid_amount) as min_bid_price
           FROM orders o
           LEFT JOIN bids b ON o.id = b.order_id AND b.status = 'pending'
           WHERE o.status = 'active'
             AND o.id NOT IN (
                 SELECT order_id FROM bids WHERE driver_id = ? AND status = 'pending'
             )
           GROUP BY o.id
           ORDER BY o.created_at DESC
           LIMIT 50''',
        (user['id'],)
    ).fetchall()
    
    # Заявки с предложениями от водителя
    my_bids_orders = conn.execute(
        '''SELECT o.*, b.bid_amount as my_bid_price, b.id as bid_id,
                  COUNT(DISTINCT b2.id) as total_bids,
                  MIN(b2.bid_amount) as min_bid_price
           FROM orders o
           JOIN bids b ON o.id = b.order_id
           LEFT JOIN bids b2 ON o.id = b2.order_id AND b2.status = 'pending'
           WHERE b.driver_id = ? 
             AND b.status = 'pending'
             AND o.status = 'active'
           GROUP BY o.id
           ORDER BY o.created_at DESC''',
        (user['id'],)
    ).fetchall()
    
    # Выигранные заявки
    won_orders = conn.execute(
        '''SELECT o.*, b.bid_amount as my_bid_price
           FROM orders o
           JOIN bids b ON o.id = b.order_id
           WHERE b.driver_id = ? 
             AND b.status = 'won'
           ORDER BY o.created_at DESC''',
        (user['id'],)
    ).fetchall()
    
    # Закрытые заявки
    closed_orders = conn.execute(
        '''SELECT o.*, b.bid_amount as my_bid_price, b.status as bid_status
           FROM orders o
           LEFT JOIN bids b ON o.id = b.order_id AND b.driver_id = ?
           WHERE (o.status = 'completed' OR o.status = 'cancelled')
             AND b.id IS NOT NULL
           ORDER BY o.created_at DESC
           LIMIT 20''',
        (user['id'],)
    ).fetchall()
    
    conn.close()
    
    result['open'] = [dict_from_row(order) for order in open_orders]
    result['my_bids'] = [dict_from_row(order) for order in my_bids_orders]
    result['won'] = [dict_from_row(order) for order in won_orders]
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
        'SELECT id FROM bids WHERE order_id = ? AND driver_id = ? AND status = "pending"',
        (data['order_id'], user['id'])
    ).fetchone()
    
    if existing:
        conn.close()
        return jsonify({'error': 'Bid already exists'}), 400
    
    # Создаем предложение
    cursor = conn.execute(
        '''INSERT INTO bids (order_id, driver_id, bid_amount, status, created_at)
           VALUES (?, ?, ?, ?, ?)''',
        (
            data['order_id'],
            user['id'],
            data['price'],
            'pending',
            datetime.now().isoformat()
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
