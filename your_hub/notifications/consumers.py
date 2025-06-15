import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import UserNotificationSettings

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            self.user_group_name = f'notifications_user_{self.user.id}'

            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            await self.accept()
            print(f"WebSocket підключено для користувача: {self.user.username}, група: {self.user_group_name}") # Translated
        else:
            await self.close()
            print("Підключення WebSocket відхилено: Користувач не автентифікований") # Translated

    async def disconnect(self, close_code):
        if self.scope["user"].is_authenticated:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            print(f"WebSocket відключено для користувача: {self.user.username}") # Translated

    async def new_notification(self, event):
        notification_data = event
        notification_type = notification_data.get('notification_type')

        user_settings = await self.get_user_notification_settings()

        send_to_client = True
        play_sound = False
        sound_file = ''
        volume = 0.5

        if user_settings:
            volume = float(user_settings.volume)

            if user_settings.do_not_disturb:
                send_to_client = False
            else:
                if notification_type == 'message' and not user_settings.receive_messages_notifications:
                    send_to_client = False
                elif notification_type == 'group_message' and not user_settings.receive_group_messages_notifications:
                    send_to_client = False
                elif notification_type == 'friend_request' and not user_settings.receive_friend_requests_notifications:
                    send_to_client = False
                elif notification_type == 'friend_request_approved' and not user_settings.receive_approved_friend_requests_notifications:
                    send_to_client = False
                elif notification_type == 'comment' and not user_settings.receive_comments_notifications:
                    send_to_client = False
                elif notification_type == 'like' and not user_settings.receive_likes_notifications:
                    send_to_client = False
                elif notification_type == 'repost' and not user_settings.receive_reposts_notifications:
                    send_to_client = False
                elif notification_type == 'follow' and not user_settings.receive_follows_notifications:
                    send_to_client = False

                if send_to_client:
                    if user_settings.notification_sound:
                        play_sound = True
                        sound_file = user_settings.notification_sound
        else:
            pass 

        notification_data['play_sound'] = play_sound
        notification_data['sound_file'] = sound_file
        notification_data['volume'] = volume

        if send_to_client:
            await self.send(text_data=json.dumps({
                'type': 'new_notification',
                'notification': notification_data
            }))
            print(f"Сповіщення надіслано користувачу {self.user.username}: {notification_data.get('content')}") # Translated
        else:
            print(f"Сповіщення для {self.user.username} типу '{notification_type}' було заблоковано налаштуваннями користувача.") # Translated


    @database_sync_to_async
    def get_user_notification_settings(self):
        try:
            return UserNotificationSettings.objects.select_related('user').get(user=self.user)
        except UserNotificationSettings.DoesNotExist:
            print(f"Налаштування сповіщень для користувача {self.user.username} не знайдено. Повернення за замовчуванням.") # Translated
            return None