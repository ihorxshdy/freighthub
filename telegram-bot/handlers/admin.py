import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from database.models import (
    get_all_users, delete_user_by_telegram_id, delete_all_users, 
    get_user_stats, get_user_by_telegram_id, get_order_by_id
)
from bot.config import TRUCK_TYPES
import aiosqlite
from bot.config import DB_PATH
from datetime import datetime

logger = logging.getLogger(__name__)

router = Router()

# Список администраторов (добавьте свой Telegram ID)
ADMIN_IDS = [643813567]

def is_admin(user_id: int) -> bool:
    """Проверка является ли пользователь администратором"""
    return user_id in ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Панель администратора"""
    user_id = message.from_user.id if message.from_user else None
    logger.info(f"Команда /admin от пользователя {user_id}")
    
    if not user_id or not is_admin(user_id):
        logger.warning(f"Отказано в доступе пользователю {user_id}. Админы: {ADMIN_IDS}")
        await message.answer("❌ У вас нет прав администратора!")
        return
    
    logger.info(f"Доступ к админ панели предоставлен пользователю {user_id}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="� Информация о заказе", callback_data="admin_order_info")],
        [InlineKeyboardButton(text="�🗑️ Очистить всех пользователей", callback_data="admin_clear_all")],
    ])
    
    await message.answer(
        "🛠️ **Панель администратора**\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

@router.message(Command("reset"))
async def reset_user(message: Message):
    """Команда сброса данных пользователя"""
    user_id = message.from_user.id if message.from_user else None
    logger.info(f"Команда /reset от пользователя {user_id}")
    
    if not user_id:
        await message.answer("❌ Ошибка получения данных пользователя!")
        return
        
    user = await get_user_by_telegram_id(user_id)
    if not user:
        logger.info(f"Пользователь {user_id} не найден в базе данных")
        await message.answer("❌ Вы не зарегистрированы в системе!")
        return
    
    logger.info(f"Пользователь {user_id} найден в БД, показываем подтверждение")

@router.callback_query(F.data == "admin_stats")
async def show_admin_stats(callback: CallbackQuery):
    """Показать статистику администратору"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав!", show_alert=True)
        return
    
    stats = await get_user_stats()
    
    await callback.message.edit_text(
        f"📊 **Статистика системы**\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🚚 Водителей: {stats['drivers_count']}\n"
        f"👤 Заказчиков: {stats['customers_count']}\n"
        f"📋 Активных заявок: {stats['active_orders']}\n\n"
        f"⏰ Время подбора: 5 минут",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ])
    )

@router.callback_query(F.data == "admin_users_list")
async def show_users_list(callback: CallbackQuery):
    """Показать список всех пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав!", show_alert=True)
        return
    
    users = await get_all_users()
    
    if not users:
        await callback.message.edit_text(
            "📭 **Список пользователей пуст**\n\n"
            "Пользователи появятся после регистрации через /start",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
            ])
        )
        return
    
    text = "👥 **Список всех пользователей:**\n\n"
    
    # Показываем первых 10 пользователей
    for i, user in enumerate(users[:10], 1):
        role_emoji = "🚚" if user['role'] == 'driver' else "👤"
        truck_info = f" ({TRUCK_TYPES.get(user['truck_type'], user['truck_type'])[:20]}...)" if user['truck_type'] else ""
        
        text += (
            f"{i}. {role_emoji} {user['name'] or 'Без имени'}\n"
            f"   📞 {user['phone_number']}\n"
            f"   🆔 {user['telegram_id']}{truck_info}\n\n"
        )
    
    if len(users) > 10:
        text += f"... и еще {len(users) - 10} пользователей"
    
    keyboard = []
    if len(users) > 0:
        keyboard.append([InlineKeyboardButton(text="🗑️ Очистить всех", callback_data="admin_clear_all")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data == "admin_clear_all")
async def confirm_clear_all(callback: CallbackQuery):
    """Подтверждение очистки всех пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав!", show_alert=True)
        return
    
    stats = await get_user_stats()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Да, удалить всех", callback_data="admin_clear_confirmed")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(
        f"⚠️ **ВНИМАНИЕ!**\n\n"
        f"Вы собираетесь удалить **ВСЕ** регистрации пользователей:\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"🚚 Водителей: {stats['drivers_count']}\n"
        f"👤 Заказчиков: {stats['customers_count']}\n\n"
        f"❗️ **Это действие нельзя отменить!**\n"
        f"Все пользователи должны будут зарегистрироваться заново.",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "admin_clear_confirmed")
async def clear_all_confirmed(callback: CallbackQuery):
    """Подтвержденная очистка всех пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав!", show_alert=True)
        return
    
    try:
        await delete_all_users()
        await callback.message.edit_text(
            "✅ **Все пользователи удалены!**\n\n"
            "База данных пользователей очищена.\n"
            "Пользователи могут зарегистрироваться заново через /start",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ К панели админа", callback_data="admin_back")]
            ])
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ **Ошибка при удалении:**\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
            ])
        )

@router.callback_query(F.data.startswith("reset_confirm_"))
async def reset_user_confirmed(callback: CallbackQuery):
    """Подтвержденное удаление своей регистрации"""
    user_id = int(callback.data.split("_")[2])
    
    if callback.from_user.id != user_id:
        await callback.answer("❌ Ошибка аутентификации!", show_alert=True)
        return
    
    try:
        await delete_user_by_telegram_id(user_id)
        await callback.message.edit_text(
            "✅ **Ваша регистрация удалена!**\n\n"
            "Теперь вы можете зарегистрироваться заново с помощью команды /start"
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ **Ошибка при удалении:**\n\n{str(e)}"
        )

@router.callback_query(F.data == "reset_cancel")
async def reset_cancelled(callback: CallbackQuery):
    """Отмена удаления регистрации"""
    await callback.message.edit_text(
        "❌ **Удаление отменено**\n\n"
        "Ваша регистрация сохранена."
    )

@router.callback_query(F.data == "admin_order_info")
async def ask_order_id(callback: CallbackQuery):
    """Запросить номер заказа"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📋 **Просмотр информации о заказе**\n\n"
        "Отправьте номер заказа цифрами, например: `5`\n\n"
        "Или отправьте /admin для возврата в меню",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")]
        ])
    )

