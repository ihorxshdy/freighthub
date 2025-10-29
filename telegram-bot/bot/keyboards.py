"""
Функции создания клавиатур для бота
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from bot.webapp_config import WEBAPP_URL

def get_webapp_menu():
    """Главное меню с кнопкой открытия веб-приложения"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="🌐 Приложение", 
                web_app=WebAppInfo(url=WEBAPP_URL)
            )],
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )

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