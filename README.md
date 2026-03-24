# ProcureBot
Backend API для магазина с асинхронными задачами, JWT авторизацией и Swagger документацией.

## Описание
Система автоматизации закупок с поддержкой двух типов пользователей (клиенты и магазины). Основные возможности:
- Каталог товаров с открытым доступом (без авторизации)
- Корзина с проверкой остатков (Redis)
- Атомарное создание заказов с блокировкой складских остатков
- Асинхронный импорт/экспорт прайсов поставщиков (Celery, YAML/JSON)
- Email уведомления об заказах
- Swagger/ReDoc API документация
- JWT + Yandex OAuth2 авторизация
- Разделение ролей: Buyer/Shop (с выбором типа после OAuth)
- SQL оптимизация (Silk)
- Sentry мониторинг ошибок
- django-baton улучшенная админка
- django-cachalot Redis query cache
- Pytest + coverage
- Gunicorn production WSGI server
- Health check endpoint (БД + Redis)
## Технологии
**Core:**
- Python 3.13
- Django 6.0.1 + Django REST Framework
- PostgreSQL для хранения данных
- Redis (корзина + Celery broker)
**Async & Background:**
- Celery для асинхронных задач
**Auth:**
- JWT авторизация (djangorestframework-simplejwt)
- **Yandex OAuth2 (social-auth-app-django)**
**API & Docs:**
- drf-spectacular (Swagger/OpenAPI)
**Performance:**
- **django-silk (SQL профилирование)**
- **django-cachalot (Redis query cache)**
**Monitoring:**
- **sentry-sdk (ошибки + traceback)**
**Admin:**
- **django-baton (Material Design админка)**
**DevOps:**
- Docker + Docker Compose
- Gunicorn (production WSGI server)
- Pytest + coverage.py
- python-dotenv (.env файлы)
## Версии и зависимости
| Компонент | Версия |
|-----------|--------|
| **Python** | 3.13 |
| **Django** | 6.0.1 |
| **Django REST Framework** | 3.16.1 |
| **Celery** | 5.6.2 |
| **PostgreSQL** | 16-alpine |
| **Redis** | 7.1.0-alpine |
| **Gunicorn** | 21.2.0 |
| **djangorestframework-simplejwt** | 5.5.1 |
| **drf-spectacular** | 0.29.0 |
Полный список пакетов: `requirements.txt`
## Установка и настройка
### 1. Требования
- Docker и Docker Compose
- Git

### 2. Настройка окружения
Создайте файл `.env` в корне проекта на основе `.env.example`:
```bash
cp .env.example .env
# или
nano .env
```

### 3. Запуск проекта
Зависимости, миграции и статика устанавливаются автоматически.
```bash
make up
# или
docker compose up -d --build
```

### 4. Проверка состояния (Health Check)
```bash
curl http://localhost:8000/api/v1/health/
```
Ответ:
```json
{
    "status": "healthy",
    "checks": {
        "database": "ok",
        "redis": "ok"
    }
}
```
## 5. Проверка логов:
```bash
make logs
# или
docker compose logs -f web
```

## 6. Тестирование
Тесты запускаются через Makefile с coverage отчетом.
В проекте используются модульные и интеграционные тесты.
Запуск тестов
```bash
make test
```

## Production Deployment
### Быстрый старт
```bash
# 1. Настроить .env для production
cp .env.example .env
nano .env

# 2. Обязательно установить:
# DEBUG=False
# SECRET_KEY=<32-64 случайных символа>
# ALLOWED_HOSTS=yourdomain.com

# 3. Запустить
make up

# 4. Создать суперпользователя
make superuser
```


