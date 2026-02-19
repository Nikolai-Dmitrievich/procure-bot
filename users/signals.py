
from django.db.models.signals import post_save
from django.dispatch import receiver
from backend.tasks import send_email_verification
from .models import User


@receiver(post_save, sender=User)
def send_verification_on_create(sender, instance, created, **kwargs):
    if created and not instance.email_verified and not instance.is_staff:
        send_email_verification.delay(instance.id)
