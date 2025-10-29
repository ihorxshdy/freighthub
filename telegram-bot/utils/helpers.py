import logging
from typing import Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def format_price(price: float) -> str:
    """Форматирование цены"""
    return f"{price:,.0f} руб.".replace(',', ' ')

def safe_get_user_attr(user: Optional[dict], attr: str, default: str = "Неизвестно") -> str:
    """Безопасное получение атрибута пользователя"""
    if user and user.get(attr):
        return str(user[attr])
    return default

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезка текста до максимальной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."