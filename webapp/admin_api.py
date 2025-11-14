"""
API для управления организациями и инвайт-кодами (админ панель)
"""
from flask import Blueprint, request, jsonify
import sqlite3
import secrets
import string
from datetime import datetime, timedelta

def setup_admin_routes(app, get_db_connection):
    """Настройка маршрутов админ панели"""
    
    # Список админов (telegram_id)
    ADMIN_IDS = [643813567]  # Замените на ваш telegram_id
    
    def is_admin(telegram_id):
        """Проверка прав администратора"""
        return int(telegram_id) in ADMIN_IDS
    
    # ========== ОРГАНИЗАЦИИ ==========
    
    @app.route('/api/admin/organizations', methods=['GET'])
    def get_organizations():
        """Получить список всех организаций"""
        telegram_id = request.args.get('telegram_id')
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        orgs = conn.execute('''
            SELECT o.*, 
                   COUNT(DISTINCT u.id) as users_count,
                   COUNT(DISTINCT ic.id) as total_codes,
                   COUNT(DISTINCT CASE WHEN ic.used_by_telegram_id IS NOT NULL THEN ic.id END) as used_codes
            FROM organizations o
            LEFT JOIN users u ON o.id = u.organization_id
            LEFT JOIN invite_codes ic ON o.id = ic.organization_id
            GROUP BY o.id
            ORDER BY o.created_at DESC
        ''').fetchall()
        conn.close()
        
        return jsonify([dict(org) for org in orgs])
    
    @app.route('/api/admin/organizations', methods=['POST'])
    def create_organization():
        """Создать новую организацию"""
        telegram_id = request.args.get('telegram_id')
        data = request.json
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        name = data.get('name')
        description = data.get('description', '')
        
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        
        conn = get_db_connection()
        try:
            cursor = conn.execute(
                'INSERT INTO organizations (name, description) VALUES (?, ?)',
                (name, description)
            )
            org_id = cursor.lastrowid
            conn.commit()
            
            org = conn.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
            conn.close()
            
            return jsonify({'success': True, 'organization': dict(org)}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Organization with this name already exists'}), 409
    
    @app.route('/api/admin/organizations/<int:org_id>', methods=['PUT'])
    def update_organization(org_id):
        """Обновить организацию"""
        telegram_id = request.args.get('telegram_id')
        data = request.json
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        
        updates = []
        params = []
        
        if 'name' in data:
            updates.append('name = ?')
            params.append(data['name'])
        if 'description' in data:
            updates.append('description = ?')
            params.append(data['description'])
        if 'is_active' in data:
            updates.append('is_active = ?')
            params.append(1 if data['is_active'] else 0)
        
        if updates:
            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(org_id)
            
            conn.execute(
                f"UPDATE organizations SET {', '.join(updates)} WHERE id = ?",
                params
            )
            conn.commit()
        
        org = conn.execute('SELECT * FROM organizations WHERE id = ?', (org_id,)).fetchone()
        conn.close()
        
        if org:
            return jsonify({'success': True, 'organization': dict(org)})
        return jsonify({'error': 'Organization not found'}), 404
    
    @app.route('/api/admin/organizations/<int:org_id>', methods=['DELETE'])
    def delete_organization(org_id):
        """Удалить организацию"""
        telegram_id = request.args.get('telegram_id')
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        conn.execute('DELETE FROM organizations WHERE id = ?', (org_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    # ========== ИНВАЙТ-КОДЫ ==========
    
    def generate_invite_code(length=8):
        """Генерация уникального инвайт-кода"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))
    
    @app.route('/api/admin/invite-codes', methods=['GET'])
    def get_invite_codes():
        """Получить инвайт-коды (все или по организации)"""
        telegram_id = request.args.get('telegram_id')
        org_id = request.args.get('organization_id')
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        
        if org_id:
            codes = conn.execute('''
                SELECT ic.*, o.name as organization_name, u.name as used_by_name
                FROM invite_codes ic
                JOIN organizations o ON ic.organization_id = o.id
                LEFT JOIN users u ON ic.used_by_telegram_id = u.telegram_id
                WHERE ic.organization_id = ?
                ORDER BY ic.created_at DESC
            ''', (org_id,)).fetchall()
        else:
            codes = conn.execute('''
                SELECT ic.*, o.name as organization_name, u.name as used_by_name
                FROM invite_codes ic
                JOIN organizations o ON ic.organization_id = o.id
                LEFT JOIN users u ON ic.used_by_telegram_id = u.telegram_id
                ORDER BY ic.created_at DESC
            ''').fetchall()
        
        conn.close()
        return jsonify([dict(code) for code in codes])
    
    @app.route('/api/admin/invite-codes/generate', methods=['POST'])
    def generate_invite_codes():
        """Генерация нескольких инвайт-кодов для организации"""
        telegram_id = request.args.get('telegram_id')
        data = request.json
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        org_id = data.get('organization_id')
        count = data.get('count', 1)
        expires_days = data.get('expires_days')  # Необязательно
        
        if not org_id:
            return jsonify({'error': 'organization_id is required'}), 400
        
        if count < 1 or count > 100:
            return jsonify({'error': 'Count must be between 1 and 100'}), 400
        
        conn = get_db_connection()
        
        # Проверяем существование организации
        org = conn.execute('SELECT id FROM organizations WHERE id = ?', (org_id,)).fetchone()
        if not org:
            conn.close()
            return jsonify({'error': 'Organization not found'}), 404
        
        generated_codes = []
        expires_at = None
        
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        for _ in range(count):
            # Генерируем уникальный код
            while True:
                code = generate_invite_code()
                existing = conn.execute('SELECT id FROM invite_codes WHERE code = ?', (code,)).fetchone()
                if not existing:
                    break
            
            cursor = conn.execute(
                '''INSERT INTO invite_codes (code, organization_id, expires_at) 
                   VALUES (?, ?, ?)''',
                (code, org_id, expires_at)
            )
            
            code_data = conn.execute(
                'SELECT * FROM invite_codes WHERE id = ?',
                (cursor.lastrowid,)
            ).fetchone()
            
            generated_codes.append(dict(code_data))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(generated_codes),
            'codes': generated_codes
        }), 201
    
    @app.route('/api/admin/invite-codes/<int:code_id>', methods=['PUT'])
    def update_invite_code(code_id):
        """Обновить инвайт-код (активировать/деактивировать)"""
        telegram_id = request.args.get('telegram_id')
        data = request.json
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        
        if 'is_active' in data:
            conn.execute(
                'UPDATE invite_codes SET is_active = ? WHERE id = ?',
                (1 if data['is_active'] else 0, code_id)
            )
            conn.commit()
        
        code = conn.execute('SELECT * FROM invite_codes WHERE id = ?', (code_id,)).fetchone()
        conn.close()
        
        if code:
            return jsonify({'success': True, 'code': dict(code)})
        return jsonify({'error': 'Code not found'}), 404
    
    @app.route('/api/admin/invite-codes/<int:code_id>', methods=['DELETE'])
    def delete_invite_code(code_id):
        """Удалить инвайт-код"""
        telegram_id = request.args.get('telegram_id')
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        conn.execute('DELETE FROM invite_codes WHERE id = ?', (code_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    
    # ========== ПРОВЕРКА КОДА (для регистрации) ==========
    
    @app.route('/api/invite-codes/validate', methods=['POST'])
    def validate_invite_code():
        """Проверить валидность инвайт-кода"""
        data = request.json
        code = data.get('code')
        telegram_id = data.get('telegram_id')
        
        if not code or not telegram_id:
            return jsonify({'valid': False, 'error': 'Code and telegram_id required'}), 400
        
        conn = get_db_connection()
        
        invite = conn.execute('''
            SELECT ic.*, o.name as organization_name, o.is_active as org_is_active
            FROM invite_codes ic
            JOIN organizations o ON ic.organization_id = o.id
            WHERE ic.code = ?
        ''', (code.upper(),)).fetchone()
        
        if not invite:
            conn.close()
            return jsonify({'valid': False, 'error': 'Код не найден'})
        
        # Проверки
        if not invite['is_active']:
            conn.close()
            return jsonify({'valid': False, 'error': 'Код деактивирован'})
        
        if not invite['org_is_active']:
            conn.close()
            return jsonify({'valid': False, 'error': 'Организация неактивна'})
        
        if invite['used_by_telegram_id']:
            if invite['used_by_telegram_id'] == telegram_id:
                conn.close()
                return jsonify({'valid': True, 'organization_id': invite['organization_id'], 
                              'organization_name': invite['organization_name'], 'already_used': True})
            else:
                conn.close()
                return jsonify({'valid': False, 'error': 'Код уже использован другим пользователем'})
        
        if invite['expires_at']:
            expires = datetime.fromisoformat(invite['expires_at'])
            if datetime.now() > expires:
                conn.close()
                return jsonify({'valid': False, 'error': 'Срок действия кода истёк'})
        
        conn.close()
        return jsonify({
            'valid': True,
            'organization_id': invite['organization_id'],
            'organization_name': invite['organization_name']
        })
    
    @app.route('/api/invite-codes/use', methods=['POST'])
    def use_invite_code():
        """Использовать инвайт-код (привязать к пользователю)"""
        data = request.json
        code = data.get('code')
        telegram_id = data.get('telegram_id')
        
        if not code or not telegram_id:
            return jsonify({'error': 'Code and telegram_id required'}), 400
        
        conn = get_db_connection()
        
        # Проверяем валидность
        invite = conn.execute('''
            SELECT ic.*, o.is_active as org_is_active
            FROM invite_codes ic
            JOIN organizations o ON ic.organization_id = o.id
            WHERE ic.code = ?
        ''', (code.upper(),)).fetchone()
        
        if not invite or not invite['is_active'] or not invite['org_is_active']:
            conn.close()
            return jsonify({'error': 'Invalid code'}), 400
        
        if invite['used_by_telegram_id'] and invite['used_by_telegram_id'] != telegram_id:
            conn.close()
            return jsonify({'error': 'Code already used'}), 400
        
        # Помечаем код как использованный
        conn.execute('''
            UPDATE invite_codes 
            SET used_by_telegram_id = ?, used_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (telegram_id, invite['id']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'organization_id': invite['organization_id'],
            'invite_code_id': invite['id']
        })
    
    # ========== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ==========
    
    @app.route('/api/admin/users', methods=['GET'])
    def get_users():
        """Получить список всех пользователей"""
        telegram_id = request.args.get('telegram_id')
        org_id = request.args.get('organization_id')
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        
        if org_id:
            users = conn.execute('''
                SELECT u.*, o.name as organization_name, ic.code as invite_code
                FROM users u
                LEFT JOIN organizations o ON u.organization_id = o.id
                LEFT JOIN invite_codes ic ON u.invite_code_id = ic.id
                WHERE u.organization_id = ?
                ORDER BY u.created_at DESC
            ''', (org_id,)).fetchall()
        else:
            users = conn.execute('''
                SELECT u.*, o.name as organization_name, ic.code as invite_code
                FROM users u
                LEFT JOIN organizations o ON u.organization_id = o.id
                LEFT JOIN invite_codes ic ON u.invite_code_id = ic.id
                ORDER BY u.created_at DESC
            ''').fetchall()
        
        conn.close()
        return jsonify([dict(user) for user in users])
    
    @app.route('/api/admin/users/<int:user_telegram_id>', methods=['PUT'])
    def update_user(user_telegram_id):
        """Обновить пользователя (привязка к организации, бан, имя)"""
        telegram_id = request.args.get('telegram_id')
        data = request.json
        
        print(f"[ADMIN] Update user {user_telegram_id}, data: {data}")
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        
        try:
            # Строим SET clause и параметры
            set_parts = []
            params = []
            
            if 'organization_id' in data:
                org_id = data['organization_id']
                if org_id is None or org_id == '':
                    set_parts.append('organization_id = NULL')
                else:
                    set_parts.append('organization_id = ?')
                    params.append(org_id)
            
            if 'is_banned' in data:
                set_parts.append('is_banned = ?')
                params.append(1 if data['is_banned'] else 0)
            
            if 'name' in data:
                set_parts.append('name = ?')
                params.append(data['name'])
            
            if not set_parts:
                conn.close()
                return jsonify({'error': 'No fields to update'}), 400
            
            # Добавляем WHERE параметр
            params.append(user_telegram_id)
            
            # Выполняем UPDATE
            query = f"UPDATE users SET {', '.join(set_parts)} WHERE telegram_id = ?"
            print(f"[ADMIN] Executing query: {query}")
            print(f"[ADMIN] Params: {params}")
            conn.execute(query, params)
            conn.commit()
            print(f"[ADMIN] User {user_telegram_id} updated successfully")
        except Exception as e:
            conn.close()
            print(f"[ADMIN] Error updating user: {e}")
            return jsonify({'error': str(e)}), 500
        
        user = conn.execute('''
            SELECT u.*, o.name as organization_name, ic.code as invite_code
            FROM users u
            LEFT JOIN organizations o ON u.organization_id = o.id
            LEFT JOIN invite_codes ic ON u.invite_code_id = ic.id
            WHERE u.telegram_id = ?
        ''', (user_telegram_id,)).fetchone()
        conn.close()
        
        if user:
            return jsonify({'success': True, 'user': dict(user)})
        return jsonify({'error': 'User not found'}), 404
    
    @app.route('/api/admin/users/<int:user_telegram_id>', methods=['DELETE'])
    def delete_user(user_telegram_id):
        """Удалить пользователя"""
        telegram_id = request.args.get('telegram_id')
        
        if not telegram_id or not is_admin(telegram_id):
            return jsonify({'error': 'Access denied'}), 403
        
        conn = get_db_connection()
        conn.execute('DELETE FROM users WHERE telegram_id = ?', (user_telegram_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
