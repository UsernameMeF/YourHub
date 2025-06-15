# users/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.apps import apps

_DND_SYNC_IN_PROGRESS_PROFILE = False

@receiver(post_save, sender=apps.get_model('users', 'Profile'))
def sync_profile_status_with_dnd_setting(sender, instance, **kwargs):
    global _DND_SYNC_IN_PROGRESS_PROFILE
    if _DND_SYNC_IN_PROGRESS_PROFILE:
        return

    _DND_SYNC_IN_PROGRESS_PROFILE = True
    try:
        UserNotificationSettings = apps.get_model('notifications', 'UserNotificationSettings')
        settings, created = UserNotificationSettings.objects.get_or_create(user=instance.user)
        if instance.status == 'dnd' and not settings.do_not_disturb:
            settings.do_not_disturb = True
            settings.save(update_fields=['do_not_disturb'])
        elif instance.status != 'dnd' and settings.do_not_disturb:
            settings.do_not_disturb = False
            settings.save(update_fields=['do_not_disturb'])
    except LookupError:
        print("Warning: 'notifications.UserNotificationSettings' model not found when syncing Profile status. Is 'notifications' in INSTALLED_APPS?")
    except Exception as e:
        print(f"Error syncing Profile status with DND setting for {instance.user.username}: {e}")
    finally:
        _DND_SYNC_IN_PROGRESS_PROFILE = False
