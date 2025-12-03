from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Reminder, Notification

@receiver(post_save, sender=Reminder)
def create_notification_and_email(sender, instance, created, **kwargs):
    """
    Create an in-app notification and send email for reminders.
    If the reminder is due now or in the past, it triggers immediately.
    """
    if created or not instance.is_triggered:
        now = timezone.now()

        # Only trigger if reminder time has arrived
        if instance.reminder_time <= now:
            # Create in-app notification
            Notification.objects.create(
                user=instance.task.user,
                message=f"Reminder: '{instance.task.title}' is due now!",
                category='reminder'
            )

            # Send email if user has email notifications enabled
            user_profile = getattr(instance.task.user, 'userprofile', None)
            if user_profile and getattr(user_profile, 'reminder_email', True):
                send_mail(
                    subject=f"Reminder: {instance.task.title}",
                    message=f"Hello {instance.task.user.userprofile.full_name},\n\n"
                            f"This is a reminder that your task '{instance.task.title}' "
                            f"is due now.\n\nRegards,\nYour Team",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.task.user.email],
                    fail_silently=False
                )

            # Mark reminder as triggered
            instance.is_triggered = True
            instance.save()
