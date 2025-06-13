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

User = get_user_model() # Получаем текущую модель пользователя

try:
    from users.models import Profile # ПРОВЕРЬТЕ, что это правильный путь к вашей модели Profile
    _PROFILE_MODEL_AVAILABLE = True
except ImportError:
    _PROFILE_MODEL_AVAILABLE = False
    print("Warning: Profile model not found in users.models. DND sync from UserNotificationSettings will be skipped.")


class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('message', 'Новое личное сообщение'),
        ('group_message', 'Новое сообщение в группе'),
        ('friend_request', 'Запрос в друзья'),
        ('approved_friend_request', 'Запрос в друзья одобрен'),
        ('comment', 'Новый комментарий'),
        ('like', 'Новый лайк'),
        ('repost', 'Новый репост'),
        ('follow', 'Новая подписка'),
        ('system', 'Системное уведомление'), # Общий тип для системных сообщений
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', verbose_name='Получатель')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications', verbose_name='Отправитель')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, verbose_name='Тип уведомления')
    content = models.TextField(blank=True, verbose_name='Содержание') # Например, "Пользователь X отправил вам сообщение"
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')

    target_url = models.CharField(max_length=255, blank=True, null=True, verbose_name='Целевой URL')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        return f"Уведомление для {self.recipient.username} о {self.get_notification_type_display()}"

    def get_absolute_url(self):
        """
        Возвращает URL для перехода по уведомлению.
        Предпочитает сохраненный target_url, если он есть.
        Иначе пытается построить URL из связанного объекта.
        """
        if self.target_url:
            return self.target_url

        # Если target_url нет, пытаемся построить из related_object
        if self.related_object:
            # Если связанный объект имеет метод get_absolute_url (например, Post)
            if hasattr(self.related_object, 'get_absolute_url'):
                return self.related_object.get_absolute_url()

            # Специальные случаи для URL, если related_object не имеет get_absolute_url
            # или его get_absolute_url не подходит для уведомлений
            if self.notification_type == 'message':
                # Для личных сообщений, связанный объект - это ChatMessage
                # Нам нужен URL чата, а не сообщения
                from chat.models import ChatRoom # Импортируем здесь, чтобы избежать циклических импортов
                if isinstance(self.related_object, ChatRoom): # Если related_object это сам ChatRoom (несообщение)
                    return reverse('chat:chat_room', args=[self.related_object.id])
                elif hasattr(self.related_object, 'chat_room') and isinstance(self.related_object.chat_room, ChatRoom):
                    return reverse('chat:chat_room', args=[self.related_object.chat_room.id])

            elif self.notification_type == 'group_message':
                from chat.models import GroupChat # Импортируем здесь
                if isinstance(self.related_object, GroupChat):
                    return reverse('chat:group_chat_room', args=[self.related_object.id])
                elif hasattr(self.related_object, 'group_chat') and isinstance(self.related_object.group_chat, GroupChat):
                    return reverse('chat:group_chat_room', args=[self.related_object.group_chat.id])

            elif self.notification_type in ['friend_request', 'approved_friend_request', 'follow'] and self.sender:
                return reverse('users:profile', args=[self.sender.id])

            elif self.notification_type in ['comment', 'like', 'repost']:
                # Предполагаем, что связанный объект - это Comment, Like или Repost,
                # и у них есть поле 'post'
                from core.models import Post # Пример импорта вашей модели Post
                if isinstance(self.related_object, Post):
                    return reverse('core:post_detail', args=[self.related_object.id])
                elif hasattr(self.related_object, 'post') and isinstance(self.related_object.post, Post):
                    return reverse('core:post_detail', args=[self.related_object.post.id])

        return '#'

class UserNotificationSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_settings', verbose_name='Пользователь')

    NOTIFICATION_SOUND_CHOICES = (
        ('sound_1.mp3', 'Звук 1'),
        ('sound_2.mp3', 'Звук 2'),
        ('sound_3.mp3', 'Звук 3'),
    )
    notification_sound = models.CharField(max_length=100, choices=NOTIFICATION_SOUND_CHOICES, default='sound1.mp3', verbose_name='Звук уведомления')

    volume = models.DecimalField(
        max_digits=3, decimal_places=2,
        default=0.7, # Значение по умолчанию 70%
        validators=[MinValueValidator(0.00), MaxValueValidator(1.00)],
        verbose_name='Громкость уведомлений'
    )

    receive_messages_notifications = models.BooleanField(default=True, verbose_name='Личные сообщения')
    receive_group_messages_notifications = models.BooleanField(default=True, verbose_name='Сообщения в группах')
    receive_friend_requests_notifications = models.BooleanField(default=True, verbose_name='Запросы в друзья')
    receive_approved_friend_requests_notifications = models.BooleanField(default=True, verbose_name='Одобренные запросы в друзья')
    receive_comments_notifications = models.BooleanField(default=True, verbose_name='Комментарии')
    receive_likes_notifications = models.BooleanField(default=True, verbose_name='Лайки')
    receive_reposts_notifications = models.BooleanField(default=True, verbose_name='Репосты')
    receive_follows_notifications = models.BooleanField(default=True, verbose_name='Подписки')

    do_not_disturb = models.BooleanField(default=False, verbose_name='Не беспокоить (отключить все звуки уведомлений)')

    class Meta:
        verbose_name = 'Настройки уведомлений пользователя'
        verbose_name_plural = 'Настройки уведомлений пользователей'

    def __str__(self):
        return f"Настройки уведомлений для {self.user.username}"

