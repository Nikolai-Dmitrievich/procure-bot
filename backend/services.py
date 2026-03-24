"""Сервис корзины на базе Redis"""

import redis
from django.conf import settings

BASKET_EXPIRY_SECONDS = 7 * 24 * 3600

redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=int(settings.REDIS_PORT),
    db=int(settings.REDIS_DB),
    decode_responses=True,
    max_connections=50
)

redis_client = redis.Redis(connection_pool=redis_pool)


class BasketService:
    """Сервис управления корзиной пользователя через Redis"""

    @staticmethod
    def _get_key(user_id):
        """Формирует ключ Redis для корзины пользователя"""

        return f"basket:{user_id}"

    @staticmethod
    def add(user_id, product_info_id, quantity=1):
        """
        Добавляет товар в корзину или увеличивает количество
        Args:
            user_id: ID пользователя
            product_info_id: ID информации о продукте
            quantity: Количество (по умолчанию 1)
        """

        key = BasketService._get_key(user_id)
        redis_client.hincrby(key, product_info_id, quantity)
        redis_client.expire(key, BASKET_EXPIRY_SECONDS)

    @staticmethod
    def get(user_id):
        """
        Получает содержимое корзины пользователя
        Args:
            user_id: ID пользователя
        Returns:
            dict: {product_info_id: quantity}
        """

        key = BasketService._get_key(user_id)
        items = redis_client.hgetall(key)
        return items

    @staticmethod
    def clear(user_id):
        """Очищает всю корзину пользователя"""

        key = BasketService._get_key(user_id)
        redis_client.delete(key)
