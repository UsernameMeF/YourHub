# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.apps import apps

# Флаги для предотвращения рекурсии
_DND_SYNC_IN_PROGRESS_SETTINGS = False
_DND_SYNC_IN_PROGRESS_PROFILE = False

@receiver(post_save, sender=get_user_model())
def create_user_notification_settings(sender, instance, created, **kwargs):
    """
    Создает объект UserNotificationSettings для нового пользователя.
    """
    if created:
        UserNotificationSettings = apps.get_model('notifications', 'UserNotificationSettings')
        UserNotificationSettings.objects.get_or_create(user=instance)

@receiver(post_save, sender=apps.get_model('notifications', 'UserNotificationSettings'))
def sync_dnd_setting_with_profile_status(sender, instance, **kwargs):
    """
    Синхронизирует флаг do_not_disturb с полем статуса в Profile.
    """
    global _DND_SYNC_IN_PROGRESS_SETTINGS
    if _DND_SYNC_IN_PROGRESS_SETTINGS:
        return

    _DND_SYNC_IN_PROGRESS_SETTINGS = True
    try:
        Profile = apps.get_model('users', 'Profile') # Отложенный импорт модели Profile
        profile, created = Profile.objects.get_or_create(user=instance.user)
        # Если в настройках DND включен, а в профиле НЕ "Не беспокоить"
        if instance.do_not_disturb and profile.status != 'dnd':
            profile.status = 'dnd'
            profile.save(update_fields=['status'])
        # Если в настройках DND выключен, а в профиле "Не беспокоить"
        elif not instance.do_not_disturb and profile.status == 'dnd':
            # Если выключили DND, можно вернуть на 'online' или другой дефолтный статус
            profile.status = 'online' # Или любой ваш дефолтный статус
            profile.save(update_fields=['status'])
    except LookupError:
        print("Warning: 'users.Profile' model not found when syncing DND setting from UserNotificationSettings. Is 'users' in INSTALLED_APPS?")
    except Exception as e:
        print(f"Error syncing DND setting with Profile status for {instance.user.username}: {e}")
    finally:
        _DND_SYNC_IN_PROGRESS_SETTINGS = False