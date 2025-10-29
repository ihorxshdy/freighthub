"""
Обработчики для управления машинами водителей
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter

from database.models import (
    get_user_by_telegram_id, get_driver_vehicles, add_driver_vehicle,
    delete_driver_vehicle, set_primary_vehicle
)
from bot.config import TRUCK_CATEGORIES, get_truck_display_name
from bot.keyboards import get_driver_menu

router = Router()

class VehicleStates(StatesGroup):
    choosing_vehicle_category = State()
    choosing_vehicle_subtype = State()
    choosing_vehicle_final = State()

@router.message(F.text == "🚗 Мои машины")
async def my_vehicles(message: Message):
    """Показать все машины водителя"""
    if not message.from_user:
        return
        
    user = await get_user_by_telegram_id(message.from_user.id)
    
    if not user or user['role'] != 'driver':
        await message.answer("❌ Эта функция доступна только водителям!")
        return
    
    vehicles = await get_driver_vehicles(user['id'])
    
    if not vehicles:
        # У водителя нет машин, предлагаем добавить первую
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить машину", callback_data="add_vehicle")]
        ])
        
        await message.answer(
            "🚗 **Мои машины**\n\n"
            "У вас пока нет добавленных машин.\n\n"
            "Добавьте свою первую машину, чтобы получать заявки!",
            reply_markup=keyboard
        )
        return
    
    # Формируем список машин
    response = "🚗 **Мои машины:**\n\n"
    
    buttons = []
    for vehicle in vehicles:
        truck_name = get_truck_display_name(vehicle['truck_type'])
        primary_mark = "⭐ " if vehicle['is_primary'] else ""
        
        response += f"{primary_mark}{truck_name}\n"
        
        # Кнопки для каждой машины
        truck_buttons = []
        if not vehicle['is_primary'] and len(vehicles) > 1:
            truck_buttons.append(
                InlineKeyboardButton(
                    text="⭐ Сделать основной", 
                    callback_data=f"set_primary_{vehicle['truck_type']}"
                )
            )
        
        truck_buttons.append(
            InlineKeyboardButton(
                text="🗑️ Удалить", 
                callback_data=f"delete_vehicle_{vehicle['truck_type']}"
            )
        )
        
        buttons.extend([truck_buttons])
    
    # Добавляем кнопку для добавления новой машины
    buttons.append([
        InlineKeyboardButton(text="➕ Добавить еще машину", callback_data="add_vehicle")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if vehicles:
        response += f"\n💡 Основная машина отмечена звездочкой ⭐\n"
        response += "По основной машине вы будете получать уведомления в первую очередь."
    
    await message.answer(response, reply_markup=keyboard)

@router.callback_query(F.data == "add_vehicle")
async def add_vehicle_start(callback: CallbackQuery, state: FSMContext):
    """Начать добавление новой машины"""
    # Показываем категории машин
    category_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=category_info['name'], callback_data=f"vehicle_category_{category_id}")]
        for category_id, category_info in TRUCK_CATEGORIES.items()
    ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_vehicles")]])
    
    await callback.message.edit_text(
        "🚗 **Добавление машины**\n\n"
        "Выберите категорию вашей машины:",
        reply_markup=category_keyboard
    )
    
    await state.set_state(VehicleStates.choosing_vehicle_category)

@router.callback_query(StateFilter(VehicleStates.choosing_vehicle_category), F.data.startswith("vehicle_category_"))
async def vehicle_category_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории машины"""
    category_id = callback.data.split("_")[2]
    category_info = TRUCK_CATEGORIES[category_id]
    
    await state.update_data(vehicle_category=category_id)
    
    # Создаем клавиатуру с подтипами
    subtype_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=subtype_name, callback_data=f"vehicle_subtype_{category_id}_{subtype_id}")]
        for subtype_id, subtype_name in category_info['subtypes'].items()
    ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data="add_vehicle")]])
    
    await callback.message.edit_text(
        f"🚗 **Добавление машины**\n\n"
        f"Категория: {category_info['name']}\n\n"
        "Выберите подтип:",
        reply_markup=subtype_keyboard
    )
    
    await state.set_state(VehicleStates.choosing_vehicle_subtype)

