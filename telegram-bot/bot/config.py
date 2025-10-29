import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "database/delivery.db")
AUCTION_DURATION = int(os.getenv("AUCTION_DURATION", 300))  # 5 минут (300 секунд)

# Иерархические типы машин для грузоперевозок
TRUCK_CATEGORIES = {
    "manipulator": {
        "name": "🏗️ Манипулятор", 
        "subtypes": {
            "manipulator_5t": "5 тонн",
            "manipulator_7t": "7 тонн", 
            "manipulator_10t": "10 тонн",
            "manipulator_12t": "12 тонн",
            "manipulator_20t": "20 тонн"
        }
    },
    "gazel": {
        "name": "🚐 Газель",
        "subtypes": {
            "gazel_open": "Открытая",
            "gazel_closed": "Закрытая"
        },
        "sub_subtypes": {
            "gazel_open": {
                "gazel_open_3t": "3 тонны",
                "gazel_open_5t": "5 тонн"
            },
            "gazel_closed": {
                "gazel_closed_10m3": "10 кубических метров",
                "gazel_closed_15m3": "15 кубических метров", 
                "gazel_closed_30m3": "30 кубических метров"
            }
        }
    },
    "longbed": {
        "name": "🚛 Длинномер",
        "subtypes": {
            "longbed_tent": "Тент",
            "longbed_platform": "Площадка"
        }
    }
}

# Плоский список всех конечных типов машин для базы данных
TRUCK_TYPES = {
    # Манипуляторы
    "manipulator_5t": "🏗️ Манипулятор 5 тонн",
    "manipulator_7t": "🏗️ Манипулятор 7 тонн",
    "manipulator_10t": "🏗️ Манипулятор 10 тонн",
    "manipulator_12t": "🏗️ Манипулятор 12 тонн",
    "manipulator_20t": "🏗️ Манипулятор 20 тонн",
    
    # Газели открытые
    "gazel_open_3t": "🚐 Газель открытая 3 тонны",
    "gazel_open_5t": "🚐 Газель открытая 5 тонн",
    
    # Газели закрытые
    "gazel_closed_10m3": "🚐 Газель закрытая 10 м³",
    "gazel_closed_15m3": "🚐 Газель закрытая 15 м³",
    "gazel_closed_30m3": "🚐 Газель закрытая 30 м³",
    
    # Длинномеры
    "longbed_tent": "🚛 Длинномер тент",
    "longbed_platform": "🚛 Длинномер площадка"
}

# Статусы пользователей
USER_ROLES = {
    "customer": "Заказчик",
    "driver": "Водитель"
}

# Статусы заявок
ORDER_STATUS = {
    "active": "Активная",
    "completed": "Завершена", 
    "cancelled": "Отменена",
    "no_offers": "Нет предложений"
}

def get_truck_display_name(truck_type_key: str) -> str:
    """Получить полное отображаемое название типа машины"""
    return TRUCK_TYPES.get(truck_type_key, truck_type_key)