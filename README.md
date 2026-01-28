Kapitonovi Wedding — Telegram Mini App

Telegram Mini App + backend (FastAPI) + bot (Telegram) + SQLite.
Проект предназначен для сбора анкет гостей, управления “семьями” (пара + дети), отображения информации о мероприятии и расписаний (две группы), а также админ-управления через Telegram-бота.

Архитектура

webapp/ — фронтенд Mini App (Vite + React + TypeScript)

backend/ — FastAPI API + SQLite (основной источник данных)

bot/ — Telegram bot (админ-меню, уведомления, рассылки)

Общение WebApp ↔ Backend идёт через HTTP API.
Авторизация: через Telegram WebApp initData (основной сценарий) + fallback по invite-token для browser mode (если включено).

Структура репозитория (важные файлы)
/backend
  /app
    main.py
    db.py
    models.py
    schemas.py
    /routers
      auth.py
      profile.py
      family.py
      event_info.py
      questions.py
      admin.py
    /services
      telegram_auth.py
      notifier.py
  /data/app.db        # SQLite (может монтироваться в prod)
/webapp
  /src
    api.ts
    app.tsx
    /screens
    /pages
  nginx.conf
/docker-compose.server.yml
/docker-compose.prod.yml
.env

База данных (SQLite)

По умолчанию backend использует SQLite файл:

prod: /app/data/app.db (в контейнере backend)

host: обычно монтируется как backend/data/app.db (bind-mount)

Проверить состояние БД можно через админ-endpoint (если включён):

GET /api/admin/db-health

Требования

Docker + Docker Compose (v2)

Node.js (если запуск webapp локально без Docker)

Python 3.11+ (если запуск backend локально без Docker)

Переменные окружения

.env в корне проекта (или отдельные .env для сервисов) обычно содержит:

BOT_TOKEN — токен Telegram-бота (тот же используется для проверки initData)

ADMIN_IDS — список Telegram ID админов (через запятую)

DATABASE_URL или DB_PATH — путь к SQLite

(опционально) настройки домена, webhook, уведомлений и т.д.

Есть пример: .env.example

Запуск на сервере (production)

Обычно используется compose-файл сервера:

docker compose -f docker-compose.server.yml up -d --build


Проверить логи:

docker compose -f docker-compose.server.yml logs -n 200 backend
docker compose -f docker-compose.server.yml logs -n 200 webapp
docker compose -f docker-compose.server.yml logs -n 200 bot


Остановить:

docker compose -f docker-compose.server.yml down

Деплой (обновление с git)

Типовой сценарий:

cd ~/Vedding_bot
git pull
docker compose -f docker-compose.server.yml up -d --build


Если нужно подчистить старые образы/кеш:

docker compose -f docker-compose.server.yml down
docker system prune -f
docker compose -f docker-compose.server.yml up -d --build

API: принципы
Канонический префикс

Все пользовательские запросы должны ходить на /api/*.

Если в логах backend появляются запросы без /api (например /auth/telegram, /event-info/*), это означает:

фронт где-то дергает legacy URL, или

пользователь попал на старую сборку (кеш Telegram WebView)

Рекомендуемая стратегия:

фронт: единый api.ts, все запросы через buildUrl(/api/...)

backend: по возможности поддерживать legacy aliases (чтобы не падало 404)

Пользовательские сценарии (WebApp)
Анкета

“Смогу присутствовать?” — выбор статуса обязателен

Сохранение анкеты пишет данные в SQLite

Отдельные поля могут быть валидируемыми (например, обязательные)

Семья

максимум 2 взрослых (пара) + любое число детей

ребёнка можно сохранить текстом без привязки

если для ребёнка/партнёра найден username — отправляется уведомление

Информация о событии

Контент редактируется админами сыром текстом (кроме локации/контактов/таймингов), а в WebApp форматируется под стиль приложения.

Расписание

Две группы пользователей:

Группа 1: родственники (родственник чекбокс) + “лучшие друзья” (скрытый флаг профиля, виден админам)

Группа 2: все остальные

Расписание в админке редактируется отдельно для каждой группы.

Админка через Telegram Bot

Админы (по ADMIN_IDS) могут:

смотреть список гостей (табличный вывод)

удалять гостей

чистить БД (с подтверждениями)

редактировать контент “Информация о событии”

редактировать расписание (две группы)

включать/выключать системные уведомления (кроме вопросов)

получать вопросы от гостей (всегда приходят)

Частые проблемы и диагностика
1) 404 на /auth/telegram или /event-info/*

Симптом: в backend логах:

POST /auth/telegram 404

GET /event-info/content 404

GET /event-info/timing/me 404

Причина: фронт дергает URL без /api или кеш старой сборки.

Что делать:

проверить webapp/src/api.ts, что base = /api

найти все fetch/axios вне api.ts и заменить на общий слой API

(опционально) добавить legacy aliases на backend (прокси на /api/*)

2) В админке “Сохранено”, но в WebApp не видно

Причина: WebApp не читает правильный endpoint (или 404), либо парсер контента падает и подставляет fallback.

Проверка:

открыть devtools (если возможно) и посмотреть network

в backend логах убедиться, что есть GET /api/... 200

руками дернуть endpoint:

curl -i https://<domain>/api/admin/event-content

3) БД пустая в dev, но не в prod

Нормально, если dev и prod используют разные mount/пути.
В prod чаще всего данные лежат в backend/data/app.db на хосте (bind mount).

Интеграция Google Sheets (секреты)

Сервисный JSON ключ не коммитим в git.
Рекомендуемый путь на сервере:

/home/<user>/secrets/google/service-account.json

Далее пробрасываем путь через env переменную, например:

GOOGLE_SA_JSON=/home/<user>/secrets/google/service-account.json

Лицензия / Примечания

Проект внутренний. Персональные данные гостей не публиковать и не хранить в открытом доступе.
