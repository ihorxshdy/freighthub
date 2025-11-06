// Telegram Web App API
const tg = window.Telegram?.WebApp;

// Применение темы Telegram
function applyTelegramTheme() {
    console.log('=== Theme Detection Debug ===');
    console.log('tg exists:', !!tg);
    
    if (tg) {
        console.log('tg.colorScheme:', tg.colorScheme);
        console.log('tg.themeParams:', tg.themeParams);
        console.log('tg.backgroundColor:', tg.backgroundColor);
    }
    
    let isDarkTheme = false;
    
    // Приоритет 1: используем colorScheme если доступен
    if (tg && tg.colorScheme) {
        isDarkTheme = tg.colorScheme === 'dark';
        console.log('Theme from colorScheme:', isDarkTheme ? 'dark' : 'light');
    }
    // Приоритет 2: определяем по цвету фона
    else if (tg && (tg.themeParams?.bg_color || tg.backgroundColor)) {
        const bgColor = tg.themeParams?.bg_color || tg.backgroundColor;
        isDarkTheme = isColorDark(bgColor);
        console.log('Theme from bg_color:', bgColor, '→', isDarkTheme ? 'dark' : 'light');
    }
    // Приоритет 3: проверяем системную тему через CSS
    else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        isDarkTheme = true;
        console.log('Theme from system prefers-color-scheme: dark');
    }
    
    // Применяем тему
    if (isDarkTheme) {
        document.body.classList.add('theme-dark');
        console.log('✓ Applied theme-dark class to body');
    } else {
        document.body.classList.remove('theme-dark');
        console.log('✓ Removed theme-dark class from body');
    }
    
    console.log('Final body classes:', document.body.className);
    console.log('============================');
}

// Определение, является ли цвет темным
function isColorDark(color) {
    if (!color) return false;
    
    // Убираем # если есть
    const hex = color.replace('#', '');
    
    // Конвертируем в RGB
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    
    // Вычисляем яркость (weighted luminance formula)
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    
    // Если яркость меньше 128, цвет темный
    return brightness < 128;
}

// Применяем тему сразу при загрузке
applyTelegramTheme();

// Применяем тему после загрузки DOM
document.addEventListener('DOMContentLoaded', applyTelegramTheme);

if (tg) {
    try {
        tg.expand();
        tg.ready();
        // Скрываем нижнюю кнопку "Приложение"
        tg.MainButton.hide();
        
        // Применяем тему Telegram
        applyTelegramTheme();
        
        // Слушаем изменения темы
        if (tg.onEvent) {
            tg.onEvent('themeChanged', applyTelegramTheme);
        }
        
        // Слушаем изменения системной темы
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTelegramTheme);
        }
    } catch (e) {
        console.error('Ошибка инициализации Telegram WebApp:', e);
    }
}

// Базовый путь для API запросов (поддержка вложенных путей)
const API_BASE = './';

// Глобальные переменные
let currentUser = null;
let currentTab = null;
let currentOrderForBid = null;
let currentOrderForCancellation = null;
let truckTypesMap = {}; // Маппинг ID -> название типа машины
let ordersCache = null; // Кэш заказов
let ordersCacheTime = 0; // Время последнего обновления кэша
const CACHE_DURATION = 30000; // 30 секунд

// Функция для форматирования даты/времени из UTC в локальное время
function formatLocalDateTime(utcDateString) {
    if (!utcDateString) return '';
    
    try {
        const date = new Date(utcDateString);
        
        // Форматируем дату и время по местному часовому поясу
        const options = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        };
        
        return date.toLocaleString('ru-RU', options);
    } catch (e) {
        console.error('Ошибка форматирования даты:', e);
        return utcDateString;
    }
}

// Функция для форматирования только даты
function formatLocalDate(utcDateString) {
    if (!utcDateString) return '';
    
    try {
        const date = new Date(utcDateString);
        
        const options = {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        };
        
        return date.toLocaleDateString('ru-RU', options);
    } catch (e) {
        console.error('Ошибка форматирования даты:', e);
        return utcDateString;
    }
}

// Получаем данные пользователя из Telegram
function getTelegramUser() {
    if (!tg || !tg.initDataUnsafe) {
        console.log('⚠️ tg или initDataUnsafe отсутствует');
        return null;
    }
    
    console.log('🔍 initDataUnsafe:', JSON.stringify(tg.initDataUnsafe));
    console.log('🔍 initData:', tg.initData);
    
    // Способ 1: из initDataUnsafe.user
    if (tg.initDataUnsafe.user && tg.initDataUnsafe.user.id) {
        console.log('✅ Пользователь найден в initDataUnsafe.user');
        return tg.initDataUnsafe.user;
    }
    
    // Способ 2: парсим initData вручную
    if (tg.initData) {
        try {
            const params = new URLSearchParams(tg.initData);
            const userJson = params.get('user');
            if (userJson) {
                const user = JSON.parse(userJson);
                console.log('✅ Пользователь распарсен из initData');
                return user;
            }
        } catch (e) {
            console.error('❌ Ошибка парсинга initData:', e);
        }
    }
    
    console.log('⚠️ Не удалось получить данные пользователя');
    return null;
}

// Инициализация приложения
document.addEventListener('DOMContentLoaded', async () => {
    const loadingText = document.getElementById('loading-text');
    
    try {
        // Применяем тему Telegram
        applyTelegramTheme();
        
        loadingText.textContent = 'Подключение...';
        console.log('🔌 Подключение к Telegram...');
        
        // Получаем данные пользователя из Telegram
        const telegramUser = getTelegramUser();
        
        if (!telegramUser || !telegramUser.id) {
            console.log('❌ Пользователь не найден в Telegram WebApp', 'error');
            loadingText.textContent = 'Ошибка подключения';
            
            // Показываем сообщение с инструкцией
            showScreen('registration-screen');
            document.querySelector('.registration-form h2').textContent = 'Ошибка доступа';
            document.querySelector('.registration-form .description').innerHTML = 
                'Не удалось получить данные пользователя из Telegram.<br><br>' +
                '<strong>Пожалуйста, откройте приложение через команду /webapp в боте</strong><br><br>' +
                'Не используйте кнопку "Приложение" внизу экрана.';
            return;
        }
        
        console.log('👤 Telegram пользователь: ID=' + telegramUser.id + ', имя=' + telegramUser.first_name);
        loadingText.textContent = `Загрузка профиля...`;
        
        // Всегда проверяем актуальные данные с сервера
        const user = await fetchUser(telegramUser.id);
        
        if (user) {
            currentUser = user;
            // Сохраняем в localStorage для быстрого доступа
            localStorage.setItem('currentUser', JSON.stringify(user));
            console.log('💾 Профиль сохранён в localStorage');
            showMainScreen();
        } else {
            // Пользователь не зарегистрирован - показываем экран регистрации
            console.log('📝 Требуется регистрация');
            showRegistrationScreen(telegramUser);
        }
    } catch (error) {
        console.log('💥 Критическая ошибка инициализации: ' + error.message, 'error');
        showError('Ошибка загрузки приложения');
    }
});

