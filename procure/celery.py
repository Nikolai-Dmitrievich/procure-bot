"""
Celery конфигурация для Django проекта Procure.

Настраивает Celery приложение для асинхронной обработки задач,
автоматически обнаруживает tasks из Django приложений.
"""

import os
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'procure.settings')

app = Celery('procure')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
