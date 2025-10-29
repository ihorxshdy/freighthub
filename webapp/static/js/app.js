// Telegram Web App API
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.expand();
}

// Глобальные переменные
let currentUser = null;
let currentTab = null;
let currentOrderForBid = null;
let truckTypesMap = {}; // Маппинг ID -> название типа машины

// Режим тестирования (для браузера)
const TEST_MODE = !tg || !tg.initDataUnsafe?.user;

// Тестовый пользователь для режима разработки
const TEST_USER = {
    id: 123456789,
    first_name: 'Тестовый',
    last_name: 'Пользователь',
    username: 'test_user'
};

// Инициализация приложения
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Применяем тему Telegram
        applyTelegramTheme();
        
        // Получаем данные пользователя из Telegram или используем тестовые
        const telegramUser = TEST_MODE ? TEST_USER : tg.initDataUnsafe.user;
        
        console.log('Режим работы:', TEST_MODE ? 'ТЕСТОВЫЙ (браузер)' : 'TELEGRAM');
        console.log('Пользователь Telegram:', telegramUser);
        
        // Всегда проверяем актуальные данные с сервера
        const user = await fetchUser(telegramUser.id);
        
        if (user) {
            currentUser = user;
            // Сохраняем в localStorage для быстрого доступа
            localStorage.setItem('currentUser', JSON.stringify(user));
            console.log('Пользователь загружен:', user);
            showMainScreen();
        } else {
            // Проверяем кэш (на случай если сервер недоступен)
            const cachedUser = localStorage.getItem('currentUser');
            if (cachedUser) {
                const parsedUser = JSON.parse(cachedUser);
                // Проверяем что это тот же пользователь
                if (parsedUser.telegram_id == telegramUser.id) {
                    currentUser = parsedUser;
                    console.log('Пользователь загружен из кэша:', parsedUser);
                    showMainScreen();
                    return;
                }
            }
            // Показываем регистрацию только если пользователя точно нет
            showRegistrationScreen(telegramUser);
        }
    } catch (error) {
        console.error('Ошибка инициализации:', error);
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
async function fetchUser(telegramId) {
    const response = await fetch(`/api/user?telegram_id=${telegramId}`);
    if (response.ok) {
        return await response.json();
    }
    return null;
}

async function registerUser(userData) {
    const response = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
    });
    
    if (!response.ok) {
        throw new Error('Ошибка регистрации');
    }
    
    return await response.json();
}

async function fetchTruckTypes() {
    const response = await fetch('/api/truck-types');
    return await response.json();
}

async function fetchCustomerOrders(telegramId) {
    const response = await fetch(`/api/customer/orders?telegram_id=${telegramId}`);
    return await response.json();
}

async function fetchDriverOrders(telegramId) {
    const response = await fetch(`/api/driver/orders?telegram_id=${telegramId}`);
    return await response.json();
}

async function createOrder(orderData) {
    const response = await fetch(`/api/orders?telegram_id=${currentUser.telegram_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderData)
    });
    
    if (!response.ok) {
        throw new Error('Ошибка создания заявки');
    }
    
    return await response.json();
}

async function createBid(bidData) {
    const response = await fetch(`/api/bids?telegram_id=${currentUser.telegram_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bidData)
    });
    
    if (!response.ok) {
        throw new Error('Ошибка создания предложения');
    }
    
    return await response.json();
}

async function fetchOrderBids(orderId) {
    const response = await fetch(`/api/orders/${orderId}/bids`);
    return await response.json();
}

// === НАВИГАЦИЯ ===
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    document.getElementById(screenId).classList.remove('hidden');
}

function showRegistrationScreen(telegramUser) {
    showScreen('registration-screen');
    
    // Обработчики выбора роли
    document.querySelectorAll('.role-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const role = btn.dataset.role;
            
            try {
                showScreen('loading-screen');
                
                const userData = {
                    telegram_id: telegramUser.id,
                    username: telegramUser.username || '',
                    first_name: telegramUser.first_name || '',
                    last_name: telegramUser.last_name || '',
                    role: role
                };
                
                await registerUser(userData);
                const user = await fetchUser(telegramUser.id);
                currentUser = user;
                
                // Сохраняем в localStorage
                localStorage.setItem('currentUser', JSON.stringify(user));
                console.log('Регистрация успешна, пользователь сохранен:', user);
                
                showMainScreen();
            } catch (error) {
                console.error('Ошибка регистрации:', error);
                showError('Ошибка регистрации');
                showRegistrationScreen(telegramUser);
            }
        });
    });
}

async function showMainScreen() {
    showScreen('main-screen');
    
    // Обновляем информацию о пользователе
    document.getElementById('user-name').textContent = `${currentUser.first_name} ${currentUser.last_name || ''}`.trim();
    const roleText = currentUser.role === 'customer' ? 'Заказчик' : 'Водитель';
    const phoneText = currentUser.phone_number ? ` • ${currentUser.phone_number}` : '';
    document.getElementById('user-role').textContent = roleText + phoneText;
    document.body.className = `role-${currentUser.role}`;
    
    // Инициализируем вкладки
    initTabs();
    
    // Загружаем типы грузовиков для форм
    await loadTruckTypes();
    
    // Инициализируем модальные окна
    initModals();
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
            { id: 'completed', label: 'Завершенные', icon: '✅' }
        ];
    } else {
        tabs = [
            { id: 'open', label: 'Открытые', icon: '📋' },
            { id: 'my_bids', label: 'Мои предложения', icon: '💰' },
            { id: 'won', label: 'Выигранные', icon: '🏆' },
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

async function loadTabData(tabId) {
    const tabPane = document.getElementById(`tab-${tabId}`);
    tabPane.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';
    
    try {
        if (currentUser.role === 'customer') {
            const orders = await fetchCustomerOrders(currentUser.telegram_id);
            renderCustomerOrders(orders[tabId], tabPane, tabId);
            updateBadges(orders);
        } else {
            const orders = await fetchDriverOrders(currentUser.telegram_id);
            renderDriverOrders(orders[tabId], tabPane, tabId);
            updateBadges(orders);
        }
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
        tabPane.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><div class="empty-title">Ошибка загрузки</div></div>';
    }
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
                    <span>${order.pickup_location}</span>
                </div>
                <div class="route-point">
                    <span class="route-icon">🎯</span>
                    <span>${order.delivery_location}</span>
                </div>
            </div>
            
            <div class="order-description">${order.description}</div>
            
            <div class="order-meta">
                <span>🚛 ${getTruckTypeName(order.truck_type)}</span>
                <span>📅 ${formatDate(order.created_at)}</span>
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
                    <span>${order.pickup_location}</span>
                </div>
                <div class="route-point">
                    <span class="route-icon">🎯</span>
                    <span>${order.delivery_location}</span>
                </div>
            </div>
            
            <div class="order-description">${order.description}</div>
            
            <div class="order-meta">
                <span>🚛 ${getTruckTypeName(order.truck_type)}</span>
                <span>📅 ${formatDate(order.created_at)}</span>
                ${order.total_bids ? `<span>💰 ${order.total_bids} предложений</span>` : ''}
            </div>
            
            <div class="order-footer">
                ${order.my_bid_price ? `
                    <div class="my-bid-price">Моя ставка: ${formatPrice(order.my_bid_price)}</div>
                ` : ''}
                ${tabId === 'open' ? `
                    <button class="btn btn-small btn-primary" onclick="openBidModal(${order.id}, '${order.pickup_location}', '${order.delivery_location}', '${order.description}')">
                        Сделать предложение
                    </button>
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
                price: document.getElementById('price').value || null
            };
            
            try {
                await createOrder(orderData);
                createOrderModal.classList.add('hidden');
                createOrderForm.reset();
                showSuccess('Заявка создана успешно!');
                loadTabData(currentTab);
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
                loadTabData(currentTab);
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
            optgroup.label = category.category;
            
            category.types.forEach(type => {
                // Сохраняем в map для использования в getTruckTypeName
                truckTypesMap[type.id] = type.full_name || type.name;
                
                // Создаем option
                const option = document.createElement('option');
                option.value = type.id;
                option.textContent = `${type.emoji} ${type.name}`;
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
                        <div class="bid-driver">${index + 1}. ${bid.first_name} ${bid.last_name || ''}</div>
                        <div class="bid-price">${formatPrice(bid.price)}</div>
                    </div>
                    <div class="bid-time">📅 ${formatDate(bid.created_at)}</div>
                </div>
            `).join('');
        }
        
        modal.classList.remove('hidden');
    } catch (error) {
        showError('Ошибка загрузки предложений');
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