// === ТЕМА TELEGRAM ===
function applyTelegramTheme() {
    const root = document.documentElement;
    
    if (tg.themeParams) {
        if (tg.themeParams.bg_color) root.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color);
        if (tg.themeParams.text_color) root.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color);
        if (tg.themeParams.hint_color) root.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color);
        if (tg.themeParams.link_color) root.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color);
        if (tg.themeParams.button_color) root.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color);
        if (tg.themeParams.button_text_color) root.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color);
        if (tg.themeParams.secondary_bg_color) root.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color);
    }
}

// === API ФУНКЦИИ ===

// Универсальная функция для fetch с timeout и retry
async function fetchWithTimeout(url, options = {}, timeout = 10000, retries = 2) {
    let lastError;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);
        
        try {
            if (attempt > 0) {
                console.log(`🔄 Повторная попытка ${attempt}/${retries} для ${url}`, 'warning');
            }
            
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(id);
            return response;
        } catch (error) {
            clearTimeout(id);
            lastError = error;
            
            if (error.name === 'AbortError') {
                console.log(`⏱️ Timeout (попытка ${attempt + 1}/${retries + 1})`, 'warning');
                if (attempt < retries) {
                    // Экспоненциальная задержка между попытками
                    await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
                    continue;
                }
                throw new Error('Превышено время ожидания. Проверьте интернет-соединение.');
            }
            throw error;
        }
    }
    
    throw lastError;
}

async function fetchUser(telegramId) {
    console.log('🔍 Запрос пользователя, telegram_id: ' + telegramId);
    const url = `${API_BASE}api/user?telegram_id=${telegramId}`;
    console.log('📡 URL: ' + url);
    
    try {
        const response = await fetchWithTimeout(url, {}, 20000, 2); // 20 сек, 2 повтора
        console.log('📥 Статус ответа: ' + response.status);
        
        if (response.ok) {
            const userData = await response.json();
            console.log('✅ Пользователь найден: ' + userData.name + ' (' + userData.role + ')');
            return userData;
        }
        
        console.log('❌ Пользователь не найден', 'warning');
        return null;
    } catch (error) {
        console.log('❌ Ошибка запроса: ' + error.message, 'error');
        return null;
    }
}

async function registerUser(userData) {
    const response = await fetchWithTimeout(API_BASE + 'api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
    }, 15000);
    
    if (!response.ok) {
        throw new Error('Ошибка регистрации');
    }
    
    return await response.json();
}

async function fetchTruckTypes() {
    const response = await fetchWithTimeout(`${API_BASE}api/truck-types`, {}, 10000);
    return await response.json();
}

async function fetchCustomerOrders(telegramId) {
    console.log('📦 Загрузка заказов заказчика, ID: ' + telegramId);
    const url = `${API_BASE}api/customer/orders?telegram_id=${telegramId}`;
    const startTime = Date.now();
    
    try {
        const response = await fetchWithTimeout(url, {}, 30000, 2); // 30 сек, 2 повтора для медленной сети
        const duration = Date.now() - startTime;
        console.log(`✅ Заказы загружены за ${duration}ms, статус: ${response.status}`);
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки заказов');
        }
        const data = await response.json();
        const total = Object.values(data).reduce((sum, arr) => sum + arr.length, 0);
        console.log(`📊 Всего заказов: ${total}`);
        return data;
    } catch (error) {
        const duration = Date.now() - startTime;
        console.log(`❌ Ошибка загрузки за ${duration}ms: ${error.message}`, 'error');
        throw error;
    }
}

async function fetchDriverOrders(telegramId) {
    console.log('🚗 Загрузка заказов водителя, ID: ' + telegramId);
    const url = `${API_BASE}api/driver/orders?telegram_id=${telegramId}`;
    const startTime = Date.now();
    
    try {
        const response = await fetchWithTimeout(url, {}, 30000, 2); // 30 сек, 2 повтора для медленной сети
        const duration = Date.now() - startTime;
        console.log(`✅ Заказы загружены за ${duration}ms, статус: ${response.status}`);
        
        if (!response.ok) {
            throw new Error('Ошибка загрузки заказов');
        }
        const data = await response.json();
        const total = Object.values(data).reduce((sum, arr) => sum + arr.length, 0);
        console.log(`📊 Всего заказов: ${total}`);
        return data;
    } catch (error) {
        const duration = Date.now() - startTime;
        console.log(`❌ Ошибка загрузки за ${duration}ms: ${error.message}`, 'error');
        throw error;
    }
}

async function createOrder(orderData) {
    const response = await fetchWithTimeout(`${API_BASE}api/orders?telegram_id=${currentUser.telegram_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData)
    }, 15000);
    
    if (!response.ok) {
        throw new Error('Ошибка создания заявки');
    }
    
    return await response.json();
}

async function createBid(bidData) {
    const response = await fetchWithTimeout(`${API_BASE}api/bids?telegram_id=${currentUser.telegram_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bidData)
    }, 15000);
    
    if (!response.ok) {
        throw new Error('Ошибка создания предложения');
    }
    
    return await response.json();
}

async function fetchOrderBids(orderId) {
    const response = await fetchWithTimeout(`${API_BASE}api/orders/${orderId}/bids?telegram_id=${currentUser.telegram_id}`, {}, 10000);
    return await response.json();
}

