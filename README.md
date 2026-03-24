# FamBot

Telegram-бот и веб-приложение для пар. Помогает отслеживать историю отношений, вести совместный вишлист и хранить общие ресурсы.

## Возможности

- **Пары**: создание пар через инвайт-токен, кастомные ники для партнёра
- **История отношений**: дата начала, статистика (дней вместе, лет, месяцев), обратный отсчёт до годовщины, отслеживание milestone'ов
- **Вишлист**: личный список желаний каждого партнёра с приоритетами, статусом выполнения и ссылками
- **Облачное хранилище**: хранение ссылки на общее хранилище (Google Drive и др.)
- **Уведомления**: автоматические уведомления о новых пожеланиях партнёра и milestone'ах
- **Экспорт**: выгрузка вишлиста в Excel (.xlsx) прямо в Telegram
- **Темы**: голубая ("Вода") и розовая ("Роза")

## Стек

| Слой | Технологии |
|------|-----------|
| Bot | Python, pyTelegramBotAPI |
| Web App | Flask, Vanilla JS, Telegram WebApp SDK |
| Database | PostgreSQL |
| Прочее | openpyxl, python-dotenv |

## Структура проекта

```
FamBot/
├── tgbot/
│   ├── main.py          # Точка входа бота
│   ├── handlers.py      # Обработчики сообщений и колбэков
│   ├── flows.py         # UI-меню и диалоги
│   ├── services.py      # Бизнес-логика и запросы к БД
│   ├── notifier.py      # Система уведомлений
│   ├── db.py            # Подключение к БД
│   ├── bot_setup.py     # Инициализация бота
│   ├── config.py        # Конфигурация
│   └── migrations.sql   # Схема БД
└── webapp/
    ├── app.py           # Flask API
    ├── templates/
    │   └── index.html
    └── static/
        ├── main.js
        └── style.css
```

## Установка и запуск

### 1. Зависимости

```bash
pip install -r requirements.txt
```

### 2. База данных

```bash
psql -U postgres -d lovebot -f tgbot/migrations.sql
```

### 3. Переменные окружения

Создайте `tgbot/.env`:

```env
BOT_TOKEN=your_telegram_bot_token
BOT_USERNAME=your_bot_username
DATABASE_URL=postgres://user:password@localhost:5432/lovebot
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=lovebot
DB_USER=postgres
DB_PASSWORD=your_password
```

### 4. Запуск

**Бот:**
```bash
cd tgbot
python main.py
```

**Веб-приложение:**
```bash
cd webapp
python app.py  # http://0.0.0.0:8000
```

## Схема базы данных

| Таблица | Назначение |
|---------|-----------|
| `users` | Пользователи Telegram |
| `pairs` | Пары (creator + partner, дата начала, алиасы) |
| `pair_invites` | Инвайт-токены для создания пар |
| `wishlist_items` | Элементы вишлиста с приоритетом и статусом |
| `notifications_log` | Лог отправленных уведомлений |
