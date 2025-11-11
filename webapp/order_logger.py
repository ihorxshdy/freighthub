"""
Утилита для логирования изменений заказов
"""
import sqlite3
from datetime import datetime
from flask import request

def log_order_change(conn, order_id, user_id, action, description=None, 
                     field_name=None, old_value=None, new_value=None):
    """
    Логировать изменение заказа
    
    Args:
        conn: Подключение к базе данных
        order_id: ID заказа
        user_id: ID пользователя (может быть None для системных действий)
        action: Тип действия (created, updated, status_changed, bid_added, winner_selected, etc.)
        description: Описание изменения
        field_name: Имя измененного поля
        old_value: Старое значение
        new_value: Новое значение
    """
    # Получаем информацию о пользователе
    user_telegram_id = None
    user_name = None
    user_role = None
    
    if user_id:
        user = conn.execute(
            'SELECT telegram_id, name, role FROM users WHERE id = ?',
            (user_id,)
        ).fetchone()
        
        if user:
            user_telegram_id = user[0]
            user_name = user[1]
            user_role = user[2]
    
    # Получаем информацию о заказе и сторонах
    order_info = conn.execute(
        '''SELECT 
            o.customer_id,
            c.telegram_id as customer_telegram_id,
            c.name as customer_name,
            c.phone_number as customer_phone,
            o.winner_driver_id,
            d.telegram_id as driver_telegram_id,
            d.name as driver_name,
            d.phone_number as driver_phone
        FROM orders o
        LEFT JOIN users c ON o.customer_id = c.id
        LEFT JOIN users d ON o.winner_driver_id = d.id
        WHERE o.id = ?''',
        (order_id,)
    ).fetchone()
    
    customer_id = None
    customer_telegram_id = None
    customer_name = None
    customer_phone = None
    driver_id = None
    driver_telegram_id = None
    driver_name = None
    driver_phone = None
    
    if order_info:
        customer_id = order_info[0]
        customer_telegram_id = order_info[1]
        customer_name = order_info[2]
        customer_phone = order_info[3]
        driver_id = order_info[4]
        driver_telegram_id = order_info[5]
        driver_name = order_info[6]
        driver_phone = order_info[7]
    
    # Получаем IP адрес и User-Agent из запроса (если доступен)
    try:
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None
    except:
        ip_address = None
        user_agent = None
    
    # Сохраняем запись в историю
    conn.execute(
        '''INSERT INTO order_history (
            order_id, user_id, user_telegram_id, user_name, user_role,
            action, field_name, old_value, new_value, description,
            ip_address, user_agent, created_at,
            customer_id, customer_telegram_id, customer_name, customer_phone,
            driver_id, driver_telegram_id, driver_name, driver_phone
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            order_id, user_id, user_telegram_id, user_name, user_role,
            action, field_name, old_value, new_value, description,
            ip_address, user_agent, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            customer_id, customer_telegram_id, customer_name, customer_phone,
            driver_id, driver_telegram_id, driver_name, driver_phone
        )
    )
    conn.commit()

def get_order_history(conn, order_id=None, user_id=None, limit=100):
    """
    Получить историю изменений
    
    Args:
        conn: Подключение к базе данных
        order_id: Фильтр по ID заказа (опционально)
        user_id: Фильтр по ID пользователя (опционально)
        limit: Максимальное количество записей
        
    Returns:
        Список записей истории
    """
    query = 'SELECT * FROM v_order_history WHERE 1=1'
    params = []
    
    if order_id:
        query += ' AND order_id = ?'
        params.append(order_id)
    
    if user_id:
        query += ' AND user_id = ?'
        params.append(user_id)
    
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    
    return [{
        'id': row[0],
        'order_id': row[1],
        'user_id': row[2],
        'user_telegram_id': row[3],
        'user_name': row[4],
        'user_role': row[5],
        'action': row[6],
        'field_name': row[7],
        'old_value': row[8],
        'new_value': row[9],
        'description': row[10],
        'ip_address': row[11],
        'user_agent': row[12],
        'created_at': row[13],
        'customer_id': row[14],
        'order_status': row[15],
        'truck_type': row[16],
        'pickup_address': row[17],
        'delivery_address': row[18],
        'customer_name': row[19],
        'customer_telegram_id': row[20]
    } for row in rows]

# Константы для типов действий
ACTION_CREATED = 'created'
ACTION_UPDATED = 'updated'
ACTION_STATUS_CHANGED = 'status_changed'
ACTION_BID_ADDED = 'bid_added'
ACTION_BID_UPDATED = 'bid_updated'
ACTION_WINNER_SELECTED = 'winner_selected'
ACTION_CONFIRMED = 'confirmed'
ACTION_CONFIRMED_CUSTOMER = 'confirmed_customer'
ACTION_CONFIRMED_DRIVER = 'confirmed_driver'
ACTION_CANCELLED = 'cancelled'
ACTION_COMPLETED = 'completed'
ACTION_PRICE_CHANGED = 'price_changed'
