from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.apps import apps

_DND_SYNC_IN_PROGRESS_SETTINGS = False
_DND_SYNC_IN_PROGRESS_PROFILE = False

@receiver(post_save, sender=get_user_model())
def create_user_notification_settings(sender, instance, created, **kwargs):
    if created:
        UserNotificationSettings = apps.get_model('notifications', 'UserNotificationSettings')
        UserNotificationSettings.objects.get_or_create(user=instance)

@receiver(post_save, sender=apps.get_model('notifications', 'UserNotificationSettings'))
def sync_dnd_setting_with_profile_status(sender, instance, **kwargs):
    global _DND_SYNC_IN_PROGRESS_SETTINGS
    if _DND_SYNC_IN_PROGRESS_SETTINGS:
        return

    _DND_SYNC_IN_PROGRESS_SETTINGS = True
    try:
        Profile = apps.get_model('users', 'Profile')
        profile, created = Profile.objects.get_or_create(user=instance.user)
        if instance.do_not_disturb and profile.status != 'dnd':
            profile.status = 'dnd'
            profile.save(update_fields=['status'])
        elif not instance.do_not_disturb and profile.status == 'dnd':
            profile.status = 'online'
            profile.save(update_fields=['status'])
    except LookupError:
        print("Попередження: Модель 'users.Profile' не знайдена під час синхронізації налаштування 'Не турбувати' з UserNotificationSettings. Чи додано 'users' до INSTALLED_APPS?") # Translated
    except Exception as e:
        print(f"Помилка синхронізації налаштування 'Не турбувати' зі статусом профілю для {instance.user.username}: {e}") # Translated
    finally:
        _DND_SYNC_IN_PROGRESS_SETTINGS = False