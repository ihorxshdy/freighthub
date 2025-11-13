"""
Конфигурация для Web Application
"""
import os

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
                "gazel_open_5t": "5 тонн",
                "gazel_open_koniki": "Коники 4.2м"
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

# Плоский список всех конечных типов машин
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
    "gazel_open_koniki": "🚐 Газель открытая Коники 4.2м",
    
    # Газели закрытые
    "gazel_closed_10m3": "🚐 Газель закрытая 10 м³",
    "gazel_closed_15m3": "🚐 Газель закрытая 15 м³",
    "gazel_closed_30m3": "🚐 Газель закрытая 30 м³",
    
    # Длинномеры
    "longbed_tent": "🚛 Длинномер тент",
    "longbed_platform": "🚛 Длинномер площадка"
}

# Путь к базе данных
# На Render: либо /mnt/data/delivery.db (с персистентным диском), либо создаём локально
# Локально: используем БД бота
if os.environ.get('DATABASE_PATH'):
    # Render с персистентным диском
    DATABASE_PATH = os.environ.get('DATABASE_PATH')
elif os.path.exists('/mnt/data'):
    # Render с примонтированным диском
    DATABASE_PATH = '/mnt/data/delivery.db'
else:
    # Локальная разработка - используем БД бота
    bot_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'telegram-bot', 'database', 'delivery.db')
    if os.path.exists(bot_db_path):
        DATABASE_PATH = bot_db_path
    else:
        # Если нет БД бота, создаём в текущей папке (для Render без диска)
        DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'delivery.db')

# Secret key для Flask
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

def get_truck_display_name(truck_type_key: str) -> str:
    """Получить полное отображаемое название типа машины"""
    return TRUCK_TYPES.get(truck_type_key, truck_type_key)
