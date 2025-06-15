from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.apps import apps
from django.urls import reverse

User = get_user_model()

try:
    from users.models import Profile
    _PROFILE_MODEL_AVAILABLE = True
except ImportError:
    _PROFILE_MODEL_AVAILABLE = False
    print("Попередження: Модель профілю не знайдена в users.models. Синхронізація 'Не турбувати' з UserNotificationSettings буде пропущена.") # Translated


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('message', 'Нове особисте повідомлення'), # Translated
        ('group_message', 'Нове повідомлення в групі'), # Translated
        ('friend_request', 'Запит у друзі'), # Translated
        ('approved_friend_request', 'Запит у друзі схвалено'), # Translated
        ('comment', 'Новий коментар'), # Translated
        ('like', 'Новий лайк'), # Translated
        ('repost', 'Новий репост'), # Translated
        ('follow', 'Нова підписка'), # Translated
        ('system', 'Системне сповіщення'), # Translated
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', verbose_name='Отримувач') # Translated
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications', verbose_name='Відправник') # Translated
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, verbose_name='Тип сповіщення') # Translated
    content = models.TextField(blank=True, verbose_name='Зміст') # Translated
    is_read = models.BooleanField(default=False, verbose_name='Прочитано') # Translated
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Час створення') # Translated

    target_url = models.CharField(max_length=255, blank=True, null=True, verbose_name='Цільовий URL') # Translated

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Сповіщення' # Translated
        verbose_name_plural = 'Сповіщення' # Translated

    def __str__(self):
        return f"Сповіщення для {self.recipient.username} про {self.get_notification_type_display()}" # Translated

    def get_absolute_url(self):
        """
        Повертає URL для переходу за сповіщенням. # Translated
        Віддає перевагу збереженому target_url, якщо він є. # Translated
        Інакше намагається побудувати URL зі зв'язаного об'єкта. # Translated
        """
        if self.target_url:
            return self.target_url

        if self.related_object:
            if hasattr(self.related_object, 'get_absolute_url'):
                return self.related_object.get_absolute_url()

            if self.notification_type == 'message':
                from chat.models import ChatRoom
                if isinstance(self.related_object, ChatRoom):
                    return reverse('chat:chat_room', args=[self.related_object.id])
                elif hasattr(self.related_object, 'chat_room') and isinstance(self.related_object.chat_room, ChatRoom):
                    return reverse('chat:chat_room', args=[self.related_object.chat_room.id])

            elif self.notification_type == 'group_message':
                from chat.models import GroupChat
                if isinstance(self.related_object, GroupChat):
                    return reverse('chat:group_chat_room', args=[self.related_object.id])
                elif hasattr(self.related_object, 'group_chat') and isinstance(self.related_object.group_chat, GroupChat):
                    return reverse('chat:group_chat_room', args=[self.related_object.group_chat.id])

            elif self.notification_type in ['friend_request', 'approved_friend_request', 'follow'] and self.sender:
                return reverse('users:profile', args=[self.sender.id])

            elif self.notification_type in ['comment', 'like', 'repost']:
                from core.models import Post
                if isinstance(self.related_object, Post):
                    return reverse('core:post_detail', args=[self.related_object.id])
                elif hasattr(self.related_object, 'post') and isinstance(self.related_object.post, Post):
                    return reverse('core:post_detail', args=[self.related_object.post.id])

        return '#'

class UserNotificationSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_settings', verbose_name='Користувач') # Translated

    NOTIFICATION_SOUND_CHOICES = (
        ('sound_1.mp3', 'Звук 1'), # Translated
        ('sound_2.mp3', 'Звук 2'), # Translated
        ('sound_3.mp3', 'Звук 3'), # Translated
    )
    notification_sound = models.CharField(max_length=100, choices=NOTIFICATION_SOUND_CHOICES, default='sound1.mp3', verbose_name='Звук сповіщення') # Translated

    volume = models.DecimalField(
        max_digits=3, decimal_places=2,
        default=0.7,
        validators=[MinValueValidator(0.00), MaxValueValidator(1.00)],
        verbose_name='Гучність сповіщень' # Translated
    )

    receive_messages_notifications = models.BooleanField(default=True, verbose_name='Особисті повідомлення') # Translated
    receive_group_messages_notifications = models.BooleanField(default=True, verbose_name='Повідомлення в групах') # Translated
    receive_friend_requests_notifications = models.BooleanField(default=True, verbose_name='Запити в друзі') # Translated
    receive_approved_friend_requests_notifications = models.BooleanField(default=True, verbose_name='Схвалені запити в друзі') # Translated
    receive_comments_notifications = models.BooleanField(default=True, verbose_name='Коментарі') # Translated
    receive_likes_notifications = models.BooleanField(default=True, verbose_name='Вподобання') # Translated
    receive_reposts_notifications = models.BooleanField(default=True, verbose_name='Репости') # Translated
    receive_follows_notifications = models.BooleanField(default=True, verbose_name='Підписки') # Translated

    do_not_disturb = models.BooleanField(default=False, verbose_name='Не турбувати (вимкнути всі звуки сповіщень)') # Translated

    class Meta:
        verbose_name = 'Налаштування сповіщень користувача' # Translated
        verbose_name_plural = 'Налаштування сповіщень користувачів' # Translated

    def __str__(self):
        return f"Налаштування сповіщень для {self.user.username}" # Translated