**Критические настройки:**
- DEBUG=False
- SECRET_KEY (уникальный)
- ALLOWED_HOSTS (ваш домен)
- SECURE_SSL_REDIRECT=True (если HTTPS)
- SESSION_COOKIE_SECURE=True
- CSRF_COOKIE_SECURE=True
## Команды API
### Health Check
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/v1/health/` | Проверка БД + Redis |

### Admin
| Метод | Эндпоинт                   | Описание                 |
|-------|----------------------------|--------------------------|
| GET   | `/api/v1/admin/stats/`     | Статистика системы       |
| GET   | `/api/v1/admin/low-stock/` | Товары с низким остатком |
### Поставщики (Магазины)
| Метод | Эндпоинт                   | Описание                  |
|-------|----------------------------|---------------------------|
| POST  | `/api/v1/partners/update/` | Импорт прайса (YAML/JSON) |
| POST  | `/api/v1/partners/export/` | Экспорт прайса магазина   |
| GET   | `/api/v1/partners/state/`  | Статус магазина           |
| POST  | `/api/v1/partners/state/`  | Изменить статус магазина  |
| GET   | `/api/v1/partners/orders/` | Заказы магазина           |
### Авторизация
| Метод  | Эндпоинт                          | Описание                     |
|--------|-----------------------------------|------------------------------|
| POST   | `/api/v1/auth/login/`             | Вход (email/password)        |
| POST   | `/api/v1/auth/register/`          | Регистрация                  |
| POST   | `/api/v1/auth/token/`             | JWT токен                    |
| POST   | `/api/v1/auth/token/refresh/`     | Обновление токена            |
| GET    | `/api/v1/auth/me/`                | Профиль пользователя         |
| PATCH  | `/api/v1/auth/me/`                | Обновить профиль             |
| GET    | `/api/v1/auth/verify-email-link/` | Подтверждение email          |
| DELETE | `/api/v1/auth/delete/`            | Удалить аккаунт              |
| GET    | `/api/v1/auth/social/yandex-oauth2/` | Яндекс OAuth (редирект)   |
| GET    | `/api/v1/auth/social/complete/yandex-oauth2/` | Яндекс OAuth callback |
| POST   | `/api/v1/auth/social/select-type/` | Выбор buyer/shop после OAuth |
### Корзина
| Метод  | Эндпоинт                | Описание           |
|--------|-------------------------|--------------------|
| GET    | `/api/v1/basket/`       | Содержимое корзины |
| POST   | `/api/v1/basket/`       | Добавить товар     |
| DELETE | `/api/v1/basket/`       | Удалить товар      |
| DELETE | `/api/v1/basket/clear/` | Очистить корзину   |
### Контакты
| Метод  | Эндпоинт                 | Описание         |
|--------|--------------------------|------------------|
| GET    | `/api/v1/contacts/`      | Список контактов |
| POST   | `/api/v1/contacts/`      | Создать контакт  |
| PATCH  | `/api/v1/contacts/{id}/` | Обновить контакт |
| DELETE | `/api/v1/contacts/{id}/` | Удалить контакт  |
### Заказы
| Метод | Эндпоинт                      | Описание                 |
|-------|-------------------------------|--------------------------|
| POST  | `/api/v1/orders/create/`      | Создать заказ из корзины |
| GET   | `/api/v1/orders/`             | Список заказов           |
| GET   | `/api/v1/orders/{id}/`        | Детали заказа            |
| PATCH | `/api/v1/orders/{id}/status/` | Изменить статус заказа   |
### Товары (Открытый доступ)
| Метод | Эндпоинт               | Описание                              |
|-------|------------------------|---------------------------------------|
| GET | `/api/v1/products/`      | Список товаров (фильтры: shop, price) |
| GET | `/api/v1/products/{id}/` | Детали товара                         |
## Структура проекта
```
procure-bot/
├── backend/                    # Основное Django приложение
│   ├── migrations/             # Миграции БД
│   ├── admin.py                # Django Admin конфигурация
│   ├── apps.py                 # Django App конфигурация
│   ├── models.py               # Модели (ProductInfo, Order, Shop)
│   ├── serializers.py          # DRF сериализаторы
│   ├── views.py                # API представления
│   ├── services.py             # Бизнес-логика (BasketService)
│   ├── signals.py              # Django signals
│   ├── tasks.py                # Celery задачи
│   ├── urls.py                 # URL маршруты backend
│   └── tests.py                # Тесты backend
├── procure/                    # Основной проект Django
│   ├── asgi.py                 # ASGI конфигурация
│   ├── settings.py             # Настройки Django
│   ├── celery.py               # Celery конфигурация
│   ├── urls.py                 # Главные URL маршруты
│   └── wsgi.py                 # WSGI конфигурация
├── users/                      # Пользователи и авторизация
│   ├── migrations/             # Миграции БД
│   ├── admin.py                # Django Admin конфигурация
│   ├── apps.py                 # Django App конфигурация
│   ├── models.py               # Custom User модель
│   ├── pipeline.py             # Celery pipeline (импорт/экспорт обработка)
│   ├── serializers.py          # DRF сериализаторы
│   ├── views.py                # API представления
│   ├── oauth_views.py          # OAuth2 базовые классы (Yandex)
│   ├── oauth_config.py         # Конфигурация OAuth2 провайдеров
│   ├── urls.py                 # URL маршруты users
│   └── tests.py                # Тесты users
├── static/                     # Статические файлы
│   ├── shop.yaml               # Демо прайс
│   └── price_test.json         # Тестовые данные
├── manage.py                   # Django управление
├── .env.example                # Шаблон конфигурации
├── docker-compose.yml          # Docker сервисы
├── Dockerfile                  # Docker образ (Gunicorn)
├── .gitignore                  # Git игнорируемые файлы
├── .dockerignore               # Docker игнорируемые файлы
├── Makefile                    # Удобные команды
├── requirements.txt            # Python зависимости
└── README.md                   # Документация
```
## Доступ к сервисам
| Сервис        | URL                               |
| ------------- | ----------------------------------|
| Swagger API   | http://localhost:8000/api/swagger/|
| Django Admin  | http://localhost:8000/admin/      |
| ReDoc         | http://localhost:8000/api/redoc/  |
| Silk          | http://localhost:8000/silk/       |
## Docker Compose сервисы
| Сервис        | Описание                        |
| ------------- | ------------------------------- |
| web           | Django API + Gunicorn (4 workers) |
| postgres      | PostgreSQL база данных          |
| redis         | Redis (корзина + Celery broker) |
| celery        | Celery worker                   |
## Основные команды
```bash
make up          # docker compose up -d --build
make logs        # docker compose logs -f web
make test        # Тесты + coverage
make down        # docker compose down
make clean       # Очистка volumes
make superuser   # Создание суперпользователя
make restart     # Перезапуск сервисов
make run         # Локальный запуск с Gunicorn (без Docker)
```

## OAuth2 Flow (Yandex)
```
1. GET /api/v1/auth/social/yandex-oauth2/
   (редирект на Яндекс)

2. Пользователь авторизуется в Яндексе
   (callback с authorization code)

3. GET /api/v1/auth/social/complete/yandex-oauth2/
   (обмен code на токен, создание пользователя)

4. Редирект на /api/v1/auth/social/select-type/?token=xxx
   (frontend получает временный токен)

5. POST /api/v1/auth/social/select-type/
   Body: {"type": "buyer"} или {"type": "shop"}

6. Ответ с JWT токенами
```

## Monitoring
### Health Checks
- Docker healthcheck: /api/v1/health/ каждые 30s
- Auto-restart: restart: unless-stopped

### Logs
```bash
# Web логи
docker compose logs -f web

# Celery логи
docker compose logs -f celery

# Все логи
docker compose logs -f
```
