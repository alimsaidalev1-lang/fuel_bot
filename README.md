# Telegram бот — учёт топлива (готовый проект)

## Подготовка
1. Скопируй файлы проекта в папку.
2. Переименуй `.env.example` → `.env` и вставь:
   - TG_BOT_TOKEN — новый токен (после того как ревокнул старый)
   - ADMIN_ID — твой Telegram user id (можно узнать через @userinfobot или отправив /start в другом боте)
   - DB_PATH — по умолчанию data.db

## Запуск локально
```bash
python -m venv venv
source venv/bin/activate      # или venv\Scripts\activate на Windows
pip install -r requirements.txt
python main.py

