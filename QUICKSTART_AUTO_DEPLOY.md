# ⚡ Быстрая настройка автоматического деплоя

## Шаг 1: Создайте SSH ключ (1 минута)

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/freighthub_deploy
# Нажмите Enter 3 раза (без пароля)
```

## Шаг 2: Скопируйте ключ на сервер (1 минута)

```bash
ssh-copy-id -i ~/.ssh/freighthub_deploy.pub root@81.200.147.68
# Введите пароль: tSmLE76Upf@_B.
```

## Шаг 3: Добавьте секреты на GitHub (3 минуты)

Откройте: `https://github.com/ihorxshdy/webapp/settings/secrets/actions`

Нажмите **New repository secret** и добавьте:

| Name | Value |
|------|-------|
| `SSH_PRIVATE_KEY` | Содержимое `~/.ssh/freighthub_deploy` (весь файл!) |
| `SERVER_HOST` | `81.200.147.68` |
| `SERVER_USER` | `root` |
| `BOT_TOKEN` | `8411170559:AAEDh27G2wBeJc8Acpp7Qz6FZs-dnMkeObM` |
| `WEBHOOK_SECRET` | `SlimShady313` |

### Как получить SSH_PRIVATE_KEY:

```bash
cat ~/.ssh/freighthub_deploy
```

Скопируйте ВСЁ от `-----BEGIN RSA PRIVATE KEY-----` до `-----END RSA PRIVATE KEY-----`

## Шаг 4: Закоммитьте изменения (30 секунд)

```bash
cd /Users/igordvoretskii/Documents/deliveryapp
git add .
git commit -m "Add GitHub Actions auto-deploy"
git push
```

## ✅ Готово!

Теперь при каждом `git push` в `main` - сервер автоматически обновится!

### Проверка:

1. Откройте: `https://github.com/ihorxshdy/webapp/actions`
2. Увидите запущенный workflow "Deploy to Server"
3. Дождитесь зеленой галочки ✅
4. Проверьте: http://81.200.147.68

---

## 🎯 Использование

**Внесли изменения в код?**

```bash
git add .
git commit -m "Описание изменений"
git push  # 🚀 Автоматический деплой!
```

**Нужно запустить деплой вручную?**

1. Откройте: `https://github.com/ihorxshdy/webapp/actions`
2. Выберите "Deploy to Server"
3. Нажмите "Run workflow" → "Run workflow"

**Смотреть логи деплоя:**

- На GitHub: `https://github.com/ihorxshdy/webapp/actions`
- На сервере: `ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose logs -f'`

---

## 🔧 Troubleshooting

**Ошибка: Permission denied (publickey)**
```bash
# Проверьте, что ключ скопирован на сервер
ssh -i ~/.ssh/freighthub_deploy root@81.200.147.68
```

**Workflow не запускается**
→ Проверьте, что файл `.github/workflows/deploy.yml` закоммичен в репозиторий

**Секреты не работают**
→ Проверьте имена секретов (с большой буквы, с подчеркиваниями)

---

📖 **Подробная инструкция:** [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)
