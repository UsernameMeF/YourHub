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
            print(f"WebSocket connected for user: {self.user.username}, group: {self.user_group_name}")
        else:
            await self.close()
            print("WebSocket connection denied: User not authenticated")

    async def disconnect(self, close_code):
        if self.scope["user"].is_authenticated:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            print(f"WebSocket disconnected for user: {self.user.username}")

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
            print(f"Notification sent to {self.user.username}: {notification_data.get('content')}")
        else:
            print(f"Notification for {self.user.username} of type '{notification_type}' was blocked by user settings.")


    @database_sync_to_async
    def get_user_notification_settings(self):
        try:
            return UserNotificationSettings.objects.select_related('user').get(user=self.user)
        except UserNotificationSettings.DoesNotExist:
            print(f"No notification settings found for user {self.user.username}. Returning default.")
            return None