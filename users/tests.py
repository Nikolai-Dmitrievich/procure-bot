from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserTests(TestCase):
    """Тесты создания пользователей и магазинов"""

    def test_create_buyer_user(self):
        """Тестирует создание пользователя-покупателя"""
        user = User.objects.create_user(
            email='buyer1@test.com',
            password='testpass123',
            type='buyer',
            username='buyer1'
        )
        self.assertEqual(user.type, 'buyer')
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)
        self.assertTrue(user.check_password('testpass123'))
        self.assertEqual(user.email, 'buyer1@test.com')

    def test_create_shop_user(self):
        """Тестирует создание пользователя-магазина"""
        user = User.objects.create_user(
            email='shop1@test.com',
            password='testpass123',
            type='shop',
            username='shop1'
        )
        self.assertEqual(user.type, 'shop')
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password('testpass123'))

    def test_create_superuser(self):
        """Тестирует создание суперпользователя"""
        user = User.objects.create_superuser(
            email='admin@test.com',
            password='testpass123',
            username='admin'
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password('testpass123'))

    def test_user_type_choices(self):
        """Тестирует допустимые типы пользователей"""
        choices = ['buyer', 'shop']
        for user_type in choices:
            user = User.objects.create_user(
                email=f'test_{user_type}@test.com',
                password='testpass123',
                type=user_type,
                username=f'test_{user_type}'
            )
            self.assertEqual(user.type, user_type)
            self.assertEqual(
                user.get_type_display(),
                'Покупатель' if user_type == 'buyer' else 'Магазин'
            )

    def test_email_required(self):
        """Тестирует обязательность email"""
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email='',
                password='testpass123',
                username='test'
            )
