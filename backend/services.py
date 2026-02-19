"""Сервис корзины на базе Redis"""
import redis
from django.conf import settings

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=int(settings.REDIS_PORT),
    db=int(settings.REDIS_DB),
    decode_responses=True
)


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
        redis_client.expire(key, 3600 * 24 * 7)

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