async function fetchUserRating(telegramId) {
    try {
        const response = await fetchWithTimeout(`${API_BASE}api/user/${telegramId}/rating`, {}, 10000);
        if (!response.ok) return { average: 0, count: 0 };
        return await response.json();
    } catch (error) {
        console.error('Ошибка загрузки рейтинга:', error);
        return { average: 0, count: 0 };
    }
}

async function fetchUserStats(telegramId) {
    try {
        const response = await fetchWithTimeout(`${API_BASE}api/user/${telegramId}/stats`, {}, 10000);
        if (!response.ok) return { total_orders: 0 };
        return await response.json();
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        return { total_orders: 0 };
    }
}

async function fetchUserReviews(telegramId) {
    try {
        const response = await fetchWithTimeout(`${API_BASE}api/user/${telegramId}/reviews`, {}, 10000);
        if (!response.ok) return [];
        return await response.json();
    } catch (error) {
        console.error('Ошибка загрузки отзывов:', error);
        return [];
    }
}

async function submitReview(orderId, revieweeId, rating, comment) {
    const response = await fetchWithTimeout(`${API_BASE}api/reviews?telegram_id=${currentUser.telegram_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            order_id: orderId,
            reviewee_id: revieweeId,
            rating: rating,
            comment: comment
        })
    }, 15000);
    
    if (!response.ok) {
        throw new Error('Ошибка отправки отзыва');
    }
    
    return await response.json();
}

// === НАВИГАЦИЯ ===
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    document.getElementById(screenId).classList.remove('hidden');
}

function showRegistrationScreen(telegramUser) {
    showScreen('registration-screen');
    console.log('Пользователь не зарегистрирован. Показываем инструкцию для регистрации через бота.');
}

async function showMainScreen() {
    showScreen('main-screen');
    
    // Загружаем типы грузовиков ДО отображения профиля
    await loadTruckTypes();
    
    // Загружаем рейтинг пользователя
    const rating = await fetchUserRating(currentUser.telegram_id);
    
    // Обновляем информацию о пользователе в профиле
    document.getElementById('user-name').textContent = currentUser.name || 'Пользователь';
    document.getElementById('user-phone').textContent = formatPhoneNumber(currentUser.phone_number);
    
    // Отображаем рейтинг
    updateRatingDisplay(rating);
    
    document.body.className = `role-${currentUser.role}`;
    
    // Устанавливаем аватар из Telegram
    const telegramUser = getTelegramUser();
    const avatar = document.getElementById('user-avatar');
    if (telegramUser && telegramUser.photo_url) {
        avatar.style.backgroundImage = `url(${telegramUser.photo_url})`;
        avatar.style.backgroundSize = 'cover';
        avatar.style.backgroundPosition = 'center';
        avatar.textContent = '';
    } else {
        // Используем первую букву имени
        const initial = (currentUser.name || 'U').charAt(0).toUpperCase();
        avatar.textContent = initial;
        avatar.style.backgroundImage = '';
    }
    
    // Инициализируем меню навигации
    initNavMenu();
    
    // Инициализируем модальные окна
    initModals();
    
    // Автоматическое обновление данных каждые 30 секунд
    setInterval(() => {
        if (currentTab && !document.hidden) {
            // Обновляем только если вкладка активна
            const now = Date.now();
            if (now - ordersCacheTime >= CACHE_DURATION) {
                loadTabData(currentTab, true);
            }
        }
    }, CACHE_DURATION);
}

// Функция для форматирования номера телефона
function formatPhoneNumber(phone) {
    if (!phone) return '+7 (000) 000-00-00';
    const cleaned = phone.replace(/\D/g, '');
    if (cleaned.length === 11 && cleaned[0] === '7') {
        return `+7 (${cleaned.slice(1,4)}) ${cleaned.slice(4,7)}-${cleaned.slice(7,9)}-${cleaned.slice(9)}`;
    }
    return phone;
}

// Обновление отображения рейтинга
function updateRatingDisplay(rating) {
    const avgRating = rating.average || 0;
    const count = rating.count || 0;
    
    // Обновляем в карточке профиля
    document.getElementById('user-rating').innerHTML = `
        <span class="rating-stars">${getStarsHTML(avgRating)}</span>
        <span class="rating-value">${avgRating.toFixed(1)} (${count})</span>
    `;
}

// Генерация HTML для звёзд рейтинга
function getStarsHTML(rating) {
    const fullStars = Math.floor(rating);
    const halfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (halfStar ? 1 : 0);
    
    let html = '';
    for (let i = 0; i < fullStars; i++) html += '★';
    if (halfStar) html += '☆';
    for (let i = 0; i < emptyStars; i++) html += '☆';
    
    return html;
}

// Открытие профиля
async function openProfile() {
    await loadProfileData(currentUser.telegram_id);
    showScreen('profile-screen');
}

// Закрытие профиля
function closeProfile() {
    showScreen('main-screen');
}

// Загрузка данных профиля
async function loadProfileData(telegramId) {
    try {
        const [rating, stats, reviews] = await Promise.all([
            fetchUserRating(telegramId),
            fetchUserStats(telegramId),
            fetchUserReviews(telegramId)
        ]);
        
        // Обновляем данные профиля
        const telegramUser = getTelegramUser();
        const avatarLarge = document.getElementById('profile-avatar-large');
        
        if (telegramUser && telegramUser.photo_url) {
            avatarLarge.style.backgroundImage = `url(${telegramUser.photo_url})`;
            avatarLarge.style.backgroundSize = 'cover';
            avatarLarge.style.backgroundPosition = 'center';
            avatarLarge.textContent = '';
        } else {
            const initial = (currentUser.name || 'U').charAt(0).toUpperCase();
            avatarLarge.textContent = initial;
            avatarLarge.style.backgroundImage = '';
        }
        
        document.getElementById('profile-name-large').textContent = currentUser.name || 'Пользователь';
        document.getElementById('profile-phone-large').textContent = formatPhoneNumber(currentUser.phone_number);
        document.getElementById('profile-role-large').textContent = currentUser.role === 'customer' ? 'Заказчик' : 'Водитель';
        
        // Статистика
        document.getElementById('stat-orders').textContent = stats.total_orders || 0;
        document.getElementById('stat-rating-value').textContent = (rating.average || 0).toFixed(1);
        document.getElementById('stat-reviews').textContent = rating.count || 0;
        
        // Отзывы
        renderReviews(reviews);
    } catch (error) {
        console.error('Ошибка загрузки профиля:', error);
        showError('Не удалось загрузить данные профиля');
    }
}

// Отрисовка отзывов
function renderReviews(reviews) {
    const reviewsList = document.getElementById('reviews-list');
    
    if (!reviews || reviews.length === 0) {
        reviewsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-title">Нет отзывов</div>
                <div class="empty-description">Здесь будут отображаться отзывы после выполнения заказов</div>
            </div>
        `;
        return;
    }
    
    reviewsList.innerHTML = reviews.map(review => `
        <div class="review-card">
            <div class="review-header">
                <div class="review-author">${review.reviewer_name}</div>
                <div class="review-rating">${'★'.repeat(review.rating)}${'☆'.repeat(5 - review.rating)}</div>
            </div>
            <div class="review-date">${formatLocalDateTime(review.created_at)}</div>
            ${review.comment ? `<div class="review-comment">${review.comment}</div>` : ''}
            <div class="review-order">Заказ #${review.order_id}</div>
        </div>
    `).join('');
}

function initNavMenu() {
    const navMenu = document.getElementById('nav-menu');
    const tabContent = document.getElementById('tab-content');
    
    navMenu.innerHTML = '';
    tabContent.innerHTML = '';
    
    let menuItems = [];
    
    if (currentUser.role === 'customer') {
        menuItems = [
            { id: 'searching', label: 'Поиск исполнителей', icon: '◉' },
            { id: 'created', label: 'Созданные заявки', icon: '○' },
            { id: 'in_progress', label: 'В процессе', icon: '⟳' },
            { id: 'closed', label: 'Закрытые', icon: '✓' }
        ];
    } else {
        menuItems = [
            { id: 'open', label: 'Открытые заявки', icon: '□' },
            { id: 'my_bids', label: 'Мои предложения', icon: '▪' },
            { id: 'in_progress', label: 'В процессе', icon: '⟳' },
            { id: 'closed', label: 'Завершённые', icon: '✓' }
        ];
    }
    
    menuItems.forEach((item, index) => {
        // Создаем пункт меню
        const menuItem = document.createElement('div');
        menuItem.className = 'menu-item' + (index === 0 ? ' active' : '');
        menuItem.dataset.tab = item.id;
        menuItem.innerHTML = `
            <div class="menu-item-content">
                <div class="menu-icon">${item.icon}</div>
                <div class="menu-label">${item.label}</div>
            </div>
            <span class="menu-badge" id="badge-${item.id}">0</span>
        `;
        menuItem.addEventListener('click', () => switchTab(item.id));
        navMenu.appendChild(menuItem);
        
        // Создаем контент вкладки
        const tabPane = document.createElement('div');
        tabPane.className = 'tab-pane' + (index === 0 ? ' active' : '');
        tabPane.id = `tab-${item.id}`;
        tabContent.appendChild(tabPane);
    });
    
    // Загружаем данные для первой вкладки
    currentTab = menuItems[0].id;
    loadTabData(currentTab);
}

async function switchTab(tabId) {
    // Обновляем активный пункт меню
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.toggle('active', item.dataset.tab === tabId);
    });
    
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.toggle('active', pane.id === `tab-${tabId}`);
    });
    
    currentTab = tabId;
    await loadTabData(tabId);
}

async function loadTabData(tabId, forceRefresh = false) {
    const tabPane = document.getElementById(`tab-${tabId}`);
    tabPane.innerHTML = '<div class="loading-container"><div class="spinner"></div><p style="margin-top: 10px; color: #666;">Загрузка данных...</p></div>';
    
    try {
        // Проверяем кэш
        const now = Date.now();
        const cacheValid = ordersCache && !forceRefresh && (now - ordersCacheTime < CACHE_DURATION);
        
        let orders;
        if (cacheValid) {
            // Используем кэш
            console.log('📦 Используем кэш данных (возраст: ' + Math.round((now - ordersCacheTime)/1000) + 's)');
            orders = ordersCache;
        } else {
            // Загружаем свежие данные
            console.log('🌐 Загружаем свежие данные с сервера...');
            if (currentUser.role === 'customer') {
                orders = await fetchCustomerOrders(currentUser.telegram_id);
            } else {
                orders = await fetchDriverOrders(currentUser.telegram_id);
            }
            // Сохраняем в кэш
            ordersCache = orders;
            ordersCacheTime = now;
            console.log('✅ Данные закэшированы');
        }
        
        // Отрисовываем данные для текущей вкладки
        if (currentUser.role === 'customer') {
            renderCustomerOrders(orders[tabId], tabPane, tabId);
        } else {
            renderDriverOrders(orders[tabId], tabPane, tabId);
        }
        
        // Обновляем бейджи для всех вкладок
        updateBadges(orders);
    } catch (error) {
        console.log('❌ Критическая ошибка загрузки: ' + error.message, 'error');
        tabPane.innerHTML = `
            <div class="empty-state">
                <div class="empty-title">Ошибка загрузки</div>
                <p style="color: #666; margin: 10px 0;">${error.message || 'Проверьте интернет-соединение'}</p>
                <button onclick="refreshOrders()" style="margin-top: 15px; padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 8px; cursor: pointer;">
                    Повторить
                </button>
            </div>
        `;
    }
}

// Функция для принудительного обновления данных
function refreshOrders() {
    ordersCache = null;
    ordersCacheTime = 0;
    loadTabData(currentTab, true);
}

function updateBadges(orders) {
    Object.keys(orders).forEach(key => {
        const badge = document.getElementById(`badge-${key}`);
        if (badge) {
            const count = orders[key].length;
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline-block' : 'none';
        }
    });
}

// Инициализация слайдеров для подтверждения выполнения заказа
function initSlideToConfirm() {
    const sliders = document.querySelectorAll('.slide-to-confirm:not(.confirmed)');
    
    sliders.forEach(slider => {
        const button = slider.querySelector('.slide-button');
        const track = slider.querySelector('.slide-track');
        const orderId = slider.dataset.orderId;
        
        // Пропускаем уже подтвержденные слайдеры
        if (!button || slider.classList.contains('confirmed')) {
            return;
        }
        
        let isDragging = false;
        let startX = 0;
        let currentX = 0;
        const trackWidth = track.offsetWidth;
        const buttonWidth = button.offsetWidth;
        const maxDrag = trackWidth - buttonWidth;
        
        // Обработчик начала касания/клика
        const handleStart = (e) => {
            isDragging = true;
            startX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
            button.style.transition = 'none';
            slider.classList.add('dragging');
        };
        
        // Обработчик движения
        const handleMove = (e) => {
            if (!isDragging) return;
            
            e.preventDefault();
            const clientX = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
            currentX = clientX - startX;
            
            // Ограничиваем движение
            if (currentX < 0) currentX = 0;
            if (currentX > maxDrag) currentX = maxDrag;
            
            button.style.transform = `translateX(${currentX}px)`;
            
            // Меняем прозрачность текста
            const progress = currentX / maxDrag;
            track.querySelector('.slide-text').style.opacity = 1 - progress;
        };
        
        // Обработчик окончания касания/клика
        const handleEnd = async () => {
            if (!isDragging) return;
            
            isDragging = false;
            button.style.transition = 'transform 0.3s ease';
            slider.classList.remove('dragging');
            
            // Проверяем, дотянули ли до конца (90% от максимума)
            if (currentX > maxDrag * 0.9) {
                // Успешное подтверждение
                slider.classList.add('confirmed');
                button.style.display = 'none';
                track.querySelector('.slide-text').textContent = '✓ Подтверждено';
                track.querySelector('.slide-text').style.opacity = '1';
                
                // Вызываем функцию подтверждения заказа
                await confirmOrderCompletion(orderId);
            } else {
                // Возвращаем кнопку обратно
                button.style.transform = 'translateX(0)';
                track.querySelector('.slide-text').style.opacity = '1';
            }
            
            currentX = 0;
        };
        
        // Добавляем обработчики событий
        button.addEventListener('mousedown', handleStart);
        button.addEventListener('touchstart', handleStart, { passive: false });
        
        document.addEventListener('mousemove', handleMove);
        document.addEventListener('touchmove', handleMove, { passive: false });
        
        document.addEventListener('mouseup', handleEnd);
        document.addEventListener('touchend', handleEnd);
    });
}

function renderCustomerOrders(orders, container, tabId) {
    if (!orders || orders.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-title">Нет заявок</div>
                <div class="empty-description">Создайте новую заявку на грузоперевозку</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = orders.map(order => `
        <div class="order-card">
            <div class="order-header">
                <div class="order-number">Заявка #${order.id}</div>
                <div class="order-status status-${tabId}">${(tabId === 'closed' || tabId === 'in_progress') ? getDetailedStatus(order) : getStatusLabel(tabId)}</div>
            </div>
            
            <div class="order-route">
                <div class="route-point">
                    <span class="route-icon">▸</span>
                    <span>${order.pickup_address}</span>
                </div>
                <div class="route-point">
                    <span class="route-icon">▸</span>
                    <span>${order.delivery_address}</span>
                </div>
            </div>
            
            <div class="order-description">${order.cargo_description}</div>
            
            <div class="order-meta">
                <span>${getTruckTypeName(order.truck_type)}</span>
                <span>${formatDate(order.created_at)}</span>
                ${order.delivery_date ? `<span>Доставка: ${order.delivery_date}</span>` : ''}
                ${order.max_price ? `<span>Цена: ${formatPrice(order.max_price)}</span>` : ''}
            </div>
            
            ${tabId === 'closed' && order.cancellation_reason ? `
                <div class="order-comment">
                    <strong>Причина отмены:</strong> ${order.cancellation_reason}
                </div>
            ` : ''}
            
            ${tabId === 'closed' && order.status === 'completed' && order.winner_driver_id ? `
                <div class="order-footer">
                    <div style="flex: 1;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 4px;">Исполнитель:</div>
                        <div style="font-weight: 600;">${order.driver_name || 'Водитель'}</div>
                        ${order.winning_price ? `<div style="color: #4CAF50; font-weight: 600; margin-top: 4px;">${formatPrice(order.winning_price)}</div>` : ''}
                    </div>
                    ${!order.customer_reviewed ? `
                        <button class="btn btn-small btn-primary" onclick="openReviewModal(${order.id}, ${order.winner_driver_id}, '${order.driver_name || 'Водитель'}')">
                            Оценить
                        </button>
                    ` : `
                        <div style="color: #4CAF50; font-size: 12px;">✓ Оценка оставлена</div>
                    `}
                </div>
            ` : ''}
            
            ${tabId === 'searching' ? `
                <div class="order-footer">
                    <div class="bids-info">
                        Предложений: <span class="bids-count">${order.bids_count || 0}</span>
                        ${order.min_bid_price ? `<br>От <span class="min-price">${formatPrice(order.min_bid_price)}</span>` : ''}
                    </div>
                    <button class="btn btn-small btn-primary" onclick="viewOrderBids(${order.id})">
                        Смотреть
                    </button>
                </div>
            ` : ''}
            ${tabId === 'in_progress' && order.status === 'auction_completed' ? `
                <div class="order-footer">
                    <div class="bids-info">
                        Получено предложений: <span class="bids-count">${order.bids_count || 0}</span>
                        ${order.min_bid_price ? `<br>Минимальная цена: <span class="min-price">${formatPrice(order.min_bid_price)}</span>` : ''}
                    </div>
                    <button class="btn btn-small btn-success" onclick="viewAndSelectBids(${order.id})">
                        Выбрать исполнителя
                    </button>
                </div>
            ` : ''}
            ${tabId === 'in_progress' && order.status === 'in_progress' ? `
                <div style="margin-top: 10px;">
                    ${order.customer_confirmed ? `
                        <div class="slide-to-confirm confirmed">
                            <div class="slide-track">
                                <span class="slide-text">✓ Ожидание подтверждения водителем</span>
                            </div>
                        </div>
                    ` : `
                        <div class="slide-to-confirm" id="slide-confirm-${order.id}" data-order-id="${order.id}" data-role="customer">
                            <div class="slide-track">
                                <span class="slide-text">Проведите для подтверждения</span>
                            </div>
                            <div class="slide-button">
                                <span class="slide-icon">→</span>
                            </div>
                        </div>
                    `}
                </div>
                <div style="margin-top: 10px;">
                    <button class="btn btn-small btn-danger" onclick="cancelOrder(${order.id})" style="width: 100%;">
                        Отменить заказ
                    </button>
                </div>
            ` : ''}
        </div>
    `).join('');
    
    // Инициализируем слайдеры для подтверждения
    initSlideToConfirm();
}

function renderDriverOrders(orders, container, tabId) {
    if (!orders || orders.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-title">Нет заявок</div>
                <div class="empty-description">${getEmptyMessage(tabId)}</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = orders.map(order => `
        <div class="order-card">
            <div class="order-header">
                <div class="order-number">Заявка #${order.id}</div>
                <div class="order-status status-${tabId}">${(tabId === 'closed' || tabId === 'in_progress') ? getDetailedStatus(order) : getStatusLabel(tabId)}</div>
            </div>
            
            <div class="order-route">
                <div class="route-point">
                    <span class="route-icon">▸</span>
                    <span>${order.pickup_address}</span>
                </div>
                <div class="route-point">
                    <span class="route-icon">▸</span>
                    <span>${order.delivery_address}</span>
                </div>
            </div>
            
            <div class="order-description">${order.cargo_description}</div>
            
            <div class="order-meta">
                <span>${getTruckTypeName(order.truck_type)}</span>
                <span>${formatDate(order.created_at)}</span>
                ${order.delivery_date ? `<span>Доставка: ${order.delivery_date}</span>` : ''}
                ${order.max_price ? `<span>Цена: ${formatPrice(order.max_price)}</span>` : ''}
                ${order.total_bids ? `<span>${order.total_bids} предложений</span>` : ''}
            </div>
            
            ${tabId === 'closed' && order.cancellation_reason ? `
                <div class="order-comment">
                    <strong>Причина отмены:</strong> ${order.cancellation_reason}
                </div>
            ` : ''}
            
            ${tabId === 'closed' && order.status === 'completed' && order.customer_id ? `
                <div class="order-footer">
                    <div style="flex: 1;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 4px;">Заказчик:</div>
                        <div style="font-weight: 600;">${order.customer_name || 'Заказчик'}</div>
                        ${order.winning_price ? `<div style="color: #4CAF50; font-weight: 600; margin-top: 4px;">${formatPrice(order.winning_price)}</div>` : ''}
                    </div>
                    ${!order.driver_reviewed ? `
                        <button class="btn btn-small btn-primary" onclick="openReviewModal(${order.id}, ${order.customer_id}, '${order.customer_name || 'Заказчик'}')">
                            Оценить
                        </button>
                    ` : `
                        <div style="color: #4CAF50; font-size: 12px;">✓ Оценка оставлена</div>
                    `}
                </div>
            ` : ''}
            
            <div class="order-footer">
                ${order.my_bid_price ? `
                    <div class="my-bid-price">Моя ставка: ${formatPrice(order.my_bid_price)}</div>
                ` : ''}
                ${tabId === 'open' ? `
                    <button class="btn btn-small btn-primary" onclick="openBidModal(${order.id}, '${order.pickup_address}', '${order.delivery_address}', '${order.cargo_description}')">
                        Сделать предложение
                    </button>
                ` : ''}
            </div>
            ${tabId === 'in_progress' ? `
                <div style="margin-top: 10px; padding: 0 16px;">
                    ${(order.driver_confirmed === 1 || order.driver_confirmed === true) ? `
                        <div class="slide-to-confirm confirmed">
                            <div class="slide-track">
                                <span class="slide-text">✓ Ожидание подтверждения заказчиком</span>
                            </div>
                        </div>
                    ` : `
                        <div class="slide-to-confirm" id="slide-confirm-driver-${order.id}" data-order-id="${order.id}" data-role="driver">
                            <div class="slide-track">
                                <span class="slide-text">Проведите для подтверждения</span>
                            </div>
                            <div class="slide-button">
                                <span class="slide-icon">→</span>
                            </div>
                        </div>
                    `}
                </div>
            ` : ''}
        </div>
    `).join('');
    
    // Инициализируем слайдеры для подтверждения
    initSlideToConfirm();
}

// === МОДАЛЬНЫЕ ОКНА ===
function initModals() {
    // Создание заявки
    const createOrderBtn = document.getElementById('create-order-btn');
    const createOrderModal = document.getElementById('create-order-modal');
    const createOrderForm = document.getElementById('create-order-form');
    const cancelOrderBtn = document.getElementById('cancel-order');
    
    if (createOrderBtn) {
        createOrderBtn.addEventListener('click', () => {
            createOrderModal.classList.remove('hidden');
        });
    }
    
    if (cancelOrderBtn) {
        cancelOrderBtn.addEventListener('click', () => {
            createOrderModal.classList.add('hidden');
            createOrderForm.reset();
        });
    }
    
    if (createOrderForm) {
        createOrderForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const orderData = {
                truck_type_id: document.getElementById('truck-type').value,
                pickup_location: document.getElementById('pickup-location').value,
                delivery_location: document.getElementById('delivery-location').value,
                description: document.getElementById('description').value,
                cargo_weight: document.getElementById('cargo-weight').value || null,
                cargo_volume: document.getElementById('cargo-volume').value || null,
                price: document.getElementById('price').value || null,
                delivery_date: document.getElementById('delivery-date').value || null
            };
            
            try {
                await createOrder(orderData);
                createOrderModal.classList.add('hidden');
                createOrderForm.reset();
                showSuccess('Заявка создана успешно!');
                refreshOrders(); // Обновляем данные
            } catch (error) {
                showError('Ошибка создания заявки');
            }
        });
    }
    
    // Создание предложения
    const createBidForm = document.getElementById('create-bid-form');
    const cancelBidBtn = document.getElementById('cancel-bid');
    
    if (cancelBidBtn) {
        cancelBidBtn.addEventListener('click', () => {
            document.getElementById('create-bid-modal').classList.add('hidden');
            createBidForm.reset();
        });
    }
    
    if (createBidForm) {
        createBidForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const bidData = {
                order_id: currentOrderForBid,
                price: parseInt(document.getElementById('bid-price').value)
            };
            
            try {
                await createBid(bidData);
                document.getElementById('create-bid-modal').classList.add('hidden');
                createBidForm.reset();
                showSuccess('Предложение отправлено!');
                refreshOrders(); // Обновляем данные
            } catch (error) {
                showError('Ошибка отправки предложения');
            }
        });
    }
    
    // Закрытие модалок по клику на overlay или крестик
    document.querySelectorAll('.modal-close, .modal-overlay').forEach(el => {
        el.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) modal.classList.add('hidden');
        });
    });

    // Отмена заявки
    const cancelOrderModal = document.getElementById('cancel-order-modal');
    const cancelOrderForm = document.getElementById('cancel-order-form');
    const cancelCancellationBtn = document.getElementById('cancel-cancellation');
    
    if (cancelCancellationBtn) {
        cancelCancellationBtn.addEventListener('click', () => {
            cancelOrderModal.classList.add('hidden');
            cancelOrderForm.reset();
            currentOrderForCancellation = null;
        });
    }
    
    if (cancelOrderForm) {
        cancelOrderForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const reason = document.getElementById('cancellation-reason').value;
            
            try {
                const response = await fetchWithTimeout(`${API_BASE}api/orders/${currentOrderForCancellation}/cancel`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        telegram_id: currentUser.telegram_id,
                        cancellation_reason: reason
                    })
                }, 15000);
                
                if (!response.ok) {
                    throw new Error('Ошибка отмены заказа');
                }
                
                cancelOrderModal.classList.add('hidden');
                cancelOrderForm.reset();
                currentOrderForCancellation = null;
                showSuccess('Заказ отменен');
                refreshOrders();
            } catch (error) {
                showError('Ошибка отмены заказа');
            }
        });
    }
    
    // Модальное окно отзыва
    const reviewModal = document.getElementById('review-modal');
    const reviewForm = document.getElementById('review-form');
    const cancelReviewBtn = document.getElementById('cancel-review');
    const ratingStars = document.querySelectorAll('.rating-star');
    
    // Обработчики для звёзд рейтинга
    ratingStars.forEach(star => {
        star.addEventListener('click', () => {
            const rating = parseInt(star.dataset.rating);
            document.getElementById('rating-value').value = rating;
            
            ratingStars.forEach(s => {
                const starRating = parseInt(s.dataset.rating);
                s.classList.toggle('active', starRating <= rating);
            });
        });
    });
    
    if (cancelReviewBtn) {
        cancelReviewBtn.addEventListener('click', () => {
            reviewModal.classList.add('hidden');
            reviewForm.reset();
            ratingStars.forEach(s => s.classList.remove('active'));
        });
    }
    
    if (reviewForm) {
        reviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const orderId = parseInt(document.getElementById('review-order-id').value);
            const revieweeId = parseInt(document.getElementById('review-user-id').value);
            const rating = parseInt(document.getElementById('rating-value').value);
            const comment = document.getElementById('review-comment').value;
            
            if (!rating) {
                showError('Пожалуйста, выберите оценку');
                return;
            }
            
            try {
                await submitReview(orderId, revieweeId, rating, comment);
                reviewModal.classList.add('hidden');
                reviewForm.reset();
                ratingStars.forEach(s => s.classList.remove('active'));
                showSuccess('Спасибо за ваш отзыв!');
                refreshOrders();
            } catch (error) {
                showError('Ошибка отправки отзыва');
            }
        });
    }
}

