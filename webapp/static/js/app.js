// Telegram Web App API
const tg = window.Telegram?.WebApp;

if (tg) {
    try {
        tg.expand();
        tg.ready();
        // Скрываем нижнюю кнопку "Приложение"
        tg.MainButton.hide();
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
    const response = await fetchWithTimeout(`${API_BASE}api/orders/${orderId}/bids`, {}, 10000);
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
    
    // Обновляем информацию о пользователе
    document.getElementById('user-name').textContent = currentUser.name || 'Пользователь';
    const roleText = currentUser.role === 'customer' ? 'Заказчик' : 'Водитель';
    const phoneText = currentUser.phone_number ? ` • ${currentUser.phone_number}` : '';
    // Для водителей добавляем тип машины
    const truckText = (currentUser.role === 'driver' && currentUser.truck_type) ? ` • ${getTruckTypeName(currentUser.truck_type)}` : '';
    document.getElementById('user-role').textContent = roleText + phoneText + truckText;
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
        // Используем первую букву имени как fallback
        const initial = (currentUser.name || 'П').charAt(0).toUpperCase();
        avatar.textContent = initial;
    }
    
    // Инициализируем вкладки
    initTabs();
    
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

function initTabs() {
    const tabsNav = document.getElementById('tabs-nav');
    const tabContent = document.getElementById('tab-content');
    
    tabsNav.innerHTML = '';
    tabContent.innerHTML = '';
    
    let tabs = [];
    
    if (currentUser.role === 'customer') {
        tabs = [
            { id: 'searching', label: 'Поиск исполнителей', icon: '🔍' },
            { id: 'created', label: 'Созданные', icon: '📝' },
            { id: 'in_progress', label: 'В процессе', icon: '🚚' },
            { id: 'closed', label: 'Закрытые', icon: '✅' }
        ];
    } else {
        tabs = [
            { id: 'open', label: 'Открытые', icon: '📋' },
            { id: 'my_bids', label: 'Мои предложения', icon: '💰' },
            { id: 'won', label: 'Выигранные', icon: '🏆' },
            { id: 'in_progress', label: 'В процессе', icon: '🚚' },
            { id: 'closed', label: 'Закрытые', icon: '📁' }
        ];
    }
    
    tabs.forEach((tab, index) => {
        // Создаем кнопку вкладки
        const tabBtn = document.createElement('button');
        tabBtn.className = 'tab' + (index === 0 ? ' active' : '');
        tabBtn.dataset.tab = tab.id;
        tabBtn.innerHTML = `${tab.icon} ${tab.label} <span class="tab-badge" id="badge-${tab.id}">0</span>`;
        tabBtn.addEventListener('click', () => switchTab(tab.id));
        tabsNav.appendChild(tabBtn);
        
        // Создаем контент вкладки
        const tabPane = document.createElement('div');
        tabPane.className = 'tab-pane' + (index === 0 ? ' active' : '');
        tabPane.id = `tab-${tab.id}`;
        tabContent.appendChild(tabPane);
    });
    
    // Загружаем данные для первой вкладки
    currentTab = tabs[0].id;
    loadTabData(currentTab);
}

async function switchTab(tabId) {
    // Обновляем активную вкладку
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
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
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">Ошибка загрузки</div>
                <p style="color: #666; margin: 10px 0;">${error.message || 'Проверьте интернет-соединение'}</p>
                <button onclick="refreshOrders()" style="margin-top: 15px; padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 8px; cursor: pointer;">
                    🔄 Повторить
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

function renderCustomerOrders(orders, container, tabId) {
    if (!orders || orders.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📦</div>
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
                <div class="order-status status-${tabId}">${getStatusLabel(tabId)}</div>
            </div>
            
            <div class="order-route">
                <div class="route-point">
                    <span class="route-icon">📍</span>
                    <span>${order.pickup_address}</span>
                </div>
                <div class="route-point">
                    <span class="route-icon">🎯</span>
                    <span>${order.delivery_address}</span>
                </div>
            </div>
            
            <div class="order-description">${order.cargo_description}</div>
            
            <div class="order-meta">
                <span>🚛 ${getTruckTypeName(order.truck_type)}</span>
                <span>📅 ${formatDate(order.created_at)}</span>
                ${order.delivery_date ? `<span>📦 Доставка: ${order.delivery_date}</span>` : ''}
                ${order.max_price ? `<span>💰 Желаемая цена: ${formatPrice(order.max_price)}</span>` : ''}
            </div>
            
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
            ${tabId === 'in_progress' ? `
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <button class="btn btn-small btn-success" onclick="confirmOrderCompletion(${order.id})" style="flex: 1;">
                        Подтвердить выполнение
                    </button>
                    <button class="btn btn-small btn-danger" onclick="cancelOrder(${order.id})" style="flex: 1;">
                        Отменить заказ
                    </button>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function renderDriverOrders(orders, container, tabId) {
    if (!orders || orders.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🚛</div>
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
                <div class="order-status status-${tabId}">${getStatusLabel(tabId)}</div>
            </div>
            
            <div class="order-route">
                <div class="route-point">
                    <span class="route-icon">📍</span>
                    <span>${order.pickup_address}</span>
                </div>
                <div class="route-point">
                    <span class="route-icon">🎯</span>
                    <span>${order.delivery_address}</span>
                </div>
            </div>
            
            <div class="order-description">${order.cargo_description}</div>
            
            <div class="order-meta">
                <span>🚛 ${getTruckTypeName(order.truck_type)}</span>
                <span>📅 ${formatDate(order.created_at)}</span>
                ${order.delivery_date ? `<span>📦 Доставка: ${order.delivery_date}</span>` : ''}
                ${order.max_price ? `<span>💰 Желаемая цена: ${formatPrice(order.max_price)}</span>` : ''}
                ${order.total_bids ? `<span>� ${order.total_bids} предложений</span>` : ''}
            </div>
            
            <div class="order-footer">
                ${order.my_bid_price ? `
                    <div class="my-bid-price">Моя ставка: ${formatPrice(order.my_bid_price)}</div>
                ` : ''}
                ${tabId === 'open' ? `
                    <button class="btn btn-small btn-primary" onclick="openBidModal(${order.id}, '${order.pickup_address}', '${order.delivery_address}', '${order.cargo_description}')">
                        Сделать предложение
                    </button>
                ` : ''}
                ${tabId === 'in_progress' ? `
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <button class="btn btn-small btn-success" onclick="confirmOrderCompletion(${order.id})" style="flex: 1;">
                            Подтвердить выполнение
                        </button>
                        <button class="btn btn-small btn-danger" onclick="cancelOrder(${order.id})" style="flex: 1;">
                            Отменить заказ
                        </button>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
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
                    <div class="empty-icon">💰</div>
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
    if (!confirm('Вы уверены, что хотите отменить заказ?')) {
        return;
    }
    
    try {
        const response = await fetchWithTimeout(`${API_BASE}api/orders/${orderId}/cancel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                telegram_id: currentUser.telegram_id
            })
        }, 15000);
        
        if (!response.ok) {
            throw new Error('Ошибка отмены заказа');
        }
        
        showSuccess('Заказ отменен');
        refreshOrders();
    } catch (error) {
        showError('Ошибка отмены заказа');
    }
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
        'open': 'Открыта',
        'my_bids': 'Предложено',
        'won': 'Выиграна',
        'in_progress': 'В процессе',
        'closed': 'Закрыта'
    };
    return labels[status] || status;
}

function getEmptyMessage(tabId) {
    const messages = {
        'open': 'Новые заявки появятся здесь',
        'my_bids': 'Вы еще не делали предложений',
        'won': 'Вы еще не выиграли ни одной заявки',
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

