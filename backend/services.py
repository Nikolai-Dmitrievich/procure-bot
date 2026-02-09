
import redis
from django.conf import settings
import os
from dotenv import load_dotenv
load_dotenv()


redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=int(os.getenv('REDIS_PORT')),
    db=int(os.getenv('REDIS_DB')),
    decode_responses=True
)

class BasketService:
    @staticmethod
    def _get_key(user_id):
        return f"basket:{user_id}"
    
    @staticmethod
    def add(user_id, product_info_id, quantity=1):
        key = BasketService._get_key(user_id)
        redis_client.hincrby(key, product_info_id, quantity)
        redis_client.expire(key, 3600*24*7)
    
    @staticmethod
    def get(user_id):
        key = BasketService._get_key(user_id)
        items = redis_client.hgetall(key)
        return items 