@router.message(F.text.regexp(r'^\d+$'))
async def show_order_info(message: Message):
    """Показать полную информацию о заказе по номеру"""
    if not message.from_user or not is_admin(message.from_user.id):
        return
    
    try:
        order_id = int(message.text)
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Получаем основную информацию о заказе
            async with db.execute('''
                SELECT o.*, 
                       c.name as customer_name, c.phone_number as customer_phone, c.telegram_id as customer_tg_id,
                       d.name as driver_name, d.phone_number as driver_phone, d.telegram_id as driver_tg_id
                FROM orders o
                LEFT JOIN users c ON o.customer_id = c.id
                LEFT JOIN users d ON o.winner_driver_id = d.id
                WHERE o.id = ?
            ''', (order_id,)) as cursor:
                order = await cursor.fetchone()
            
            if not order:
                await message.answer(f"❌ Заказ #{order_id} не найден")
                return
            
            # Получаем все ставки
            async with db.execute('''
                SELECT b.*, u.name as driver_name, u.phone_number as driver_phone, u.telegram_id as driver_tg_id
                FROM bids b
                JOIN users u ON b.driver_id = u.id
                WHERE b.order_id = ?
                ORDER BY b.created_at ASC
            ''', (order_id,)) as cursor:
                bids = await cursor.fetchall()
            
            # Формируем детальную информацию
            status_emoji = {
                'active': '🔵',
                'in_progress': '🟡',
                'closed': '🟢',
                'cancelled': '🔴'
            }
            
            status_name = {
                'active': 'Активный',
                'in_progress': 'В процессе',
                'closed': 'Закрыт',
                'cancelled': 'Отменен'
            }
            
            text = f"📋 **Детальная информация о заказе #{order_id}**\n\n"
            text += f"**Статус:** {status_emoji.get(order['status'], '⚪')} {status_name.get(order['status'], order['status'])}\n\n"
            
            # Информация о заказе
            text += f"**📦 Данные заказа:**\n"
            text += f"Тип машины: {TRUCK_TYPES.get(order['truck_type'], order['truck_type'])}\n"
            text += f"Груз: {order['cargo_description'][:50]}...\n" if len(order['cargo_description']) > 50 else f"Груз: {order['cargo_description']}\n"
            text += f"Откуда: {order['pickup_address'] or 'Не указано'}\n"
            text += f"Куда: {order['delivery_address']}\n"
            if order['delivery_date']:
                text += f"Дата доставки: {order['delivery_date']}\n"
            if order['max_price']:
                text += f"Желаемая цена: {order['max_price']} руб.\n"
            text += f"\n**⏰ Временные метки:**\n"
            text += f"Создан: {order['created_at']}\n"
            text += f"Истекает: {order['expires_at']}\n"
            if order['cancelled_at']:
                text += f"Отменен: {order['cancelled_at']}\n"
            
            # Информация о заказчике
            text += f"\n**👤 Заказчик:**\n"
            text += f"Имя: {order['customer_name'] or 'Не указано'}\n"
            text += f"Телефон: {order['customer_phone']}\n"
            text += f"Telegram ID: {order['customer_tg_id']}\n"
            
            # Информация о водителе-победителе
            if order['winner_driver_id']:
                text += f"\n**🚚 Исполнитель:**\n"
                text += f"Имя: {order['driver_name'] or 'Не указано'}\n"
                text += f"Телефон: {order['driver_phone']}\n"
                text += f"Telegram ID: {order['driver_tg_id']}\n"
                text += f"Цена: {order['winning_price']} руб.\n"
                
                # Статус подтверждения
                if order['status'] == 'in_progress':
                    text += f"\n**✅ Подтверждения:**\n"
                    text += f"Заказчик: {'✅ Да' if order['customer_confirmed'] else '❌ Нет'}\n"
                    text += f"Водитель: {'✅ Да' if order['driver_confirmed'] else '❌ Нет'}\n"
            
            # Информация о ставках
            if bids:
                text += f"\n**💰 Ставки ({len(bids)}):**\n"
                for i, bid in enumerate(bids[:5], 1):  # Показываем первые 5
                    is_winner = bid['driver_id'] == order['winner_driver_id'] if order['winner_driver_id'] else False
                    winner_mark = " 🏆" if is_winner else ""
                    text += f"{i}. {bid['driver_name']}{winner_mark}: {bid['price']} руб. ({bid['created_at']})\n"
                
                if len(bids) > 5:
                    text += f"... и еще {len(bids) - 5} ставок\n"
            else:
                text += f"\n**💰 Ставки:** Нет ставок\n"
            
            # Отправляем информацию
            if len(text) > 4096:
                # Если сообщение слишком длинное, разбиваем на части
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for part in parts:
                    await message.answer(part)
            else:
                await message.answer(text)
                
    except ValueError:
        await message.answer("❌ Неверный формат номера заказа")
    except Exception as e:
        logger.error(f"Ошибка при получении информации о заказе: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Возврат к панели администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="� Информация о заказе", callback_data="admin_order_info")],
        [InlineKeyboardButton(text="�🗑️ Очистить всех пользователей", callback_data="admin_clear_all")],
    ])
    
    await callback.message.edit_text(
        "🛠️ **Панель администратора**\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )