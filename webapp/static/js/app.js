// Telegram Web App API
const tg = window.Telegram?.WebApp;

// Применение темы Telegram
function applyTelegramTheme() {
    let isDark = false;
    
    if (tg) {
        // Проверяем colorScheme
        if (tg.colorScheme === 'dark') {
            isDark = true;
        }
        // Проверяем bg_color
        else if (tg.themeParams?.bg_color) {
            const color = tg.themeParams.bg_color.replace('#', '');
            const r = parseInt(color.substr(0, 2), 16);
            const g = parseInt(color.substr(2, 2), 16);
            const b = parseInt(color.substr(4, 2), 16);
            const brightness = (r * 299 + g * 587 + b * 114) / 1000;
            isDark = brightness < 128;
        }
    }
    
    // Применяем класс
    if (isDark) {
        document.body.classList.add('theme-dark');
    } else {
        document.body.classList.remove('theme-dark');
    }
}

// Применяем тему сразу
applyTelegramTheme();

if (tg) {
    tg.ready();
    tg.expand();
    tg.MainButton.hide();
    
    // Применяем тему после ready
    setTimeout(applyTelegramTheme, 100);
    
    // Слушаем события изменения темы
    tg.onEvent('themeChanged', applyTelegramTheme);
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
        // Если дата не содержит информации о временной зоне, добавляем UTC
        let dateToFormat = utcDateString;
        if (!utcDateString.includes('Z') && !utcDateString.includes('+') && !utcDateString.includes('T')) {
            // Формат SQLite: YYYY-MM-DD HH:MM:SS - добавляем 'Z' чтобы указать что это UTC
            dateToFormat = utcDateString.replace(' ', 'T') + 'Z';
        } else if (utcDateString.includes(' ') && !utcDateString.includes('Z')) {
            // Если есть пробел вместо T, но нет Z
            dateToFormat = utcDateString.replace(' ', 'T') + 'Z';
        }
        
        const date = new Date(dateToFormat);
        if (isNaN(date.getTime())) return utcDateString;
        
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

// Функция для отображения звезд рейтинга
function renderStars(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    let stars = '';
    
    // Полные звезды
    for (let i = 0; i < fullStars; i++) {
        stars += '★';
    }
    
    // Половинка звезды
    if (hasHalfStar) {
        stars += '☆';
    }
    
    // Пустые звезды
    for (let i = 0; i < emptyStars; i++) {
        stars += '☆';
    }
    
    return stars;
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
    try {
        const response = await fetchWithTimeout(`${API_BASE}api/orders/${orderId}/bids?telegram_id=${currentUser.telegram_id}`, {}, 10000);
        if (!response.ok) {
            console.error(`Failed to fetch bids: ${response.status} ${response.statusText}`);
            return [];
        }
        return await response.json();
    } catch (error) {
        console.error('Error fetching bids:', error);
        return [];
    }
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

async function submitReview(orderId, revieweeTelegramId, rating, comment, badges) {
    const response = await fetchWithTimeout(`${API_BASE}api/reviews/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            order_id: orderId,
            reviewer_telegram_id: currentUser.telegram_id,
            reviewee_telegram_id: revieweeTelegramId,
            rating: rating,
            comment: comment,
            punctuality_rating: null,
            quality_rating: null,
            professionalism_rating: null,
            communication_rating: null,
            vehicle_condition_rating: null,
            badges: badges,
            is_public: true
        })
    }, 15000);
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Ошибка отправки отзыва');
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
async function openProfile(userId = null) {
    const targetUserId = userId || currentUser.telegram_id;
    await loadProfileData(targetUserId);
    showScreen('profile-screen');
}

// Закрытие профиля
function closeProfile() {
    showScreen('main-screen');
}

// Загрузка данных профиля
async function loadProfileData(telegramId) {
    try {
        // Получаем данные пользователя
        const userResponse = await fetchWithTimeout(`${API_BASE}api/user/${telegramId}`, {}, 10000);
        const userData = await userResponse.json();
        
        const [rating, stats, reviews] = await Promise.all([
            fetchUserRating(telegramId),
            fetchUserStats(telegramId),
            fetchUserReviews(telegramId)
        ]);
        
        // Обновляем данные профиля
        const avatarLarge = document.getElementById('profile-avatar-large');
        
        avatarLarge.textContent = (userData.name || 'U').charAt(0).toUpperCase();
        avatarLarge.style.backgroundImage = '';
        
        document.getElementById('profile-name-large').textContent = userData.name || 'Пользователь';
        document.getElementById('profile-phone-large').textContent = formatPhoneNumber(userData.phone_number || '');
        document.getElementById('profile-role-large').textContent = userData.role === 'customer' ? 'Заказчик' : 'Водитель';
        
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

// Загрузка и отображение фотографий заказа
async function loadOrderPhotos(orderId) {
    try {
        const telegram_id = window.Telegram.WebApp.initDataUnsafe.user?.id;
        if (!telegram_id) {
            console.error('[LOAD PHOTOS] User ID not available');
            return;
        }

        console.log(`[LOAD PHOTOS] Loading photos for order ${orderId}, user ${telegram_id}`);

        const response = await fetch(`${API_BASE}api/orders/${orderId}/photos`, {
            headers: {
                'telegram-id': telegram_id.toString()
            }
        });

        console.log(`[LOAD PHOTOS] Response status: ${response.status}`);

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[LOAD PHOTOS] Failed to fetch photos: ${response.status} - ${errorText}`);
            return;
        }

        const photos = await response.json();
        console.log(`[LOAD PHOTOS] Received photos:`, photos);
        const container = document.getElementById(`photos-section-${orderId}`);
        console.log(`[LOAD PHOTOS] Container for order ${orderId}:`, container);
        
        if (!container) {
            console.error(`[LOAD PHOTOS] Container photos-section-${orderId} not found!`);
            return;
        }

        let html = '';

        // Секция фотографий загрузки
        if (photos.loading && photos.loading.length > 0) {
            html += `
                <div class="photo-stage">
                    <div class="photo-stage-title">Фото загрузки груза</div>
                    <div class="photo-grid">
                        ${photos.loading.map(photo => `
                            <img src="${API_BASE}api/photos/${photo.id}?telegram_id=${telegram_id}" 
                                 class="photo-thumbnail" 
                                 onclick="openPhotoModal('${API_BASE}api/photos/${photo.id}?telegram_id=${telegram_id}')"
                                 alt="Фото загрузки">
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Секция фотографий выгрузки
        if (photos.unloading && photos.unloading.length > 0) {
            html += `
                <div class="photo-stage">
                    <div class="photo-stage-title">Фото выгрузки груза</div>
                    <div class="photo-grid">
                        ${photos.unloading.map(photo => `
                            <img src="${API_BASE}api/photos/${photo.id}?telegram_id=${telegram_id}" 
                                 class="photo-thumbnail" 
                                 onclick="openPhotoModal('${API_BASE}api/photos/${photo.id}?telegram_id=${telegram_id}')"
                                 alt="Фото выгрузки">
                        `).join('')}
                    </div>
                </div>
            `;
        }

        console.log(`[LOAD PHOTOS] Generated HTML length: ${html.length} chars`);
        console.log(`[LOAD PHOTOS] HTML preview:`, html.substring(0, 200));
        container.innerHTML = html;
        console.log(`[LOAD PHOTOS] HTML injected into container`);
    } catch (error) {
        console.error('[LOAD PHOTOS] Error loading order photos:', error);
    }
}

// Открытие модального окна с фотографией
function openPhotoModal(photoUrl) {
    const modal = document.createElement('div');
    modal.className = 'photo-modal';
    modal.innerHTML = `
        <div class="photo-modal-content">
            <span class="photo-modal-close" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <img src="${photoUrl}" alt="Фото">
        </div>
    `;
    modal.onclick = (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    };
    document.body.appendChild(modal);
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
                <div class="order-status status-${tabId}">${(tabId === 'closed' || tabId === 'in_progress' || order.status === 'no_offers') ? getDetailedStatus(order) : getStatusLabel(tabId)}</div>
            </div>
            
            <div class="order-route">
                <div class="route-point">
                    <span class="route-icon">▸</span>
                    <span><strong>Адрес отправки:</strong> ${order.pickup_address}</span>
                </div>
                <div class="route-point">
                    <span class="route-icon">▸</span>
                    <span><strong>Адрес доставки:</strong> ${order.delivery_address}</span>
                </div>
            </div>
            
            <div class="order-description"><strong>Описание:</strong> ${order.cargo_description}</div>
            
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
            
            ${tabId === 'closed' && order.status === 'closed' && order.customer_confirmed && order.driver_confirmed && order.winner_driver_id ? `
                <div id="photos-section-${order.id}" class="photos-section" style="margin-top: 15px;"></div>
                <div class="order-footer">
                    <div style="flex: 1;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 4px;">Исполнитель:</div>
                        <div style="font-weight: 600;">${order.driver_name || 'Водитель'}</div>
                        ${order.winning_price ? `<div style="color: #4CAF50; font-weight: 600; margin-top: 4px;">${formatPrice(order.winning_price)}</div>` : ''}
                    </div>
                    ${!order.customer_reviewed ? `
                        <button class="btn btn-small btn-primary" onclick="openReviewModal(${order.id}, ${order.winner_driver_id}, '${(order.driver_name || 'Водитель').replace(/'/g, "\\'")}', ${order.winner_telegram_id})">
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
                <div style="margin-top: 15px; padding: 12px; background: var(--input-bg); border-radius: 8px;">
                    <div style="font-size: 14px; font-weight: 600; margin-bottom: 8px;">Статус выполнения:</div>
                    <div style="font-size: 13px; color: var(--tg-theme-hint-color);">
                        ${!order.loading_confirmed_at ? '⏳ Водитель готовится к загрузке груза' : 
                          !order.unloading_confirmed_at ? '🚛 Груз загружен, в пути к месту доставки' :
                          !order.driver_completed_at ? '📦 Груз доставлен, ожидание подтверждения водителя' :
                          !order.customer_confirmed ? '✅ Водитель подтвердил выполнение, ожидается ваше подтверждение' :
                          '✅ Заказ выполнен'}
                    </div>
                </div>
                <div id="photos-section-${order.id}" class="photos-section" style="margin-top: 15px;"></div>
                <div style="margin-top: 15px; display: flex; gap: 8px;">
                    <button class="btn btn-small btn-primary" onclick="openChat(${order.id}, '${(order.driver_name || 'Водитель').replace(/'/g, "\\'")}', 'driver')" style="flex: 1;">
                        💬 Чат с водителем
                    </button>
                </div>
                <div style="margin-top: 10px;">
                    ${order.customer_confirmed ? `
                        <div class="slide-to-confirm confirmed">
                            <div class="slide-track">
                                <span class="slide-text">✓ Ожидание подтверждения водителем</span>
                            </div>
                        </div>
                    ` : order.driver_completed_at ? `
                        <div class="slide-to-confirm" id="slide-confirm-${order.id}" data-order-id="${order.id}" data-role="customer">
                            <div class="slide-track">
                                <span class="slide-text">Проведите для подтверждения</span>
                            </div>
                            <div class="slide-button">
                                <span class="slide-icon">→</span>
                            </div>
                        </div>
                    ` : `
                        <div class="slide-to-confirm disabled">
                            <div class="slide-track">
                                <span class="slide-text">Ожидание подтверждения водителем</span>
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
    
    // Загружаем фотографии для заказов в работе и завершенных
    if (tabId === 'in_progress') {
        orders.forEach(order => {
            if (order.status === 'in_progress') {
                loadOrderPhotos(order.id);
            }
        });
    } else if (tabId === 'closed') {
        orders.forEach(order => {
            if (order.status === 'closed' && order.customer_confirmed && order.driver_confirmed && order.winner_driver_id) {
                loadOrderPhotos(order.id);
            }
        });
    }
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
                <div class="order-status status-${tabId}">${(tabId === 'closed' || tabId === 'in_progress' || order.status === 'no_offers') ? getDetailedStatus(order) : getStatusLabel(tabId)}</div>
            </div>
            
            <div class="order-route">
                <div class="route-point">
                    <span class="route-icon">▸</span>
                    <span><strong>Адрес отправки:</strong> ${order.pickup_address}</span>
                </div>
                <div class="route-point">
                    <span class="route-icon">▸</span>
                    <span><strong>Адрес доставки:</strong> ${order.delivery_address}</span>
                </div>
            </div>
            
            <div class="order-description"><strong>Описание:</strong> ${order.cargo_description}</div>
            
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
            
            ${tabId === 'closed' && order.status === 'closed' && order.customer_confirmed && order.driver_confirmed && order.customer_id ? `
                <div id="photos-section-${order.id}" class="photos-section" style="margin-top: 15px;"></div>
                <div class="order-footer">
                    <div style="flex: 1;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 4px;">Заказчик:</div>
                        <div style="font-weight: 600;">${order.customer_name || 'Заказчик'}</div>
                        ${order.winning_price ? `<div style="color: #4CAF50; font-weight: 600; margin-top: 4px;">${formatPrice(order.winning_price)}</div>` : ''}
                    </div>
                    ${!order.driver_reviewed ? `
                        <button class="btn btn-small btn-primary" onclick="openReviewModal(${order.id}, ${order.customer_id}, '${(order.customer_name || 'Заказчик').replace(/'/g, "\\'")}', ${order.customer_telegram_id})">
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
                <div id="photos-section-${order.id}" class="photos-section" style="margin-top: 15px;"></div>
                <div style="margin-top: 10px; padding: 0 16px;">
                    <button class="btn btn-small btn-primary" onclick="openChat(${order.id}, '${(order.customer_name || 'Заказчик').replace(/'/g, "\\'")}', 'customer')" style="width: 100%; margin-bottom: 10px;">
                        💬 Чат с заказчиком
                    </button>
                    ${(order.driver_confirmed === 1 || order.driver_confirmed === true) ? `
                        <div class="slide-to-confirm confirmed">
                            <div class="slide-track">
                                <span class="slide-text">✓ Ожидание подтверждения заказчиком</span>
                            </div>
                        </div>
                        <button class="btn btn-small btn-danger" onclick="cancelOrder(${order.id})" style="width: 100%; margin-top: 10px;">
                            Отменить заказ
                        </button>
                    ` : (order.unloading_confirmed_at && !order.driver_completed_at) ? `
                        <div class="slide-to-confirm" id="slide-confirm-driver-${order.id}" data-order-id="${order.id}" data-role="driver">
                            <div class="slide-track">
                                <span class="slide-text">Проведите для подтверждения</span>
                            </div>
                            <div class="slide-button">
                                <span class="slide-icon">→</span>
                            </div>
                        </div>
                        <button class="btn btn-small btn-danger" onclick="cancelOrder(${order.id})" style="width: 100%; margin-top: 10px;">
                            Отменить заказ
                        </button>
                    ` : (order.loading_confirmed_at && !order.unloading_confirmed_at) ? `
                        <button class="btn btn-primary" onclick="openPhotoUploadModal(${order.id}, 'unloading')" style="width: 100%;">
                            📤 Загрузить фото выгрузки
                        </button>
                        <button class="btn btn-small btn-danger" onclick="cancelOrder(${order.id})" style="width: 100%; margin-top: 10px;">
                            Отменить заказ
                        </button>
                    ` : `
                        <button class="btn btn-primary" onclick="openPhotoUploadModal(${order.id}, 'loading')" style="width: 100%;">
                            📦 Загрузить фото загрузки
                        </button>
                        <button class="btn btn-small btn-danger" onclick="cancelOrder(${order.id})" style="width: 100%; margin-top: 10px;">
                            Отменить заказ
                        </button>
                    `}
                </div>
            ` : ''}
        </div>
    `).join('');
    
    // Инициализируем слайдеры для подтверждения
    initSlideToConfirm();
    
    // Загружаем фотографии для заказов в работе и завершенных
    if (tabId === 'in_progress') {
        orders.forEach(order => {
            if (order.status === 'in_progress') {
                loadOrderPhotos(order.id);
            }
        });
    } else if (tabId === 'closed') {
        orders.forEach(order => {
            if (order.status === 'closed' && order.customer_confirmed && order.driver_confirmed && order.customer_id) {
                loadOrderPhotos(order.id);
            }
        });
    }
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
    
    // Состояние для комплиментов
    let selectedBadges = [];
    
    // Загрузка комплиментов
    async function loadBadges() {
        try {
            const response = await fetch(`${API_BASE}api/reviews/badges`);
            const data = await response.json();
            
            const badgesGrid = document.getElementById('badges-grid');
            badgesGrid.innerHTML = data.badges.map(badge => `
                <div class="badge-item" data-badge="${badge.id}">
                    <div class="badge-label">${badge.label}</div>
                </div>
            `).join('');
            
            // Обработчики для комплиментов
            document.querySelectorAll('.badge-item').forEach(item => {
                item.addEventListener('click', () => {
                    const badge = item.dataset.badge;
                    item.classList.toggle('selected');
                    
                    if (selectedBadges.includes(badge)) {
                        selectedBadges = selectedBadges.filter(b => b !== badge);
                    } else {
                        selectedBadges.push(badge);
                    }
                });
            });
        } catch (error) {
            console.error('Error loading badges:', error);
        }
    }
    
    // Загружаем комплименты при загрузке
    loadBadges();
    
    // Обработчики для основного рейтинга
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
            document.querySelectorAll('.badge-item').forEach(b => b.classList.remove('selected'));
            selectedBadges = [];
        });
    }
    
    if (reviewForm) {
        reviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const orderId = parseInt(document.getElementById('review-order-id').value);
            const revieweeTelegramId = parseInt(document.getElementById('review-reviewee-telegram-id').value);
            const rating = parseInt(document.getElementById('rating-value').value);
            const comment = document.getElementById('review-comment').value;
            
            if (!rating) {
                showError('Пожалуйста, выберите общую оценку');
                return;
            }
            
            try {
                await submitReview(orderId, revieweeTelegramId, rating, comment, selectedBadges);
                reviewModal.classList.add('hidden');
                reviewForm.reset();
                ratingStars.forEach(s => s.classList.remove('active'));
                document.querySelectorAll('.badge-item').forEach(b => b.classList.remove('selected'));
                selectedBadges = [];
                showSuccess('Спасибо за ваш отзыв!');
                refreshOrders();
            } catch (error) {
                showError(error.message || 'Ошибка отправки отзыва');
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
        console.log('Fetching bids for order:', orderId);
        const bids = await fetchOrderBids(orderId);
        console.log('Bids received:', bids);
        
        const modal = document.getElementById('view-bids-modal');
        const bidsList = document.getElementById('bids-list');
        
        if (!bids || bids.length === 0) {
            bidsList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-title">Нет предложений</div>
                </div>
            `;
        } else {
            bidsList.innerHTML = bids.map((bid, index) => `
                <div class="bid-card">
                    <div class="bid-header">
                        <div class="bid-driver">
                            ${index + 1}. ${bid.name || 'Водитель'}
                            <div class="driver-rating">
                                ${renderStars(bid.driver_rating || 0)} ${(bid.driver_rating || 0).toFixed(1)} (${bid.review_count || 0})
                            </div>
                        </div>
                        <div class="bid-price">${formatPrice(bid.price)}</div>
                    </div>
                    <div class="bid-meta">
                        <span> ${formatDate(bid.created_at)}</span>
                    </div>
                    <div class="bid-actions">
                        <button class="btn btn-secondary" onclick="openProfile(${bid.driver_id})" style="flex: 1;">
                            Профиль
                        </button>
                        <button class="btn btn-primary" onclick="selectWinner(${orderId}, ${bid.id})" style="flex: 2;">
                            Выбрать
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
        modal.classList.remove('hidden');
    } catch (error) {
        console.error('Error in viewOrderBids:', error);
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
        console.log('Fetching bids for order (select mode):', orderId);
        const bids = await fetchOrderBids(orderId);
        console.log('Bids received (select mode):', bids);
        
        const modal = document.getElementById('view-bids-modal');
        const bidsList = document.getElementById('bids-list');
        
        if (!bids || bids.length === 0) {
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
                        <div class="bid-driver">
                            ${index + 1}. ${bid.name || 'Водитель'}
                            <div class="driver-rating">
                                ${renderStars(bid.driver_rating || 0)} ${(bid.driver_rating || 0).toFixed(1)} (${bid.review_count || 0})
                            </div>
                        </div>
                        <div class="bid-price">${formatPrice(bid.price)}</div>
                    </div>
                    <div class="bid-contact">
                        ${bid.phone_number || 'Телефон не указан'}
                    </div>
                    <div class="bid-meta">
                        <span>${formatDate(bid.created_at)}</span>
                    </div>
                    <div class="bid-actions">
                        <button class="btn btn-secondary" onclick="openProfile(${bid.driver_id})" style="flex: 1;">
                            Профиль
                        </button>
                        <button class="btn btn-success" onclick="selectWinner(${orderId}, ${bid.id})" style="flex: 2;">
                            Выбрать
                        </button>
                    </div>
                </div>
            `).join('');
        }
        
        // Обновляем заголовок модального окна
        const modalHeader = modal.querySelector('.modal-header h2');
        if (modalHeader && bids && bids.length > 0) {
            modalHeader.textContent = `Выбор исполнителя (${bids.length} предложений)`;
        }
        
        modal.classList.remove('hidden');
    } catch (error) {
        console.error('Error in viewAndSelectBids:', error);
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
            return 'Предложений не поступило';
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
    
    try {
        // Если дата не содержит информации о временной зоне, добавляем UTC
        let dateToFormat = dateString;
        if (!dateString.includes('Z') && !dateString.includes('+') && !dateString.includes('T')) {
            // Формат SQLite: YYYY-MM-DD HH:MM:SS - добавляем 'Z' чтобы указать что это UTC
            dateToFormat = dateString.replace(' ', 'T') + 'Z';
        } else if (dateString.includes(' ') && !dateString.includes('Z')) {
            // Если есть пробел вместо T, но нет Z
            dateToFormat = dateString.replace(' ', 'T') + 'Z';
        }
        
        const date = new Date(dateToFormat);
        if (isNaN(date.getTime())) return 'Неверная дата';
        
        // Форматируем в локальное время пользователя
        return date.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        console.error('Ошибка форматирования даты:', e);
        return dateString;
    }
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
window.openReviewModal = function(orderId, userId, userName, userTelegramId) {
    console.log('Opening review modal:', { orderId, userId, userName, userTelegramId });
    const modal = document.getElementById('review-modal');
    if (!modal) {
        console.error('Review modal not found!');
        return;
    }
    document.getElementById('review-order-id').value = orderId;
    document.getElementById('review-user-id').value = userId;
    document.getElementById('review-reviewee-telegram-id').value = userTelegramId || userId;
    document.getElementById('review-user-name').textContent = userName;
    
    // Сбросить все оценки
    document.querySelectorAll('.rating-star').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.badge-item').forEach(b => b.classList.remove('selected'));
    document.getElementById('rating-value').value = '';
    document.getElementById('review-comment').value = '';
    
    modal.classList.remove('hidden');
};

// === ЗАГРУЗКА ФОТО ===
let selectedPhotos = [];

window.openPhotoUploadModal = function(orderId, photoType) {
    const modal = document.getElementById('photo-upload-modal');
    const title = document.getElementById('photo-upload-title');
    
    document.getElementById('photo-upload-order-id').value = orderId;
    document.getElementById('photo-upload-type').value = photoType;
    
    title.textContent = photoType === 'loading' ? '📦 Загрузить фото загрузки' : '📤 Загрузить фото выгрузки';
    
    // Сброс выбранных фото
    selectedPhotos = [];
    document.getElementById('photo-preview-container').innerHTML = '';
    document.getElementById('submit-photos').disabled = true;
    
    modal.classList.remove('hidden');
};

// Обработчик выбора файлов
document.addEventListener('DOMContentLoaded', function() {
    const photoInput = document.getElementById('photo-input');
    const previewContainer = document.getElementById('photo-preview-container');
    const submitBtn = document.getElementById('submit-photos');
    
    if (photoInput) {
        photoInput.addEventListener('change', function(e) {
            const files = Array.from(e.target.files);
            
            // Ограничение на 5 фото
            if (selectedPhotos.length + files.length > 5) {
                alert('Можно загрузить максимум 5 фотографий');
                return;
            }
            
            files.forEach(file => {
                if (file.type.startsWith('image/')) {
                    selectedPhotos.push(file);
                    
                    // Создаем превью
                    const reader = new FileReader();
                    reader.onload = function(event) {
                        const preview = document.createElement('div');
                        preview.className = 'photo-preview-item';
                        preview.innerHTML = `
                            <img src="${event.target.result}" alt="Preview">
                            <button class="photo-remove-btn" onclick="removePhoto(${selectedPhotos.length - 1})">&times;</button>
                        `;
                        previewContainer.appendChild(preview);
                    };
                    reader.readAsDataURL(file);
                }
            });
            
            // Активируем кнопку загрузки
            submitBtn.disabled = selectedPhotos.length === 0;
            
            // Очищаем input для возможности выбрать те же файлы снова
            photoInput.value = '';
        });
    }
    
    // Кнопка загрузки
    if (submitBtn) {
        submitBtn.addEventListener('click', async function() {
            const orderId = document.getElementById('photo-upload-order-id').value;
            const photoType = document.getElementById('photo-upload-type').value;
            
            if (selectedPhotos.length === 0) {
                alert('Выберите хотя бы одно фото');
                return;
            }
            
            // Показываем индикатор загрузки
            submitBtn.disabled = true;
            submitBtn.textContent = 'Загрузка...';
            
            try {
                const telegram_id = window.Telegram.WebApp.initDataUnsafe.user?.id;
                
                console.log('=== PHOTO UPLOAD DEBUG ===');
                console.log('Telegram WebApp data:', window.Telegram.WebApp.initDataUnsafe);
                console.log('User ID:', telegram_id);
                console.log('User ID type:', typeof telegram_id);
                
                if (!telegram_id) {
                    alert('Ошибка: не удалось получить ID пользователя. Данные: ' + JSON.stringify(window.Telegram.WebApp.initDataUnsafe));
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Загрузить';
                    return;
                }
                
                console.log('Uploading photos:', {orderId, photoType, telegram_id, filesCount: selectedPhotos.length});
                
                const formData = new FormData();
                selectedPhotos.forEach(photo => {
                    formData.append('photos', photo);
                });
                
                // Добавляем telegram_id в FormData как запасной вариант
                const telegramIdStr = telegram_id.toString();
                formData.append('telegram_id', telegramIdStr);
                console.log('FormData telegram_id:', telegramIdStr);
                
                const headers = {
                    'telegram-id': telegramIdStr
                };
                console.log('Request headers:', headers);
                console.log('Request URL:', `${API_BASE}api/orders/${orderId}/photos/${photoType}`);
                
                const response = await fetch(`${API_BASE}api/orders/${orderId}/photos/${photoType}`, {
                    method: 'POST',
                    headers: headers,
                    body: formData
                });
                
                console.log('Upload response:', response.status, response.statusText);
                console.log('Response headers:', Object.fromEntries(response.headers.entries()));
                
                if (!response.ok) {
                    // Читаем тело ответа только один раз
                    const contentType = response.headers.get('content-type');
                    let errorMsg = 'Ошибка загрузки';
                    
                    try {
                        if (contentType && contentType.includes('application/json')) {
                            const error = await response.json();
                            errorMsg = error.error || errorMsg;
                            console.error('Server error:', error);
                        } else {
                            const text = await response.text();
                            console.error('Response text:', text);
                            errorMsg = text || errorMsg;
                        }
                    } catch (e) {
                        console.error('Error parsing response:', e);
                    }
                    throw new Error(errorMsg);
                }
                
                // Парсим успешный ответ
                const result = await response.json();
                console.log('Upload success:', result);
                
                // Успешно загружено
                alert('Фотографии успешно загружены!');
                document.getElementById('photo-upload-modal').classList.add('hidden');
                
                // Перезагружаем данные текущей вкладки
                await loadTabData(currentTab, true);
                
            } catch (error) {
                console.error('Error uploading photos:', error);
                alert('Ошибка загрузки: ' + error.message);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Загрузить';
            }
        });
    }
    
    // Кнопка отмены
    const cancelBtn = document.getElementById('cancel-photo-upload');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', function() {
            document.getElementById('photo-upload-modal').classList.add('hidden');
        });
    }
});

window.removePhoto = function(index) {
    selectedPhotos.splice(index, 1);
    
    // Перерисовываем превью
    const previewContainer = document.getElementById('photo-preview-container');
    previewContainer.innerHTML = '';
    
    selectedPhotos.forEach((file, idx) => {
        const reader = new FileReader();
        reader.onload = function(event) {
            const preview = document.createElement('div');
            preview.className = 'photo-preview-item';
            preview.innerHTML = `
                <img src="${event.target.result}" alt="Preview">
                <button class="photo-remove-btn" onclick="removePhoto(${idx})">&times;</button>
            `;
            previewContainer.appendChild(preview);
        };
        reader.readAsDataURL(file);
    });
    
    // Обновляем состояние кнопки
    document.getElementById('submit-photos').disabled = selectedPhotos.length === 0;
};

// ==================== CHAT FUNCTIONS ====================

let currentChatOrderId = null;
let chatRefreshInterval = null;

// Открыть чат для заказа
async function openChat(orderId, recipientName, recipientRole) {
    currentChatOrderId = orderId;
    
    const modal = document.getElementById('chat-modal');
    const title = document.getElementById('chat-modal-title');
    
    // Устанавливаем заголовок
    const roleText = recipientRole === 'driver' ? 'водителем' : 'заказчиком';
    title.textContent = `Чат с ${roleText}`;
    
    // Показываем модальное окно
    modal.classList.remove('hidden');
    
    // Загружаем сообщения
    await loadChatMessages(orderId);
    
    // Отмечаем сообщения как прочитанные
    await markMessagesRead(orderId);
    
    // Настраиваем автообновление каждые 3 секунды
    if (chatRefreshInterval) {
        clearInterval(chatRefreshInterval);
    }
    chatRefreshInterval = setInterval(() => {
        loadChatMessages(orderId);
    }, 3000);
    
    // Фокус на поле ввода
    setTimeout(() => {
        document.getElementById('chat-message-input').focus();
    }, 300);
}

// Закрыть чат
function closeChat() {
    const modal = document.getElementById('chat-modal');
    modal.classList.add('hidden');
    
    if (chatRefreshInterval) {
        clearInterval(chatRefreshInterval);
        chatRefreshInterval = null;
    }
    
    currentChatOrderId = null;
    
    // Обновляем список заказов чтобы обновить счетчики
    loadTabData(currentTab, false);
}

// Загрузить сообщения чата
async function loadChatMessages(orderId, scrollToBottom = true) {
    try {
        const telegram_id = window.Telegram.WebApp.initDataUnsafe.user?.id;
        
        const response = await fetch(`${API_BASE}api/orders/${orderId}/messages?telegram_id=${telegram_id}`);
        
        if (!response.ok) {
            console.error('Failed to load chat messages');
            return;
        }
        
        const data = await response.json();
        const container = document.getElementById('chat-messages-container');
        
        if (!data.messages || data.messages.length === 0) {
            container.innerHTML = '<div class="chat-empty-state">Сообщений пока нет.<br>Начните диалог!</div>';
            return;
        }
        
        container.innerHTML = data.messages.map(msg => `
            <div class="chat-message ${msg.is_mine ? 'mine' : 'theirs'}">
                <div class="chat-message-bubble">
                    ${escapeHtml(msg.message_text)}
                </div>
                <div class="chat-message-time">
                    ${formatDateTime(msg.created_at)}
                </div>
            </div>
        `).join('');
        
        // Прокручиваем вниз
        if (scrollToBottom) {
            container.scrollTop = container.scrollHeight;
        }
        
    } catch (error) {
        console.error('Error loading chat messages:', error);
    }
}

// Отправить сообщение
async function sendChatMessage(event) {
    event.preventDefault();
    
    const textarea = document.getElementById('chat-message-input');
    const messageText = textarea.value.trim();
    
    if (!messageText || !currentChatOrderId) {
        return;
    }
    
    try {
        const telegram_id = window.Telegram.WebApp.initDataUnsafe.user?.id;
        
        const response = await fetch(`${API_BASE}api/orders/${currentChatOrderId}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                telegram_id: telegram_id,
                message_text: messageText
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            alert(error.error || 'Ошибка отправки сообщения');
            return;
        }
        
        // Очищаем поле ввода
        textarea.value = '';
        textarea.style.height = 'auto';
        
        // Перезагружаем сообщения
        await loadChatMessages(currentChatOrderId);
        
        // Фокус обратно на поле
        textarea.focus();
        
    } catch (error) {
        console.error('Error sending message:', error);
        alert('Ошибка отправки сообщения');
    }
}

// Отметить сообщения как прочитанные
async function markMessagesRead(orderId) {
    try {
        const telegram_id = window.Telegram.WebApp.initDataUnsafe.user?.id;
        
        await fetch(`${API_BASE}api/orders/${orderId}/messages/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                telegram_id: telegram_id
            })
        });
        
    } catch (error) {
        console.error('Error marking messages as read:', error);
    }
}

// Получить счетчики непрочитанных сообщений
async function getUnreadCounts() {
    try {
        const telegram_id = window.Telegram.WebApp.initDataUnsafe.user?.id;
        
        const response = await fetch(`${API_BASE}api/orders/unread-messages-count?telegram_id=${telegram_id}`);
        
        if (!response.ok) {
            return {};
        }
        
        const data = await response.json();
        return data.unread_by_order || {};
        
    } catch (error) {
        console.error('Error getting unread counts:', error);
        return {};
    }
}

// Вспомогательная функция для экранирования HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Форматирование даты и времени для сообщений
function formatDateTime(dateStr) {
    if (!dateStr) return '';
    
    const date = new Date(dateStr);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const messageDate = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    
    const timeStr = date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    
    if (messageDate.getTime() === today.getTime()) {
        return timeStr;
    } else if (messageDate.getTime() === today.getTime() - 86400000) {
        return `Вчера ${timeStr}`;
    } else {
        return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' }) + ' ' + timeStr;
    }
}

// Event listeners для чата
document.getElementById('close-chat')?.addEventListener('click', closeChat);
document.getElementById('chat-modal')?.querySelector('.modal-overlay')?.addEventListener('click', closeChat);
document.getElementById('chat-message-form')?.addEventListener('submit', sendChatMessage);

// Auto-resize textarea
document.getElementById('chat-message-input')?.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});


