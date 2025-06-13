# notifications/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import UserNotificationSettings # Для проверки настроек пользователя

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Проверяем, аутентифицирован ли пользователь
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            # Меняем user_group_name на notifications_user_{id}, чтобы соответствовать send_notification_to_user
            self.user_group_name = f'notifications_user_{self.user.id}'

            # Добавляем пользователя в его группу Channels
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

    # Метод для обработки получения уведомления из Channel Layer
    # Имя метода 'new_notification' соответствует 'type': 'new_notification' из group_send
    async def new_notification(self, event):
        notification_data = event
        notification_type = notification_data.get('notification_type')

        # Получаем настройки уведомлений пользователя (асинхронно)
        user_settings = await self.get_user_notification_settings()

        # По умолчанию предполагаем, что уведомление будет отправлено и звук будет проигран
        send_to_client = True
        play_sound = False
        sound_file = ''
        volume = 0.5 # Значение по умолчанию, если настроек нет или они невалидны

        if user_settings:
            volume = float(user_settings.volume) # Обновляем громкость из настроек

            # Логика "Не беспокоить"
            if user_settings.do_not_disturb:
                send_to_client = False # Если режим "Не беспокоить" включен, не отправляем уведомление на клиент
            else:
                # Проверяем конкретные настройки для типа уведомления
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

                # Если уведомление разрешено к отправке на клиент, определяем, нужно ли проигрывать звук
                if send_to_client: # Проверяем send_to_client, а не user_settings.do_not_disturb
                    if user_settings.notification_sound: # Если звук выбран в настройках
                        play_sound = True
                        sound_file = user_settings.notification_sound
        else:
            pass 

        # Добавляем информацию о звуке в данные уведомления перед отправкой на клиент
        notification_data['play_sound'] = play_sound
        notification_data['sound_file'] = sound_file
        notification_data['volume'] = volume

        if send_to_client:
            # Отправляем сообщение клиенту через WebSocket
            await self.send(text_data=json.dumps({
                'type': 'new_notification', # Тип сообщения для клиента (frontend JS)
                'notification': notification_data # Сами данные уведомления
            }))
            print(f"Notification sent to {self.user.username}: {notification_data.get('content')}")
        else:
            print(f"Notification for {self.user.username} of type '{notification_type}' was blocked by user settings.")


    # Вспомогательный метод для получения настроек пользователя из базы данных
    @database_sync_to_async
    def get_user_notification_settings(self):
        try:
            # Используем select_related для оптимизации, если UserNotificationSettings часто обращается к User
            return UserNotificationSettings.objects.select_related('user').get(user=self.user)
        except UserNotificationSettings.DoesNotExist:
            print(f"No notification settings found for user {self.user.username}. Returning default.")
            return None # Если настроек нет, вернем None, что будет означать использование значений по умолчанию