# ProcureBot

Backend API для магазина с асинхронными задачами, JWT авторизацией и Swagger документацией.

## Описание

Система автоматизации закупок с поддержкой двух типов пользователей (клиенты и магазины). Основные возможности:

- Каталог товаров с открытым доступом (без авторизации)
- Корзина с проверкой остатков (Redis)
- Атомарное создание заказов с блокировкой складских остатков
- Асинхронный импорт/экспорт прайсов поставщиков (Celery, YAML/JSON)
- Email уведомления об заказах
- Swagger API документация

## Технологии

- Python 3.13
- Django 5.2 + Django REST Framework
- PostgreSQL для хранения данных
- Redis (корзина + Celery broker)
- Celery для асинхронных задач
- JWT авторизация (djangorestframework-simplejwt)
- Docker + Docker Compose
- Pytest + coverage.py
- drf-spectacular (Swagger/OpenAPI)
- python-dotenv (.env файлы)

## Установка и настройка

### 1. Требования

- Docker и Docker Compose
- Git

### 2. Настройка окружения

Создайте файл `.env` в корне проекта на основе `.env.example`:

bash
cp .env.example .env
nano .env

### 3. Запуск проекта
Зависимости, миграции и статика устанавливаются автоматически.

bash
make up
или
docker compose up -d --build

## 4. Проверка логов:

bash
make logs
или  
docker compose logs -f web

## 5. Тестирование

Тесты запускаются через Makefile с coverage отчетом. 
В проекте используются модульные и интеграционные тесты.

Запуск тестов
bash
make test

## Команды API

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

| Метод  | Эндпоинт                          | Описание              |
|--------|-----------------------------------|-----------------------|
| POST   | `/api/v1/auth/login/`             | Вход (email/password) |
| POST   | `/api/v1/auth/register/`          | Регистрация           |
| POST   | `/api/v1/auth/token/`             | JWT токен             |
| POST   | `/api/v1/auth/token/refresh/`     | Обновление токена     |
| GET    | `/api/v1/auth/me/`                | Профиль пользователя  |
| PATCH  | `/api/v1/auth/me/`                | Обновить профиль      |
| GET    | `/api/v1/auth/verify-email-link/` | Подтверждение email   |
| DELETE | `/api/v1/auth/delete/`            | Удалить аккаунт       |

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
│   ├── serializers.py          # DRF сериализаторы
│   ├── views.py                # API представления
│   ├── urls.py                 # URL маршруты users
│   └── tests.py                # Тесты users
├── static/                     # Статические файлы
│   ├── shop.yaml               # Демо прайс
│   └── price_test.json         # Тестовые данные
├── manage.py                   # Django управление
├── .env.example                # Шаблон конфигурации
├── docker-compose.yml          # Docker сервисы
├── Dockerfile                  # Docker образ
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


## Docker Compose сервисы

| Сервис        | Описание                        |
| ------------- | ------------------------------- |
| web           | Django API + Celery worker      |
| postgres      | PostgreSQL база данных          |
| redis         | Redis (корзина + Celery broker) |

## Основные команды

bash
```
- make up        # docker compose up -d --build
- make logs      # docker compose logs -f web  
- make test      # Тесты + coverage
- make down      # docker compose down
- make clean     # Очистка volumes
- make superuser # Создание суперпользователя
- make restart   # Перезапуск сервисов
```

