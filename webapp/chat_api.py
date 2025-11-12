"""
API для системы чата между заказчиком и водителем
"""
from flask import jsonify, request
import sqlite3
from datetime import datetime

def setup_chat_routes(app, get_db_connection):
    """Регистрация маршрутов для чата"""
    
    @app.route('/api/orders/<int:order_id>/messages', methods=['GET'])
    def get_order_messages(order_id):
        """Получение списка сообщений для заказа"""
        telegram_id = (request.args.get('telegram_id') or
                      request.headers.get('Telegram-Id') or 
                      request.headers.get('telegram-id'))
        
        if not telegram_id:
            return jsonify({'error': 'telegram_id required'}), 400
        
        telegram_id = int(telegram_id)
        conn = get_db_connection()
        
        try:
            # Проверяем что пользователь - участник заказа
            user = conn.execute(
                'SELECT id, role FROM users WHERE telegram_id = ?',
                (telegram_id,)
            ).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            order = conn.execute(
                'SELECT customer_id, winner_driver_id, status FROM orders WHERE id = ?',
                (order_id,)
            ).fetchone()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            # Проверяем доступ
            if user['id'] != order['customer_id'] and user['id'] != order['winner_driver_id']:
                return jsonify({'error': 'Access denied'}), 403
            
            # Получаем сообщения
            messages = conn.execute(
                '''SELECT m.id, m.sender_id, m.message_text, m.created_at,
                          m.read_by_customer, m.read_by_driver,
                          u.name as sender_name, u.role as sender_role
                   FROM order_messages m
                   JOIN users u ON m.sender_id = u.id
                   WHERE m.order_id = ?
                   ORDER BY m.created_at ASC''',
                (order_id,)
            ).fetchall()
            
            result = []
            for msg in messages:
                result.append({
                    'id': msg['id'],
                    'sender_id': msg['sender_id'],
                    'sender_name': msg['sender_name'],
                    'sender_role': msg['sender_role'],
                    'message_text': msg['message_text'],
                    'created_at': msg['created_at'],
                    'read_by_customer': bool(msg['read_by_customer']),
                    'read_by_driver': bool(msg['read_by_driver']),
                    'is_mine': msg['sender_id'] == user['id']
                })
            
            # Подсчитываем непрочитанные сообщения
            unread_count = 0
            if user['role'] == 'customer':
                unread_count = sum(1 for msg in messages if not msg['read_by_customer'] and msg['sender_id'] != user['id'])
            else:
                unread_count = sum(1 for msg in messages if not msg['read_by_driver'] and msg['sender_id'] != user['id'])
            
            return jsonify({
                'messages': result,
                'unread_count': unread_count
            })
            
        finally:
            conn.close()
    
    @app.route('/api/orders/<int:order_id>/messages', methods=['POST'])
    def send_message(order_id):
        """Отправка сообщения в чат"""
        telegram_id = (request.json.get('telegram_id') or
                      request.headers.get('Telegram-Id') or 
                      request.headers.get('telegram-id'))
        
        if not telegram_id:
            return jsonify({'error': 'telegram_id required'}), 400
        
        data = request.json
        message_text = data.get('message_text', '').strip()
        
        if not message_text:
            return jsonify({'error': 'Message text required'}), 400
        
        if len(message_text) > 2000:
            return jsonify({'error': 'Message too long (max 2000 characters)'}), 400
        
        telegram_id = int(telegram_id)
        conn = get_db_connection()
        
        try:
            # Проверяем пользователя
            user = conn.execute(
                'SELECT id, role, name FROM users WHERE telegram_id = ?',
                (telegram_id,)
            ).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Проверяем заказ и доступ
            order = conn.execute(
                '''SELECT customer_id, winner_driver_id, status,
                          c.telegram_id as customer_telegram_id,
                          d.telegram_id as driver_telegram_id,
                          c.name as customer_name,
                          d.name as driver_name
                   FROM orders o
                   LEFT JOIN users c ON o.customer_id = c.id
                   LEFT JOIN users d ON o.winner_driver_id = d.id
                   WHERE o.id = ?''',
                (order_id,)
            ).fetchone()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            if user['id'] != order['customer_id'] and user['id'] != order['winner_driver_id']:
                return jsonify({'error': 'Access denied'}), 403
            
            # Создаем сообщение
            cursor = conn.execute(
                '''INSERT INTO order_messages 
                   (order_id, sender_id, message_text, read_by_customer, read_by_driver)
                   VALUES (?, ?, ?, ?, ?)''',
                (order_id, user['id'], message_text,
                 user['role'] == 'customer',  # Если отправитель - заказчик, то он уже прочитал
                 user['role'] == 'driver')    # Если отправитель - водитель, то он уже прочитал
            )
            
            message_id = cursor.lastrowid
            conn.commit()
            
            # Получаем созданное сообщение
            message = conn.execute(
                '''SELECT id, sender_id, message_text, created_at,
                          read_by_customer, read_by_driver
                   FROM order_messages WHERE id = ?''',
                (message_id,)
            ).fetchone()
            
            # Отправляем уведомление получателю через вебхук
            try:
                recipient_telegram_id = None
                recipient_name = None
                
                if user['role'] == 'customer':
                    # Заказчик пишет водителю
                    recipient_telegram_id = order['driver_telegram_id']
                    recipient_name = order['driver_name']
                else:
                    # Водитель пишет заказчику
                    recipient_telegram_id = order['customer_telegram_id']
                    recipient_name = order['customer_name']
                
                if recipient_telegram_id:
                    # Импортируем webhook_client для отправки уведомлений
                    from webhook_client import send_webhook_notification
                    
                    notification_data = {
                        'type': 'new_chat_message',
                        'order_id': order_id,
                        'sender_name': user['name'],
                        'sender_role': user['role'],
                        'message_text': message_text[:100] + ('...' if len(message_text) > 100 else ''),
                        'recipient_telegram_id': recipient_telegram_id
                    }
                    
                    send_webhook_notification(notification_data)
            except Exception as e:
                print(f"Warning: Failed to send notification: {e}")
                # Не падаем, если уведомление не отправилось
            
            return jsonify({
                'success': True,
                'message': {
                    'id': message['id'],
                    'sender_id': message['sender_id'],
                    'sender_name': user['name'],
                    'sender_role': user['role'],
                    'message_text': message['message_text'],
                    'created_at': message['created_at'],
                    'read_by_customer': bool(message['read_by_customer']),
                    'read_by_driver': bool(message['read_by_driver']),
                    'is_mine': True
                }
            }), 201
            
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()
    
    @app.route('/api/orders/<int:order_id>/messages/read', methods=['POST'])
    def mark_messages_read(order_id):
        """Отметить сообщения как прочитанные"""
        telegram_id = (request.json.get('telegram_id') or
                      request.headers.get('Telegram-Id') or 
                      request.headers.get('telegram-id'))
        
        if not telegram_id:
            return jsonify({'error': 'telegram_id required'}), 400
        
        telegram_id = int(telegram_id)
        conn = get_db_connection()
        
        try:
            # Проверяем пользователя
            user = conn.execute(
                'SELECT id, role FROM users WHERE telegram_id = ?',
                (telegram_id,)
            ).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Проверяем заказ и доступ
            order = conn.execute(
                'SELECT customer_id, winner_driver_id FROM orders WHERE id = ?',
                (order_id,)
            ).fetchone()
            
            if not order:
                return jsonify({'error': 'Order not found'}), 404
            
            if user['id'] != order['customer_id'] and user['id'] != order['winner_driver_id']:
                return jsonify({'error': 'Access denied'}), 403
            
            # Отмечаем сообщения как прочитанные
            if user['role'] == 'customer':
                conn.execute(
                    '''UPDATE order_messages 
                       SET read_by_customer = TRUE 
                       WHERE order_id = ? AND sender_id != ?''',
                    (order_id, user['id'])
                )
            else:
                conn.execute(
                    '''UPDATE order_messages 
                       SET read_by_driver = TRUE 
                       WHERE order_id = ? AND sender_id != ?''',
                    (order_id, user['id'])
                )
            
            conn.commit()
            
            return jsonify({'success': True})
            
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            conn.close()
    
    @app.route('/api/orders/unread-messages-count', methods=['GET'])
    def get_unread_messages_count():
        """Получить общее количество непрочитанных сообщений по всем заказам"""
        telegram_id = (request.args.get('telegram_id') or
                      request.headers.get('Telegram-Id') or 
                      request.headers.get('telegram-id'))
        
        if not telegram_id:
            return jsonify({'error': 'telegram_id required'}), 400
        
        telegram_id = int(telegram_id)
        conn = get_db_connection()
        
        try:
            # Проверяем пользователя
            user = conn.execute(
                'SELECT id, role FROM users WHERE telegram_id = ?',
                (telegram_id,)
            ).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Подсчитываем непрочитанные сообщения
            if user['role'] == 'customer':
                # Для заказчика - непрочитанные сообщения в его заказах
                result = conn.execute(
                    '''SELECT order_id, COUNT(*) as unread_count
                       FROM order_messages m
                       JOIN orders o ON m.order_id = o.id
                       WHERE o.customer_id = ? 
                       AND m.read_by_customer = FALSE
                       AND m.sender_id != ?
                       GROUP BY order_id''',
                    (user['id'], user['id'])
                ).fetchall()
            else:
                # Для водителя - непрочитанные сообщения в заказах где он исполнитель
                result = conn.execute(
                    '''SELECT order_id, COUNT(*) as unread_count
                       FROM order_messages m
                       JOIN orders o ON m.order_id = o.id
                       WHERE o.winner_driver_id = ? 
                       AND m.read_by_driver = FALSE
                       AND m.sender_id != ?
                       GROUP BY order_id''',
                    (user['id'], user['id'])
                ).fetchall()
            
            unread_by_order = {row['order_id']: row['unread_count'] for row in result}
            total_unread = sum(unread_by_order.values())
            
            return jsonify({
                'total_unread': total_unread,
                'unread_by_order': unread_by_order
            })
            
        finally:
            conn.close()
