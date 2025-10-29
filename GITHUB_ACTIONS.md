# Настройка автоматического деплоя через GitHub Actions

## Подготовка SSH ключа

### 1. Создайте SSH ключ на вашем компьютере (если еще нет)

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/freighthub_deploy
```

Нажмите Enter на все вопросы (без пароля для автоматизации).

### 2. Скопируйте публичный ключ на сервер

```bash
ssh-copy-id -i ~/.ssh/freighthub_deploy.pub root@81.200.147.68
```

Или вручную:

```bash
# На вашем компьютере
cat ~/.ssh/freighthub_deploy.pub

# На сервере (через SSH)
ssh root@81.200.147.68
mkdir -p ~/.ssh
echo "ваш_публичный_ключ" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
exit
```

### 3. Проверьте подключение

```bash
ssh -i ~/.ssh/freighthub_deploy root@81.200.147.68
```

Если подключается без пароля - отлично!

## Настройка GitHub Secrets

Перейдите в ваш репозиторий на GitHub:
**Settings → Secrets and variables → Actions → New repository secret**

Создайте следующие секреты:

### SSH_PRIVATE_KEY

```bash
# На вашем компьютере выведите приватный ключ
cat ~/.ssh/freighthub_deploy
```

Скопируйте **ВСЁ** содержимое (включая `-----BEGIN RSA PRIVATE KEY-----` и `-----END RSA PRIVATE KEY-----`) и вставьте как значение секрета.

### SERVER_HOST

```
81.200.147.68
```

### SERVER_USER

```
root
```

### BOT_TOKEN

```
8411170559:AAEDh27G2wBeJc8Acpp7Qz6FZs-dnMkeObM
```

### WEBHOOK_SECRET

```
SlimShady313
```

## Как это работает

После настройки секретов:

1. **Автоматический деплой**: Каждый раз при `git push` в ветку `main` - GitHub автоматически обновит сервер

2. **Ручной деплой**: Можно запустить вручную на GitHub:
   - Перейдите: **Actions → Deploy to Server → Run workflow**

3. **Что происходит при деплое**:
   - ✅ Код синхронизируется с сервером
   - ✅ Создается .env файл с секретами
   - ✅ Контейнеры пересобираются
   - ✅ Сервисы перезапускаются
   - ✅ Проверяется статус

## Проверка

После первого push в main:

1. Откройте **Actions** в вашем репозитории на GitHub
2. Увидите запущенный workflow "Deploy to Server"
3. Можете смотреть логи в реальном времени
4. Когда закончится - проверьте сервер:

```bash
ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose ps'
```

## Отключение автодеплоя

Если нужно временно отключить:

Удалите или закомментируйте файл `.github/workflows/deploy.yml`

## Логи деплоя

Смотреть на GitHub:
- **Actions** → Выберите нужный workflow → Откройте "Deploy to server"

Смотреть на сервере:
```bash
ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose logs -f'
```

## Troubleshooting

### Ошибка: Permission denied (publickey)

→ Проверьте, что публичный ключ добавлен на сервер в `~/.ssh/authorized_keys`

### Ошибка: docker-compose: command not found

→ Убедитесь, что на сервере установлен Docker Compose (запустите `setup-server.sh`)

### Контейнеры не запускаются

→ Проверьте логи: `ssh root@81.200.147.68 'cd /opt/freighthub && docker-compose logs'`
