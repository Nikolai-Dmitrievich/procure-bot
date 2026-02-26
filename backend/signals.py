# backend/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import User
from backend.models import Product
from backend.tasks import (
    process_user_avatar, 
    process_product_images
)

@receiver(post_save, sender=User)
def generate_user_thumbnails(sender, instance, created, **kwargs):
    if created and instance.avatar:
        process_user_avatar.delay(instance.id)

@receiver(post_save, sender=Product)
def generate_product_thumbnails(sender, instance, created, **kwargs):
    if instance.image:
        process_product_images.delay(instance.id)
