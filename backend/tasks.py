"""Celery задачи"""
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from requests import get
import json
import os
from datetime import datetime
from django.db.models import Prefetch

from backend.services import redis_client
from users.models import User
from .models import (
    Order, Shop, Product, ProductInfo, Category, Parameter, ProductParameter
)
from backend.models import Product
from users.models import User
from imagekit.cachefiles import ImageCacheFile
from celery import shared_task


@shared_task
def send_email(order_id):
    """Отправляет уведомления о заказе клиенту и администраторам"""
    order = Order.objects.select_related('user', 'contact').prefetch_related(
        'ordered_items__product_info__product'
    ).get(id=order_id)

    items_table = ""
    total_price = 0

    for item in order.ordered_items.all():
        item_price = item.quantity * item.product_info.price
        total_price += item_price

        items_table += f"""
{item.product_info.product.name} ({item.product_info.model})
Количество: {item.quantity} × {item.product_info.price:,}₽ = {item_price:,}₽
        """

    client_message = f"""ProcureBot: Заказ №{order.id}

ВАШ ЗАКАЗ:
{items_table}

ИТОГО: {total_price:,}₽
Доставка: {order.contact.city}, {order.contact.street}{' д. ' + order.contact.house if order.contact.house else ''}
Статус: {order.state.upper()}

Спасибо за заказ"""

    send_mail(
        subject=f'ProcureBot: Заказ №{order.id} ({total_price:,}₽)',
        message=client_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
    )

    admin_emails = []
    if hasattr(settings, 'ADMIN_EMAIL') and settings.ADMIN_EMAIL:
        admin_emails.append(settings.ADMIN_EMAIL)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    superusers = User.objects.filter(is_superuser=True).values_list(
        'email', flat=True
    )
    admin_emails.extend([email for email in superusers if email])
    admin_emails = list(set(admin_emails))

    if admin_emails:
        admin_message = f"""НАКЛАДНАЯ №{order.id}

Покупатель: {order.user.email}
Адрес: {order.contact.city}, {order.contact.street}{' д. ' + order.contact.house if order.contact.house else ''}

ТОВАРЫ:
{items_table}

ИТОГО: {total_price:,}₽
Статус: {order.state}"""

        send_mail(
            subject=f'Накладная №{order.id} ({total_price:,}₽)',
            message=admin_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True
        )
        admin_status = f"+{len(admin_emails)} админов"
    else:
        admin_status = "нет админов"

    return f"Email: клиент + {admin_status} (#{order_id}, {total_price:,}₽)"


@shared_task(bind=True, max_retries=3)
def partner_import(self, source, user_id):
    """
    Импорт прайс-листа партнера в базу данных
    Args:
        source: bytes (содержимое файла) ИЛИ URL string
        user_id: ID пользователя-магазина
    Returns:
        str: Отчёт об импорте
    """
    shop_user = User.objects.get(id=user_id)

    try:
        if isinstance(source, bytes):
            content = source.decode('utf-8')
        else:
            original_url = source
            url = source.replace(settings.EXTERNAL_URL, settings.INTERNAL_URL)

            try:
                response = get(url, timeout=10)
                response.raise_for_status()
            except:
                response = get(original_url, timeout=10)
                response.raise_for_status()

            content = response.content.decode('utf-8')

    except Exception as e:
        return f"Ошибка чтения: {str(e)}"

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        import yaml
        data = yaml.safe_load(content)

    shop_name = data['shop']

    with transaction.atomic():
        shop, created = Shop.objects.get_or_create(
            user=shop_user, name=shop_name,
            defaults={'state': True}
        )

        ProductInfo.objects.filter(shop=shop).delete()

        created_count = 0

        for category_data in data['categories']:
            category, _ = Category.objects.get_or_create(
                id=category_data['id'],
                defaults={'name': category_data['name']}
            )
            category.shops.add(shop)

        for good in data['goods']:
            product, _ = Product.objects.get_or_create(
                name=good['name'],
                defaults={'category_id': good['category']}
            )

            product_info = ProductInfo.objects.create(
                product=product,
                external_id=good['id'],
                model=good.get('model', ''),
                price=good['price'],
                price_rrc=good['price_rrc'],
                quantity=good['quantity'],
                shop=shop
            )

            for param_name, param_value in good['parameters'].items():
                parameter, _ = Parameter.objects.get_or_create(name=param_name)
                ProductParameter.objects.create(
                    product_info=product_info,
                    parameter=parameter,
                    value=str(param_value)
                )
            created_count += 1

    return f"Импортировано {created_count} товаров для {shop_name} ({shop_user.email})"


@shared_task
def send_email_verification(user_id):
    """Отправляет ссылку для верификации email"""
    import secrets
    user = User.objects.get(id=user_id)
    token = secrets.token_urlsafe(32)

    redis_client.setex(f"email_verify_{user.email}", 1800, token)
    verify_url = f"{settings.BASE_URL}/api/v1/auth/verify-email-link/?token={token}&email={user.email}"

    send_mail(
        'ProcureBot: Подтвердите email',
        f'Кликните для подтверждения: {verify_url}\n\nСсылка действует 30 минут.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    return f"Email верификация отправлена {user.email}"


@shared_task
def partner_export(shop_id):
    """Экспортирует товары магазина в JSON файл"""
    shop = Shop.objects.select_related('user').get(id=shop_id)
    products = ProductInfo.objects.filter(shop=shop).select_related(
        'product__category'
    ).prefetch_related(
        Prefetch('product_parameters__parameter')
    )

    export_data = {
        'shop': shop.name,
        'categories': [],
        'goods': []
    }

    categories = {}
    for product in products:
        cat_id = product.product.category.id
        if cat_id not in categories:
            categories[cat_id] = {
                'id': cat_id,
                'name': product.product.category.name
            }
    export_data['categories'] = list(categories.values())

    for product_info in products:
        parameters = {}
        for pp in product_info.product_parameters.all():
            parameters[pp.parameter.name] = pp.value

        good = {
            'id': product_info.external_id,
            'name': product_info.product.name,
            'category': product_info.product.category.id,
            'model': product_info.model,
            'price': product_info.price,
            'price_rrc': product_info.price_rrc,
            'quantity': product_info.quantity,
            'parameters': parameters
        }
        export_data['goods'].append(good)

    filename = f"export_{shop.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = f"exports/{filename}"

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    full_path = os.path.join(settings.MEDIA_ROOT, filepath)

    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    download_url = f"{settings.EXTERNAL_URL}{filepath}"

    return f"Экспорт сохранён: {download_url} ({len(export_data['goods'])} товаров)"



@shared_task(bind=True)
def process_user_avatar(self, user_id):
    """Фоновая обработка аватара"""
    try:
        user = User.objects.get(id=user_id)
        
        if user.avatar:
            return f"Avatar ready: {user.email} ({user.avatar.name})"
        
        return f"No avatar: {user.email}"
    
    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as e:
        return f"Error: {str(e)}"



@shared_task(bind=True)
def process_product_images(self, product_id):
    """Фоновая обработка изображений товара"""
    try:
        product = Product.objects.get(id=product_id)

        if product.image:
            return f"Product ready: {product.name} ({product.image.name})"

        return f"No image: {product.name}"

    except Product.DoesNotExist:
        return f"Product {product_id} not found"
    except Exception as e:
        return f"Error: {str(e)}"