async function loadTruckTypes() {
    // Если truckTypesMap уже заполнен, не загружаем повторно
    if (Object.keys(truckTypesMap).length > 0) {
        return;
    }
    
    try {
        const data = await fetchTruckTypes();
        const select = document.getElementById('truck-type');
        
        // Очищаем существующие опции (кроме placeholder)
        while (select.options.length > 1) {
            select.remove(1);
        }
        
        // Заполняем truckTypesMap и создаем опции для select
        data.forEach(category => {
            // Создаем группу для категории
            const optgroup = document.createElement('optgroup');
            optgroup.label = category.name; // Исправлено: было category.category
            
            category.types.forEach(type => {
                // Сохраняем в map для использования в getTruckTypeName
                truckTypesMap[type.id] = type.full_name || type.name;
                
                // Создаем option
                const option = document.createElement('option');
                option.value = type.id;
                option.textContent = type.name; // Исправлено: убрали несуществующий emoji
                optgroup.appendChild(option);
            });
            
            select.appendChild(optgroup);
        });
    } catch (error) {
        console.error('Ошибка загрузки типов грузовиков:', error);
    }
}

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
function getTruckTypeName(typeId) {
    // Возвращаем имя из map или "Не указан" если не найдено
    return truckTypesMap[typeId] || 'Не указан';
}

window.openBidModal = function(orderId, pickup, delivery, description) {
    currentOrderForBid = orderId;
    
    document.getElementById('bid-order-info').innerHTML = `
        <div class="order-route">
            <div class="route-point">
                <span class="route-icon">📍</span>
                <span>${pickup}</span>
            </div>
            <div class="route-point">
                <span class="route-icon">🎯</span>
                <span>${delivery}</span>
            </div>
        </div>
        <div class="order-description">${description}</div>
    `;
    
    document.getElementById('create-bid-modal').classList.remove('hidden');
};

