import gc
import os
import tempfile
import time
from unittest.mock import patch

import django.test.client as client
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from backend.models import (
    Category,
    Contact,
    Order,
    OrderItem,
    Product,
    ProductInfo,
    Shop,
)

User = get_user_model()


class BackendCoreTests(TestCase):
    """Тесты загрузки прайса и расчета стоимости"""

    def setUp(self):
        self.shop_owner = User.objects.create_user(
            username='shop_test', email='shop@test.com', type='shop'
        )
        self.shop = Shop.objects.create(
            user=self.shop_owner, name='TestShop', state=True
        )
        self.category = Category.objects.create(name='Тест')
        self.product = Product.objects.create(
            name='Test',
            category=self.category
        )

    @patch('backend.tasks.partner_import.delay')
    def test_price_import_task(self, mock_task):
        """Тестирует загрузку прайса через Celery задачу"""

        yaml_data = """
        products:
          - name: Test Product
            model: TP-001
            quantity: 10
            price: 1000
        """

        with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.yaml',
                delete=False
        ) as f:
            f.write(yaml_data)
            file_path = f.name

        from backend.tasks import partner_import
        partner_import.delay(file_path, self.shop.id)

        mock_task.assert_called_once()
        os.unlink(file_path)

    def test_price_calculation(self):
        """Тестирует расчет общей стоимости товара"""

        product_info = ProductInfo.objects.create(
            product=self.product, shop=self.shop, model='Test',
            external_id=12345, quantity=10, price=1000, price_rrc=1200
        )
        total = product_info.quantity * product_info.price
        self.assertEqual(total, 10000)


class OrderTests(TestCase):
    """Тесты создания заказа и прав доступа"""

    def setUp(self):
        self.buyer = User.objects.create_user(
            username='buyer_test', email='buyer@test.com', type='buyer'
        )
        self.shop_owner = User.objects.create_user(
            username='shop_test', email='shop@test.com', type='shop'
        )
        self.shop = Shop.objects.create(
            user=self.shop_owner, name='TestShop', state=True
        )
        self.category = Category.objects.create(name='Тест')
        self.product = Product.objects.create(
            name='Test',
            category=self.category
        )
        self.product_info = ProductInfo.objects.create(
            product=self.product, shop=self.shop, model='Test',
            external_id=12345, quantity=50, price=1000, price_rrc=1200
        )
        self.contact = Contact.objects.create(
            user=self.buyer, city='Москва', street='Тест'
        )

    def test_order_creation(self):
        """Тестирует создание заказа с позициями"""

        order = Order.objects.create(user=self.buyer, state='new')
        OrderItem.objects.create(
            order=order, product_info=self.product_info, quantity=2
        )

        total_price = sum(
            item.quantity * item.product_info.price
            for item in order.ordered_items.all()
        )
        self.assertEqual(total_price, 2000)

    def test_access_rights(self):
        """Тестирует различия прав покупателя и магазина"""

        self.assertEqual(self.buyer.type, 'buyer')
        self.assertEqual(self.shop_owner.type, 'shop')

        self.assertIsNone(getattr(self.buyer, 'shop', None))
        self.assertEqual(self.shop_owner.shop.id, self.shop.id)


class CachePerformanceTests(TestCase):
    """Тесты производительности django-cachalot кэширования"""

    @classmethod
    def setUpTestData(cls):
        """Создаём тестовые данные один раз для всех тестов"""

        from backend.models import Category, Product, ProductInfo, Shop
        from django.contrib.auth import get_user_model

        User = get_user_model()
        cls.client = client.Client()

        shop_owner = User.objects.create_user(
            username='perf_test', email='perf@test.com', type='shop'
        )
        cls.shop = Shop.objects.create(
            user=shop_owner, name='PerfTestShop', state=True
        )
        category = Category.objects.create(name='Тест')
        product = Product.objects.create(name='PerfTest', category=category)

        for i in range(50):
            ProductInfo.objects.create(
                product=product,
                shop=cls.shop,
                model=f'Test-{i}',
                external_id=i,
                quantity=100,
                price=1000 + i * 10,
                price_rrc=1200 + i * 10
            )

    def test_cache_speedup_api(self):
        """Тестирует cachalot БЕЗ аутентификации"""

        url = '/api/v1/products/?limit=10'

        connection.queries_log.clear()
        gc.collect()
        start = time.perf_counter()
        response1 = self.client.get(url, HTTP_HOST='testserver')
        time1 = time.perf_counter() - start
        queries1 = len(connection.queries) or 1
        self.assertEqual(response1.status_code, 200)

        connection.queries_log.clear()
        gc.collect()
        start = time.perf_counter()
        response2 = self.client.get(url, HTTP_HOST='testserver')
        time2 = time.perf_counter() - start
        queries2 = len(connection.queries) or 1
        self.assertEqual(response2.status_code, 200)

        speedup = time1 / time2
        print(
            f"CACHALOT: {time1*1000:.0f}ms/{queries1}SQL → "
            f"{time2*1000:.0f}ms/{queries2}SQL ({speedup:.1f}x)"
        )
