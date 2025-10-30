# ✅ Быстрый чеклист настройки

## Текущий статус системы

### ✅ Завершено:
- [x] Docker контейнеры запущены на сервере
- [x] Nginx настроен и работает
- [x] WebApp доступно по HTTP: http://freight-hub.ru/tgbotfiles/freighthub/
- [x] Бот перезапущен с обновленным URL
- [x] Порты корректно настроены (webapp: 5000, bot: 8080)

### ⏳ Осталось сделать:

## Шаг 1: Включите SSL в Cloudflare (2 минуты)

1. Откройте: https://dash.cloudflare.com
2. Выберите домен `freight-hub.ru`
3. **SSL/TLS** → **Overview** → Выберите **Flexible**
4. **SSL/TLS** → **Edge Certificates**:
   - ✅ Always Use HTTPS: **On**
   - ✅ Automatic HTTPS Rewrites: **On**
5. **DNS** → **Records** → Убедитесь, что у записи `@` оранжевое облако 🟠 (Proxied)

## Шаг 2: Подождите 1-2 минуты

SSL сертификат активируется автоматически.

## Шаг 3: Проверьте работу

Откройте в браузере:
- ✅ https://freight-hub.ru/tgbotfiles/freighthub/ (должен открыться WebApp)
- ✅ https://t.me/freighthub_bot (откройте бота и нажмите "Приложение")

## Готово! 🎉

Если всё работает:
- ✅ WebApp открывается по HTTPS
- ✅ В Telegram кнопка "Приложение" работает
- ✅ Нет ошибки "Only HTTPS links are allowed"

---

## Если что-то не работает:

### Проблема: SSL не активировался
**Решение:** Подождите ещё 5 минут, очистите кеш браузера (Cmd+Shift+R)

### Проблема: Кнопка в боте не работает
**Решение:** 
```bash
ssh -i ~/.ssh/freighthub_deploy root@81.200.147.68 'cd /opt/freighthub && docker-compose restart telegram-bot'
```

### Проблема: WebApp показывает ошибку
**Решение:** Проверьте логи:
```bash
ssh -i ~/.ssh/freighthub_deploy root@81.200.147.68 'cd /opt/freighthub && docker-compose logs webapp --tail=50'
```

---

## Команды для проверки:

```bash
# Проверка контейнеров
ssh -i ~/.ssh/freighthub_deploy root@81.200.147.68 'docker ps'

# Проверка HTTPS
curl -I https://freight-hub.ru/tgbotfiles/freighthub/

# Логи бота
ssh -i ~/.ssh/freighthub_deploy root@81.200.147.68 'cd /opt/freighthub && docker-compose logs telegram-bot --tail=20'

# Логи webapp
ssh -i ~/.ssh/freighthub_deploy root@81.200.147.68 'cd /opt/freighthub && docker-compose logs webapp --tail=20'
```
