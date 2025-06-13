# notifications/apps.py
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = 'Уведомления'

    def ready(self):
        # Импортируем сигналы здесь, когда Django полностью загружен
        import notifications.signals