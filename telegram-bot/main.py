import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiohttp import web

from bot.config import BOT_TOKEN
from database.models import init_database
from handlers import registration, orders, misc, admin, vehicles
from handlers.webhooks import setup_webhook_handlers
from utils.helpers import logger
import os

async def setup_bot_commands(bot: Bot):
    """Настройка команд и описания бота"""
    # Настройка команд
    commands = [
        BotCommand(command="start", description="🚀 Начать работу / Регистрация"),
        BotCommand(command="help", description="❓ Справка по командам"),
        BotCommand(command="menu", description="🏠 Главное меню"),
        BotCommand(command="webapp", description="🚛 Открыть веб-приложение"),
    ]
    
    await bot.set_my_commands(commands)
    
    # Отключаем Menu Button (кнопку под строкой ввода)
    try:
        from aiogram.types import MenuButtonCommands
        # Устанавливаем обычное меню команд вместо WebApp
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("✅ Menu Button изменена на Commands (показывает список команд)")
    except Exception as e:
        logger.warning(f"⚠️ Не удалось изменить Menu Button: {e}")
    
    # Настройка описания бота
    try:
        await bot.set_my_description(
            description="🚚 FreightHub - надежный сервис грузоперевозок с автоматизированной системой поиска исполнителя. "
                       "Заказчики создают заявки, водители предлагают цены, система выбирает лучшее предложение автоматически!"
        )
        await bot.set_my_short_description(
            short_description="🚚 Сервис грузоперевозок с аукционной системой"
        )
    except Exception as e:
        logger.warning(f"Не удалось установить описание бота: {e}")
    
    logger.info("Команды бота настроены")

async def main():
    """Основная функция запуска бота"""
    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.error("Не найден BOT_TOKEN в переменных окружения!")
        return
    
    # Инициализация базы данных
    try:
        await init_database()
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        return
    
    # Создание бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Передаем bot в workflow_data для доступа в обработчиках
    dp.workflow_data.update({"bot": bot})
    
    # Подключение роутеров
    dp.include_router(registration.router)
    dp.include_router(orders.router)
    dp.include_router(vehicles.router)  # Роутер для управления машинами
    dp.include_router(admin.router)  # Admin должен быть ДО misc!
    dp.include_router(misc.router)
    
    # Настраиваем команды бота
    await setup_bot_commands(bot)
    
    # Создаём webhook сервер
    webhook_app = web.Application()
    setup_webhook_handlers(webhook_app, bot)
    
    # Порт для webhook сервера (Render назначает через PORT)
    webhook_port = int(os.getenv('WEBHOOK_PORT', '8080'))
    
    # Запускаем webhook сервер в фоне
    runner = web.AppRunner(webhook_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', webhook_port)
    await site.start()
    
    logger.info(f"Webhook сервер запущен на порту {webhook_port}")
    logger.info("Бот запускается...")
    
    try:
        # Удаляем webhook и запускаем поллинг
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")