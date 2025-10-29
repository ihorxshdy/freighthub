import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from database.models import (
    get_all_users, delete_user_by_telegram_id, delete_all_users, 
    get_user_stats, get_user_by_telegram_id
)
from bot.config import TRUCK_TYPES

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
        [InlineKeyboardButton(text="🗑️ Очистить всех пользователей", callback_data="admin_clear_all")],
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
        f"⏰ Время аукциона: 5 минут",
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

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Возврат к панели администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет прав!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users_list")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🗑️ Очистить всех пользователей", callback_data="admin_clear_all")],
    ])
    
    await callback.message.edit_text(
        "🛠️ **Панель администратора**\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )