"""
API для расширенной системы отзывов
Включает детальные критерии оценки, комплименты и публичные комментарии
"""
from flask import jsonify, request
import json
from datetime import datetime

# Доступные значки/комплименты
AVAILABLE_BADGES = {
    'fast_delivery': 'Быстрая доставка',
    'friendly': 'Приветливый',
    'fair_price': 'Честная цена',
    'reliable': 'Надёжный'
}

def setup_review_routes(app, get_db_connection):
    """Регистрация маршрутов для отзывов"""
    
    @app.route('/api/reviews/create', methods=['POST'])
    def create_detailed_review():
        """Создание детального отзыва с критериями и комплиментами"""
        data = request.json
        
        required_fields = ['order_id', 'reviewer_telegram_id', 'reviewee_telegram_id', 'rating']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        conn = get_db_connection()
        
        try:
            # Получаем ID пользователей
            reviewer = conn.execute(
                'SELECT id FROM users WHERE telegram_id = ?',
                (data['reviewer_telegram_id'],)
            ).fetchone()
            
            reviewee = conn.execute(
                'SELECT id FROM users WHERE telegram_id = ?',
                (data['reviewee_telegram_id'],)
            ).fetchone()
            
            if not reviewer or not reviewee:
                return jsonify({'error': 'User not found'}), 404
            
            # Проверяем что заказ существует и завершен
            order = conn.execute(
                'SELECT * FROM orders WHERE id = ? AND status = ?',
                (data['order_id'], 'completed')
            ).fetchone()
            
            if not order:
                return jsonify({'error': 'Order not found or not completed'}), 404
            
            # Проверяем что отзыв еще не оставлен
            existing = conn.execute(
                'SELECT id FROM reviews WHERE order_id = ? AND reviewer_id = ? AND reviewee_id = ?',
                (data['order_id'], reviewer['id'], reviewee['id'])
            ).fetchone()
            
            if existing:
                return jsonify({'error': 'Review already exists'}), 409
            
            # Валидация комплиментов
            badges = data.get('badges', [])
            if badges:
                invalid_badges = [b for b in badges if b not in AVAILABLE_BADGES]
                if invalid_badges:
                    return jsonify({'error': f'Invalid badges: {invalid_badges}'}), 400
            
            badges_json = json.dumps(badges) if badges else None
            
            # Создаём отзыв
            cursor = conn.execute(
                '''INSERT INTO reviews (
                    order_id, reviewer_id, reviewee_id, rating, comment,
                    punctuality_rating, quality_rating, professionalism_rating,
                    communication_rating, vehicle_condition_rating,
                    badges, is_public, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    data['order_id'],
                    reviewer['id'],
                    reviewee['id'],
                    data['rating'],
                    data.get('comment'),
                    data.get('punctuality_rating'),
                    data.get('quality_rating'),
                    data.get('professionalism_rating'),
                    data.get('communication_rating'),
                    data.get('vehicle_condition_rating'),
                    badges_json,
                    data.get('is_public', True),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            
            conn.commit()
            review_id = cursor.lastrowid
            
            return jsonify({
                'success': True,
                'review_id': review_id,
                'message': 'Review created successfully'
            }), 201
            
        except Exception as e:
            conn.rollback()
            return jsonify({'error': str(e)}), 500
            
        finally:
            conn.close()
    
    @app.route('/api/reviews/user/<int:telegram_id>', methods=['GET'])
    def get_detailed_user_reviews(telegram_id):
        """Получить все отзывы о пользователе с детальными критериями"""
        conn = get_db_connection()
        
        try:
            # Получаем ID пользователя
            user = conn.execute(
                'SELECT id, name, role FROM users WHERE telegram_id = ?',
                (telegram_id,)
            ).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Получаем все публичные отзывы
            reviews = conn.execute(
                '''SELECT 
                    r.*,
                    reviewer.name as reviewer_name,
                    reviewer.telegram_id as reviewer_telegram_id,
                    o.id as order_id
                FROM reviews r
                JOIN users reviewer ON r.reviewer_id = reviewer.id
                JOIN orders o ON r.order_id = o.id
                WHERE r.reviewee_id = ? AND r.is_public = 1
                ORDER BY r.created_at DESC''',
                (user['id'],)
            ).fetchall()
            
            # Подсчитываем статистику
            stats = conn.execute(
                '''SELECT 
                    COUNT(*) as total_reviews,
                    AVG(rating) as avg_rating,
                    AVG(punctuality_rating) as avg_punctuality,
                    AVG(quality_rating) as avg_quality,
                    AVG(professionalism_rating) as avg_professionalism,
                    AVG(communication_rating) as avg_communication,
                    AVG(vehicle_condition_rating) as avg_vehicle_condition
                FROM reviews
                WHERE reviewee_id = ? AND is_public = 1''',
                (user['id'],)
            ).fetchone()
            
            # Подсчитываем комплименты
            all_badges = []
            for review in reviews:
                if review['badges']:
                    all_badges.extend(json.loads(review['badges']))
            
            badge_counts = {}
            for badge in all_badges:
                badge_counts[badge] = badge_counts.get(badge, 0) + 1
            
            # Топ-3 комплимента
            top_badges = sorted(badge_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Форматируем отзывы
            reviews_list = []
            for review in reviews:
                review_dict = dict(review)
                if review_dict['badges']:
                    review_dict['badges'] = json.loads(review_dict['badges'])
                reviews_list.append(review_dict)
            
            return jsonify({
                'user': {
                    'telegram_id': telegram_id,
                    'name': user['name'],
                    'role': user['role']
                },
                'statistics': {
                    'total_reviews': stats['total_reviews'],
                    'average_rating': round(stats['avg_rating'], 1) if stats['avg_rating'] else 0,
                    'criteria_averages': {
                        'punctuality': round(stats['avg_punctuality'], 1) if stats['avg_punctuality'] else None,
                        'quality': round(stats['avg_quality'], 1) if stats['avg_quality'] else None,
                        'professionalism': round(stats['avg_professionalism'], 1) if stats['avg_professionalism'] else None,
                        'communication': round(stats['avg_communication'], 1) if stats['avg_communication'] else None,
                        'vehicle_condition': round(stats['avg_vehicle_condition'], 1) if stats['avg_vehicle_condition'] else None
                    },
                    'top_badges': [
                        {
                            'badge': badge,
                            'label': AVAILABLE_BADGES.get(badge, badge),
                            'count': count
                        }
                        for badge, count in top_badges
                    ]
                },
                'reviews': reviews_list
            })
            
        finally:
            conn.close()
    
    @app.route('/api/reviews/<int:review_id>/respond', methods=['POST'])
    def respond_to_review(review_id):
        """Ответить на отзыв (для владельца отзыва)"""
        data = request.json
        
        if 'telegram_id' not in data or 'response_text' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        
        try:
            # Получаем отзыв и проверяем что пользователь - тот кого оценили
            review = conn.execute(
                '''SELECT r.*, u.telegram_id as reviewee_telegram_id
                FROM reviews r
                JOIN users u ON r.reviewee_id = u.id
                WHERE r.id = ?''',
                (review_id,)
            ).fetchone()
            
            if not review:
                return jsonify({'error': 'Review not found'}), 404
            
            if review['reviewee_telegram_id'] != data['telegram_id']:
                return jsonify({'error': 'Unauthorized'}), 403
            
            # Обновляем отзыв с ответом
            conn.execute(
                '''UPDATE reviews 
                SET response_text = ?, response_at = ?
                WHERE id = ?''',
                (
                    data['response_text'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    review_id
                )
            )
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': 'Response added successfully'
            })
            
        finally:
            conn.close()
    
    @app.route('/api/reviews/<int:review_id>/helpful', methods=['POST'])
    def mark_review_helpful(review_id):
        """Отметить отзыв как полезный/бесполезный"""
        data = request.json
        
        if 'telegram_id' not in data or 'is_helpful' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        
        try:
            # Получаем ID пользователя
            user = conn.execute(
                'SELECT id FROM users WHERE telegram_id = ?',
                (data['telegram_id'],)
            ).fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Проверяем что отзыв существует
            review = conn.execute(
                'SELECT id FROM reviews WHERE id = ?',
                (review_id,)
            ).fetchone()
            
            if not review:
                return jsonify({'error': 'Review not found'}), 404
            
            # Добавляем/обновляем оценку полезности
            conn.execute(
                '''INSERT OR REPLACE INTO review_helpfulness 
                (review_id, user_id, is_helpful, created_at)
                VALUES (?, ?, ?, ?)''',
                (
                    review_id,
                    user['id'],
                    data['is_helpful'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            
            # Обновляем счётчики
            helpful_count = conn.execute(
                'SELECT COUNT(*) as count FROM review_helpfulness WHERE review_id = ? AND is_helpful = 1',
                (review_id,)
            ).fetchone()['count']
            
            not_helpful_count = conn.execute(
                'SELECT COUNT(*) as count FROM review_helpfulness WHERE review_id = ? AND is_helpful = 0',
                (review_id,)
            ).fetchone()['count']
            
            conn.execute(
                'UPDATE reviews SET helpful_count = ?, not_helpful_count = ? WHERE id = ?',
                (helpful_count, not_helpful_count, review_id)
            )
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'helpful_count': helpful_count,
                'not_helpful_count': not_helpful_count
            })
            
        finally:
            conn.close()
    
    @app.route('/api/reviews/badges', methods=['GET'])
    def get_available_badges():
        """Получить список доступных комплиментов"""
        return jsonify({
            'badges': [
                {'id': key, 'label': value}
                for key, value in AVAILABLE_BADGES.items()
            ]
        })

    return app
