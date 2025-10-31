"""
Функции создания клавиатур для бота
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

def get_webapp_menu():
    """Главное меню - теперь просто удаляет клавиатуру"""
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()

def get_customer_menu():
    """Главное меню для заказчика (DEPRECATED - используйте get_webapp_menu)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Создать заявку")],
            [KeyboardButton(text="📋 Мои заявки")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

def get_driver_menu():
    """Главное меню для водителя (DEPRECATED - используйте get_webapp_menu)"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚛 Выигранные заявки")],
            [KeyboardButton(text="💰 Мои предложения")],
            [KeyboardButton(text="🚗 Мои машины")],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )