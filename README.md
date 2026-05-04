# 📚 ЕГЭ Бот — Конспекты

Телеграм бот с базой конспектов для подготовки к ЕГЭ.

## Стек
- **aiogram 3.x** — Telegram Bot API
- **PostgreSQL** (Railway) — хранение метаданных
- **Telegram file_id** — хранение файлов (PDF, фото)

## Локальный запуск

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Скопировать и заполнить .env
cp .env.example .env

# 3. Запустить
python bot.py
```

## Деплой на Railway

1. Создай аккаунт на [railway.app](https://railway.app)
2. Новый проект → **Deploy from GitHub repo**
3. Добавь плагин **PostgreSQL** (кнопка New → Database → PostgreSQL)
4. Во вкладке Variables добавь:
   - `BOT_TOKEN` — токен от @BotFather
   - `DATABASE_URL` — скопируй из PostgreSQL плагина (вкладка Connect)
   - `ADMIN_IDS` — твой Telegram ID (узнать: @userinfobot)
5. Railway сам запустит бота через `Procfile`

## Использование (для админа)

- `/admin` — открыть панель управления
  - Добавить предмет (название + эмодзи)
  - Добавить тему к предмету
  - Загрузить конспект (PDF или фото) к теме

## Структура проекта

```
ege_bot/
├── bot.py              # Точка входа
├── config.py           # Токен, переменные окружения
├── database/
│   └── db.py           # Модели и подключение к PostgreSQL
├── handlers/
│   ├── start.py        # /start, главное меню
│   ├── subjects.py     # Выбор предмета → список тем
│   └── notes.py        # Выбор темы → конспекты → отправка файла
└── admin/
    └── upload.py       # Панель загрузки (только для ADMIN_IDS)
```
