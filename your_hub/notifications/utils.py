from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification, UserNotificationSettings
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.conf import settings

def send_notification_to_user(recipient, sender, notification_type, content, related_object=None, custom_url=None):
    channel_layer = get_channel_layer()

    content_type_instance = None
    object_id_instance = None
    final_target_url = custom_url

    if related_object:
        content_type_instance = ContentType.objects.get_for_model(related_object)
        object_id_instance = related_object.pk

        if not final_target_url:
            if hasattr(related_object, 'get_absolute_url'):
                final_target_url = related_object.get_absolute_url()
            else:
                if notification_type in ['message', 'group_message']:
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
                    post_instance = None
                    if hasattr(related_object, 'post') and related_object.post:
                        post_instance = related_object.post
                    elif related_object.__class__.__name__ == 'Post':
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
                target_url=final_target_url,
                content_type=content_type_instance,
                object_id=object_id_instance,
            )
            print(f"Notification object created in DB (ID: {notification.id}) for user {recipient.username}. Content: '{notification.content}' URL: '{notification.target_url}'")


            sender_avatar_url = ''
            if sender and hasattr(sender, 'profile') and sender.profile and sender.profile.avatar:
                sender_avatar_url = sender.profile.avatar.url
            elif settings.STATIC_URL:
                sender_avatar_url = settings.STATIC_URL + 'images/default_avatar.png'


            message_to_channel = {
                'type': 'new_notification',
                'notification': {
                    'id': str(notification.id),
                    'sender_id': sender.id if sender else None,
                    'sender_username': sender.username if sender else 'System',
                    'sender_avatar_url': sender_avatar_url,
                    'content': notification.content,
                    'timestamp': notification.timestamp.isoformat(),
                    'is_read': notification.is_read,
                    'notification_type': notification.notification_type,
                    'object_id': notification.object_id,
                    'object_url': notification.target_url,
                }
            }

            async_to_sync(channel_layer.group_send)(
                f'notifications_user_{recipient.id}',
                message_to_channel
            )
            print(f"Notification (ID: {notification.id}) successfully sent to Channel Layer group 'notifications_user_{recipient.id}'")

    except Exception as e:
        print(f"Error creating or sending notification: {e}")