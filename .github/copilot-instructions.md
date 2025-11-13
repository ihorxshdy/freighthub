# FreightHub - AI Coding Assistant Instructions

## Architecture Overview

FreightHub is a Telegram Mini App for freight transportation matching customers with drivers through an auction system. The system consists of **three primary services** running in Docker containers:

1. **telegram-bot/** - aiogram 3.22 bot handling user registration, notifications, and webhook server (port 8080)
2. **webapp/** - Flask 3.1 web app serving the Mini App UI and REST API (port 5000)
3. **auction-checker** - Background worker monitoring auction expiration (runs `webapp/auction_checker.py`)

### Critical Shared Database Pattern
All services share a **single SQLite database** via Docker volume (`db-data:/app/data`). The database path is `/app/data/delivery.db` in production containers. WAL mode is enabled for concurrent access with 30s timeout to prevent locking issues.

## Data Flow & Service Communication

### Order Creation Flow
1. Customer creates order via webapp → Flask API creates order in DB with `status='active'` and `expires_at` (2 minutes)
2. webapp calls `webhook_client.notify_new_order()` → sends HTTP POST to telegram-bot webhook
3. telegram-bot receives webhook → queries DB for drivers with matching `truck_type` via `driver_vehicles` table
4. Bot sends notification to eligible drivers with inline keyboard to make bid

### Auction Completion Flow
1. `auction_checker.py` runs every 30s checking for `status='active'` orders where `datetime(expires_at) <= datetime('now')`
2. **If bids exist**: Changes status to `auction_completed` → customer manually selects winner via webapp
3. **If no bids**: Changes status to `no_offers` → notifies customer via webhook
4. Manual selection: Customer clicks bid in webapp → triggers `/api/orders/<id>/select-winner` → sets `winner_driver_id`, `winning_price`, changes status to `in_progress`

### Photo Stage Tracking
Orders track delivery progress via photos:
- `loading_confirmed_at` - driver uploads loading photos
- `unloading_confirmed_at` - driver uploads unloading photos  
- `driver_completed_at` - set when driver confirms completion (requires unloading photos first)
- Both parties must confirm (`customer_confirmed` and `driver_confirmed`) to reach `status='closed'`

## Critical Conventions

### Truck Type System
Use `truck_config.py` constants exclusively:
- `TRUCK_CATEGORIES` - hierarchical structure for UI (manipulator → subtypes → sub_subtypes)
- `TRUCK_TYPES` - flat dict of final truck type IDs (e.g., `"manipulator_5t": "🏗️ Манипулятор 5 тонн"`)
- Drivers can have multiple vehicles via `driver_vehicles` table (many-to-many with `is_primary` flag)
- **Always query drivers by joining `driver_vehicles` table**, not deprecated `users.truck_type` field

### Database Access Patterns
- **telegram-bot**: Uses async `aiosqlite` with models in `database/models.py`
- **webapp**: Uses synchronous `sqlite3` with `get_db_connection()` helper
- Always use `conn.execute('PRAGMA journal_mode=WAL')` and `conn.execute('PRAGMA busy_timeout=30000')` for webapp connections
- Never use hardcoded user IDs - always resolve via `telegram_id` parameter

### Webhook Authentication
All inter-service communication uses `WEBHOOK_SECRET` in Authorization header:
```python
headers = {'Authorization': f'Bearer {WEBHOOK_SECRET}'}
```

### Order Status Lifecycle
```
active → auction_completed → in_progress → closed
    ↓
no_offers (if no bids)
```
- `active`: Accepting bids, auction running
- `auction_completed`: Bids ready for customer selection
- `in_progress`: Winner selected, delivery in progress
- `closed`: Both parties confirmed completion
- `no_offers`: Auction expired without bids

## Key Integration Points

### Telegram Mini App Launch
Users access webapp via Telegram WebApp button. Frontend must extract `telegram_id` from `window.Telegram.WebApp.initDataUnsafe.user.id` and pass as query param to all API calls.

### Order History Logging
Use `order_logger.py` for audit trail:
```python
from order_logger import log_order_change, ACTION_BID_ADDED
log_order_change(conn, order_id, user_id, ACTION_BID_ADDED, 
                description=f"Ставка: {price} ₽", new_value=str(price))
```
All actions logged to `order_history` table with user info, timestamps, IP addresses.

### Chat System
Real-time messaging via `chat_api.py` with webhook notifications:
- Messages stored in `chat_messages` table linked to `order_id`
- Unread count tracked per user in `last_read_message_id`
- Notifications sent via `webhook_client.send_webhook_notification()`

## Development Workflow

### Local Development
```bash
# Terminal 1: Start bot with polling
cd telegram-bot && python main.py

# Terminal 2: Start webapp
cd webapp && python app.py

# Database location (auto-shared): telegram-bot/database/delivery.db
```

### Deployment
**Automatic via GitHub Actions** (on every `git push` to main):
1. SSH to server (81.200.147.68)
2. Pull latest code to `/opt/freighthub`
3. Create `.env` from GitHub Secrets
4. Run `docker-compose up -d --build`

Manual deploy: `./deploy.sh`

### Database Migrations
Migrations in both `telegram-bot/migrations/` and `webapp/migrations/`:
- SQL files define schema changes
- Python `apply_*.py` scripts execute migrations
- **Always update both bot and webapp init_db.py files** when adding tables

### Testing Webhooks Locally
Set environment variable to point bot to local webapp:
```bash
export TELEGRAM_BOT_WEBHOOK_URL=http://localhost:5000
```

## Common Pitfalls

1. **Don't assume `users.id` == `telegram_id`** - Always join via `telegram_id` field
2. **Don't query `users.truck_type` directly** - Use `driver_vehicles` table for current multi-vehicle support
3. **Don't forget WAL mode** - Required for concurrent webapp/bot DB access
4. **Don't hardcode paths** - Use `DATABASE_PATH` from config
5. **Don't skip order logging** - Every state change must call `log_order_change()`
6. **Don't create orders without `expires_at`** - Required for auction_checker to function
7. **Bot runs polling + webhook server simultaneously** - Port 8080 webhook server handles webapp notifications even in polling mode

## File Navigation

- API routes: `webapp/app.py` (main), `webapp/reviews_api.py`, `webapp/photos_api.py`, `webapp/chat_api.py`
- Bot handlers: `telegram-bot/handlers/` (registration, orders, admin, vehicles, webhooks)
- Database models: `telegram-bot/database/models.py` (async), `webapp/init_db.py` (sync)
- Frontend: `webapp/templates/index.html`, `webapp/static/js/app.js`
- Config: `webapp/truck_config.py` (truck types), `bot/config.py` (bot settings)
- Background jobs: `webapp/auction_checker.py` (auction expiration)

## External Dependencies

- Telegram Bot API via aiogram (long polling + webhook endpoints)
- Telegram WebApp SDK (frontend Telegram integration)
- Docker Compose for orchestration
- GitHub Actions for CI/CD (`.github/workflows/deploy.yml`)
- SQLite with WAL mode (no external DB server)