window.viewOrderBids = async function(orderId) {
    try {
        const bids = await fetchOrderBids(orderId);
        const modal = document.getElementById('view-bids-modal');
        const bidsList = document.getElementById('bids-list');
        
        if (bids.length === 0) {
            bidsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-title">Нет предложений</div>
                </div>
            `;
        } else {
            bidsList.innerHTML = bids.map((bid, index) => `
                <div class="bid-card">
                    <div class="bid-header">
                        <div class="bid-driver">${index + 1}. ${bid.name || 'Водитель'}</div>
                        <div class="bid-price">${formatPrice(bid.price)}</div>
                    </div>
                    <div class="bid-meta">
                        <span> ${formatDate(bid.created_at)}</span>
                    </div>
                    <button class="btn btn-primary" onclick="selectWinner(${orderId}, ${bid.id})" style="width: 100%; margin-top: 10px;">
                        Выбрать исполнителем
                    </button>
                </div>
            `).join('');
        }
        
        modal.classList.remove('hidden');
    } catch (error) {
        showError('Ошибка загрузки предложений');
    }
};

window.selectWinner = async function(orderId, bidId) {
    try {
        const response = await fetchWithTimeout(`${API_BASE}api/orders/${orderId}/select-winner`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: currentUser.telegram_id,
                bid_id: bidId
            })
        }, 15000);
        
        if (!response.ok) {
            throw new Error('Ошибка выбора исполнителя');
        }
        
        document.getElementById('view-bids-modal').classList.add('hidden');
        showSuccess('Исполнитель выбран! Заявка перемещена в "В процессе"');
        refreshOrders();
    } catch (error) {
        showError('Ошибка выбора исполнителя');
    }
};

window.viewAndSelectBids = async function(orderId) {
    try {
        const bids = await fetchOrderBids(orderId);
        const modal = document.getElementById('view-bids-modal');
        const bidsList = document.getElementById('bids-list');
        
        if (bids.length === 0) {
            bidsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-title">Нет предложений</div>
                    <div class="empty-description">Предложения от водителей не поступили</div>
                </div>
            `;
        } else {
            bidsList.innerHTML = bids.map((bid, index) => `
                <div class="bid-card">
                    <div class="bid-header">
                        <div class="bid-driver">${index + 1}. ${bid.name || 'Водитель'}</div>
                        <div class="bid-price">${formatPrice(bid.price)}</div>
                    </div>
                    <div class="bid-contact">
                        📞 ${bid.phone_number || 'Телефон не указан'}
                    </div>
                    <div class="bid-meta">
                        <span>📅 ${formatDate(bid.created_at)}</span>
                    </div>
                    <button class="btn btn-success" onclick="selectWinner(${orderId}, ${bid.id})" style="width: 100%; margin-top: 10px;">
                        ✅ Выбрать исполнителем
                    </button>
                </div>
            `).join('');
        }
        
        // Обновляем заголовок модального окна
        const modalHeader = modal.querySelector('.modal-header h2');
        modalHeader.textContent = `Выбор исполнителя (${bids.length} предложений)`;
        
        modal.classList.remove('hidden');
    } catch (error) {
        showError('Ошибка загрузки предложений');
    }
};

window.confirmOrderCompletion = async function(orderId) {
    try {
        const response = await fetchWithTimeout(`${API_BASE}api/orders/${orderId}/confirm-completion`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: currentUser.telegram_id
            })
        }, 15000);
        
        if (!response.ok) {
            throw new Error('Ошибка подтверждения выполнения');
        }
        
        showSuccess('Выполнение подтверждено!');
        refreshOrders();
    } catch (error) {
        showError('Ошибка подтверждения выполнения');
    }
};

window.cancelOrder = async function(orderId) {
    currentOrderForCancellation = orderId;
    document.getElementById('cancel-order-modal').classList.remove('hidden');
};

function showSuccess(message) {
    if (tg && tg.showAlert) {
        tg.showAlert(message);
    } else {
        alert(message);
    }
}

function getStatusLabel(status) {
    const labels = {
        'searching': 'Поиск',
        'created': 'Создана',
        'completed': 'Завершена',
        'auction_completed': 'Прием заявок завершен',
        'open': 'Открыта',
        'my_bids': 'Предложено',
        'in_progress': 'В процессе',
        'closed': 'Закрыта'
    };
    return labels[status] || status;
}

function getDetailedStatus(order) {
    // Для закрытых заявок определяем детальный статус
    if (order.status === 'closed') {
        // Если обе стороны подтвердили выполнение
        if (order.customer_confirmed && order.driver_confirmed) {
            return 'Выполнена';
        }
        // Если есть отмена
        if (order.cancelled_by) {
            // Определяем кто отменил
            const isCancelledByCustomer = order.cancelled_by === order.customer_id;
            return isCancelledByCustomer ? 'Отменена (заказчиком)' : 'Отменена (исполнителем)';
        }
        // Если нет предложений
        if (order.status === 'no_offers') {
            return 'Закрыта (нет предложений)';
        }
    }
    
    // Для заявок с завершенным подбором
    if (order.status === 'auction_completed') {
        return 'Прием заявок завершен';
    }
    
    return getStatusLabel(order.status);
}

function getEmptyMessage(tabId) {
    const messages = {
        'open': 'Новые заявки появятся здесь',
        'my_bids': 'Вы еще не делали предложений',
        'closed': 'Нет закрытых заявок'
    };
    return messages[tabId] || '';
}

function formatPrice(price) {
    if (!price || isNaN(price)) {
        return 'Не указана';
    }
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(price);
}

function formatDate(dateString) {
    if (!dateString) return 'Не указано';
    
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'Неверная дата';
    
    // Всегда показываем полную дату и время
    return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showError(message) {
    if (tg && tg.showAlert) {
        tg.showAlert(message);
    } else {
        alert(message);
    }
}

// Открыть чат с администратором
function contactAdmin() {
    const message = "Здравствуйте! Хотел бы сообщить о проблеме с приложением FreightHub.";
    const url = `https://t.me/mosdefkweli?text=${encodeURIComponent(message)}`;
    
    if (tg && tg.openTelegramLink) {
        tg.openTelegramLink(url);
    } else {
        window.open(url, '_blank');
    }
}

// Открыть модальное окно для оценки пользователя
function openReviewModal(orderId, userId, userName) {
    const modal = document.getElementById('review-modal');
    document.getElementById('review-order-id').value = orderId;
    document.getElementById('review-user-id').value = userId;
    document.getElementById('review-user-name').textContent = userName;
    
    // Сбросить звёзды
    document.querySelectorAll('.rating-star').forEach(s => s.classList.remove('active'));
    document.getElementById('rating-value').value = '';
    document.getElementById('review-comment').value = '';
    
    modal.classList.remove('hidden');
}


