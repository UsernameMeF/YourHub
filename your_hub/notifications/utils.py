# notifications/utils.py
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification, UserNotificationSettings
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse # Для получения URL'ов
from django.conf import settings # Для default_avatar

def send_notification_to_user(recipient, sender, notification_type, content, related_object=None, custom_url=None):
    """
    Создает уведомление в БД и отправляет его через Channel Layer.
    recipient: Пользователь, который получит уведомление.
    sender: Пользователь, который инициировал уведомление (может быть None для системных).
    notification_type: Тип уведомления (из Notification.NOTIFICATION_TYPES).
    content: Содержимое уведомления (текст).
    related_object: Объект модели Django, к которому относится уведомление (например, ChatMessage, Post, FriendRequest).
                    Используется для GenericForeignKey.
    custom_url: Явно заданный URL для перехода по уведомлению. Если не указан,
                функция попытается получить его из related_object.
    """
    channel_layer = get_channel_layer()

    content_type_instance = None
    object_id_instance = None
    final_target_url = custom_url # Если custom_url передан, используем его по умолчанию

    if related_object:
        content_type_instance = ContentType.objects.get_for_model(related_object)
        object_id_instance = related_object.pk # Используем .pk для ID объекта

        # Если custom_url не предоставлен, пытаемся получить его из related_object
        if not final_target_url:
            if hasattr(related_object, 'get_absolute_url'):
                final_target_url = related_object.get_absolute_url()
            else:
                # Дополнительная логика для получения URL, если related_object не имеет get_absolute_url
                # и custom_url не был передан.
                # ЭТО ПРИМЕРЫ, АДАПТИРУЙТЕ ПОД ВАШИ РЕАЛЬНЫЕ URL-ы И МОДЕЛИ!
                if notification_type in ['message', 'group_message']:
                    # Для чатов, related_object - это сообщение, но нам нужен URL чата
                    chat_instance = None
                    if hasattr(related_object, 'chat_room') and related_object.chat_room:
                        chat_instance = related_object.chat_room
                    elif hasattr(related_object, 'group_chat') and related_object.group_chat:
                        chat_instance = related_object.group_chat

                    if chat_instance:
                        if notification_type == 'message':
                            final_target_url = reverse('chat:chat_room', args=[chat_instance.id])
                        elif notification_type == 'group_message':
                            final_target_url = reverse('chat:group_chat_room', args=[chat_instance.id])

                elif notification_type in ['friend_request', 'approved_friend_request', 'follow'] and sender:
                    final_target_url = reverse('users:profile', args=[sender.id])

                elif notification_type in ['comment', 'like', 'repost']:
                    # Если related_object - это Comment, Like или Repost, то нужно получить ссылку на Post
                    post_instance = None
                    if hasattr(related_object, 'post') and related_object.post:
                        post_instance = related_object.post
                    elif related_object.__class__.__name__ == 'Post': # Если сам Post является related_object
                        post_instance = related_object
                    if post_instance:
                        final_target_url = reverse('core:post_detail', args=[post_instance.id])

    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                recipient=recipient,
                sender=sender,
                notification_type=notification_type,
                content=content,
                target_url=final_target_url, # Сохраняем вычисленный или переданный URL
                content_type=content_type_instance,
                object_id=object_id_instance,
            )
            print(f"Notification object created in DB (ID: {notification.id}) for user {recipient.username}. Content: '{notification.content}' URL: '{notification.target_url}'")


            # Формируем данные для отправки через Channel Layer
            # Эти данные будут приняты NotificationConsumer и далее отправлены на notifications.js
            sender_avatar_url = ''
            if sender and hasattr(sender, 'profile') and sender.profile and sender.profile.avatar:
                sender_avatar_url = sender.profile.avatar.url
            elif settings.STATIC_URL: # Дефолтный аватар
                sender_avatar_url = settings.STATIC_URL + 'images/default_avatar.png'


            message_to_channel = {
                'type': 'new_notification', # Имя метода в NotificationConsumer, который обработает это сообщение
                'notification': { # Данные, которые будут отправлены в JS
                    'id': str(notification.id),
                    'sender_id': sender.id if sender else None,
                    'sender_username': sender.username if sender else 'System',
                    'sender_avatar_url': sender_avatar_url,
                    'content': notification.content,
                    'timestamp': notification.timestamp.isoformat(), # ISO формат для удобства парсинга в JS
                    'is_read': notification.is_read,
                    'notification_type': notification.notification_type,
                    'object_id': notification.object_id, # ID связанного объекта, если нужно
                    'object_url': notification.target_url, # URL для JS
                }
            }

            async_to_sync(channel_layer.group_send)(
                f'notifications_user_{recipient.id}', # Группа для уведомлений конкретного пользователя
                message_to_channel
            )
            print(f"Notification (ID: {notification.id}) successfully sent to Channel Layer group 'notifications_user_{recipient.id}'")

    except Exception as e:
        print(f"Error creating or sending notification: {e}")
        # Здесь можно добавить более подробное логирование ошибки