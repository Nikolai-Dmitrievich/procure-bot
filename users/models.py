from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager


USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),

)

class User(AbstractUser):
    """
    Стандартная модель пользователей
    """
    REQUIRED_FIELDS = []
    USERNAME_FIELD = 'email'
    objects = UserManager()
    company = models.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True)
    email = models.EmailField(unique=True, verbose_name='Email')
    type = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES, max_length=5, default='buyer')
    email_verified = models.BooleanField(default=False, verbose_name='Email подтвержден')

    def __str__(self):
        return f'{self.get_full_name() or self.email}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)

