from django.db import models
from django.contrib.auth.models import (
    AbstractUser,
    UserManager,
    BaseUserManager
    )


USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),

)


class UserManager(BaseUserManager):
    """Кастомный менеджер для email как username"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен!')
        email = self.normalize_email(email)

        extra_fields.setdefault('is_active', False)
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser должен иметь is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Стандартная модель пользователей
    """
    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'email'
    objects = UserManager()
    company = models.CharField(
        verbose_name='Компания',
        max_length=40,
        blank=True
        )
    position = models.CharField(
        verbose_name='Должность',
        max_length=40,
        blank=True
        )
    email = models.EmailField(unique=True, verbose_name='Email')
    type = models.CharField(
        verbose_name='Тип пользователя',
        choices=USER_TYPE_CHOICES,
        max_length=5,
        default='buyer'
        )
    email_verified = models.BooleanField(
        default=False,
        verbose_name='Email подтвержден'
        )

    def __str__(self):
        return f'{self.get_full_name() or self.email}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)