@router.callback_query(StateFilter(VehicleStates.choosing_vehicle_subtype), F.data.startswith("vehicle_subtype_"))
async def vehicle_subtype_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора подтипа машины"""
    parts = callback.data.split("_")
    category_id = parts[2]
    subtype_id = "_".join(parts[3:])
    
    category_info = TRUCK_CATEGORIES[category_id]
    
    # Проверяем, есть ли дополнительные подуровни
    if 'sub_subtypes' in category_info and subtype_id in category_info['sub_subtypes']:
        # Есть дополнительные подуровни (для Газели)
        await state.update_data(vehicle_subtype=subtype_id)
        
        sub_subtypes = category_info['sub_subtypes'][subtype_id]
        final_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=sub_subtype_name, callback_data=f"vehicle_final_{category_id}_{subtype_id}_{sub_subtype_id}")]
            for sub_subtype_id, sub_subtype_name in sub_subtypes.items()
        ] + [[InlineKeyboardButton(text="◀️ Назад", callback_data=f"vehicle_category_{category_id}")]])
        
        subtype_name = category_info['subtypes'][subtype_id]
        await callback.message.edit_text(
            f"🚗 **Добавление машины**\n\n"
            f"Категория: {category_info['name']}\n"
            f"Тип: {subtype_name}\n\n"
            "Выберите характеристики:",
            reply_markup=final_keyboard
        )
        
        await state.set_state(VehicleStates.choosing_vehicle_final)
    else:
        # Это финальный выбор
        await add_vehicle_final(callback, state, subtype_id)

@router.callback_query(StateFilter(VehicleStates.choosing_vehicle_final), F.data.startswith("vehicle_final_"))
async def vehicle_final_chosen(callback: CallbackQuery, state: FSMContext):
    """Обработка финального выбора машины"""
    parts = callback.data.split("_")
    final_id = parts[-1]
    
    # Ищем полный тип машины
    for truck_key in get_truck_display_name.__globals__['TRUCK_TYPES'].keys():
        if truck_key.endswith(final_id):
            final_id = truck_key
            break
    
    await add_vehicle_final(callback, state, final_id)

async def add_vehicle_final(callback: CallbackQuery, state: FSMContext, truck_type: str):
    """Завершение добавления машины"""
    user = await get_user_by_telegram_id(callback.from_user.id)
    
    # Получаем текущие машины водителя
    existing_vehicles = await get_driver_vehicles(user['id'])
    is_primary = len(existing_vehicles) == 0  # Первая машина становится основной
    
    # Добавляем машину
    success = await add_driver_vehicle(user['id'], truck_type, is_primary)
    
    if success:
        truck_name = get_truck_display_name(truck_type)
        primary_text = " (основная)" if is_primary else ""
        
        await callback.message.edit_text(
            f"✅ **Машина добавлена!**\n\n"
            f"🚗 {truck_name}{primary_text}\n\n"
            "Теперь вы будете получать заявки по этому типу машины.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚗 Мои машины", callback_data="back_to_vehicles")]
            ])
        )
    else:
        await callback.message.edit_text(
            "❌ **Ошибка!**\n\n"
            "Эта машина уже добавлена в ваш профиль.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚗 Мои машины", callback_data="back_to_vehicles")]
            ])
        )
    
    await state.clear()

@router.callback_query(F.data.startswith("set_primary_"))
async def set_primary_vehicle_handler(callback: CallbackQuery):
    """Установить машину как основную"""
    truck_type = callback.data.replace("set_primary_", "")
    user = await get_user_by_telegram_id(callback.from_user.id)
    
    await set_primary_vehicle(user['id'], truck_type)
    
    truck_name = get_truck_display_name(truck_type)
    await callback.answer(f"⭐ {truck_name} теперь основная машина!")
    
    # Обновляем список машин
    await show_vehicles_list(callback.message, user['id'])

@router.callback_query(F.data.startswith("delete_vehicle_"))
async def delete_vehicle_handler(callback: CallbackQuery):
    """Удалить машину"""
    truck_type = callback.data.replace("delete_vehicle_", "")
    user = await get_user_by_telegram_id(callback.from_user.id)
    
    # Проверяем, не единственная ли это машина
    vehicles = await get_driver_vehicles(user['id'])
    if len(vehicles) <= 1:
        await callback.answer("❌ Нельзя удалить единственную машину!")
        return
    
    await delete_driver_vehicle(user['id'], truck_type)
    
    truck_name = get_truck_display_name(truck_type)
    await callback.answer(f"🗑️ {truck_name} удалена!")
    
    # Обновляем список машин
    await show_vehicles_list(callback.message, user['id'])

@router.callback_query(F.data == "back_to_vehicles")
async def back_to_vehicles(callback: CallbackQuery):
    """Вернуться к списку машин"""
    user = await get_user_by_telegram_id(callback.from_user.id)
    await show_vehicles_list(callback.message, user['id'])

async def show_vehicles_list(message, driver_id: int):
    """Показать список машин водителя"""
    vehicles = await get_driver_vehicles(driver_id)
    
    if not vehicles:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить машину", callback_data="add_vehicle")]
        ])
        
        await message.edit_text(
            "🚗 **Мои машины**\n\n"
            "У вас пока нет добавленных машин.\n\n"
            "Добавьте свою первую машину, чтобы получать заявки!",
            reply_markup=keyboard
        )
        return
    
    # Формируем список машин
    response = "🚗 **Мои машины:**\n\n"
    
    buttons = []
    for vehicle in vehicles:
        truck_name = get_truck_display_name(vehicle['truck_type'])
        primary_mark = "⭐ " if vehicle['is_primary'] else ""
        
        response += f"{primary_mark}{truck_name}\n"
        
        # Кнопки для каждой машины
        truck_buttons = []
        if not vehicle['is_primary'] and len(vehicles) > 1:
            truck_buttons.append(
                InlineKeyboardButton(
                    text="⭐ Сделать основной", 
                    callback_data=f"set_primary_{vehicle['truck_type']}"
                )
            )
        
        if len(vehicles) > 1:  # Можно удалить только если есть другие машины
            truck_buttons.append(
                InlineKeyboardButton(
                    text="🗑️ Удалить", 
                    callback_data=f"delete_vehicle_{vehicle['truck_type']}"
                )
            )
        
        if truck_buttons:  # Добавляем кнопки только если они есть
            buttons.extend([truck_buttons])
    
    # Добавляем кнопку для добавления новой машины
    buttons.append([
        InlineKeyboardButton(text="➕ Добавить еще машину", callback_data="add_vehicle")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    if vehicles:
        response += f"\n💡 Основная машина отмечена звездочкой ⭐\n"
        response += "По основной машине вы будете получать уведомления в первую очередь."
    
    await message.edit_text(response, reply_markup=keyboard)