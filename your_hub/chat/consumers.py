import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from django.db import transaction # Для атомарности операций в асинхронном контексте

from .models import ChatRoom, ChatMessage, ChatAttachment, GroupChat, GroupChatMessage, GroupChatAttachment
from django.contrib.auth import get_user_model

# Импортируем утилиту для отправки уведомлений
from notifications.utils import send_notification_to_user
from django.urls import reverse

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    # --- Вспомогательная функция для определения типа чата и получения моделей ---
    @database_sync_to_async
    def _get_chat_models_and_instance(self, room_id, room_type): # Добавили room_type
        if room_type == 'private':
            try:
                chat_instance = ChatRoom.objects.get(id=room_id)
                return ChatRoom, ChatMessage, ChatAttachment, 'private', chat_instance
            except ChatRoom.DoesNotExist:
                return None, None, None, None, None
        elif room_type == 'group':
            try:
                chat_instance = GroupChat.objects.get(id=room_id)
                return GroupChat, GroupChatMessage, GroupChatAttachment, 'group', chat_instance
            except GroupChat.DoesNotExist:
                return None, None, None, None, None
        else:
            return None, None, None, None, None


    async def connect(self):
        self.room_type = self.scope['url_route']['kwargs']['room_type']
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Определяем тип чата и получаем соответствующие модели и экземпляр
        ChatModel, MessageModel, AttachmentModel, room_type, chat_instance = await self._get_chat_models_and_instance(self.room_id, self.room_type)

        if not chat_instance or not await self.is_user_in_chat(self.user, chat_instance):
            await self.close()
            return

        self.chat_instance = chat_instance
        self.MessageModel = MessageModel
        self.AttachmentModel = AttachmentModel
        self.room_type = room_type
        # Определяем имя группы на основе типа чата
        self.room_group_name = f'{room_type}_chat_{self.room_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # При подключении пользователя, помечаем все сообщения, предназначенные ему, как прочитанные
        await self.mark_and_notify_messages_as_read(self.user, self.chat_instance, self.MessageModel, self.room_group_name)


    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            if self.user.is_authenticated:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_status',
                        'username': self.user.username,
                        'is_typing': False
                    }
                )
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'chat_message':
            message_content = data.get('message', '').strip()
            attachments_data = data.get('attachments', []) # Для сообщений, отправленных через AJAX views.py

            if message_content or attachments_data:
                try:
                    # Вызываем новый асинхронный метод для сохранения и отправки уведомлений
                    chat_message = await self._save_message_and_send_notifications(
                        self.user,
                        self.chat_instance,
                        self.MessageModel,
                        message_content,
                        attachments_data, 
                        self.room_type,
                        self.room_id
                    )

                    sender_id = self.user.id
                    sender_avatar_url = await self.get_user_avatar_url(self.user)
                    read_count = await self.get_message_read_count(chat_message)

                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'chat_message',
                            'message': message_content,
                            'sender_username': self.user.username,
                            'sender_id': sender_id,
                            'sender_avatar_url': sender_avatar_url,
                            'timestamp': chat_message.timestamp.strftime('%d.%m.%Y %H:%M'),
                            'message_id': str(chat_message.id),
                            'attachments': attachments_data,
                            'read_count': read_count,
                            'is_edited': False,
                        }
                    )
                    print(f"DEBUG (ChatConsumer): Message sent to chat group: {self.room_group_name}")

                except Exception as e:
                    print(f"ERROR (ChatConsumer): Failed to save message or send notifications: {e}")
                    import traceback
                    traceback.print_exc()
                    # Здесь можно отправить ошибку обратно клиенту, если нужно
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Ошибка при отправке сообщения: ' + str(e)
                    }))

        elif message_type == 'typing_status':
            is_typing = data.get('is_typing', False)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_status',
                    'username': self.user.username,
                    'is_typing': is_typing
                }
            )
        elif message_type == 'read_receipt':
            message_id = data.get('message_id')
            if message_id:
                message_updated = await self.add_reader_to_message_and_check(message_id, self.user, self.MessageModel)

                if message_updated:
                    updated_read_count = await self.get_message_read_count_by_id(message_id, self.MessageModel)

                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'read_receipt_notification',
                            'message_id': message_id,
                            'reader_id': self.user.id,
                            'read_count': updated_read_count
                        }
                    )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_username': event['sender_username'],
            'sender_id': event['sender_id'],
            'sender_avatar_url': event['sender_avatar_url'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id'],
            'attachments': event.get('attachments', []),
            'read_count': event.get('read_count', 0),
            'is_edited': event.get('is_edited', False),
        }))

    async def typing_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing_status',
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def read_receipt_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read_receipt_notification',
            'message_id': event['message_id'],
            'reader_id': event['reader_id'],
            'read_count': event['read_count']
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message_id': event['message_id'],
            'new_content': event['new_content'],
            'attachments': event.get('attachments', []), # Добавлено для обновления вложений
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id']
        }))

    # --- Database Sync to Async Helpers (updated) ---

    @database_sync_to_async
    def is_user_in_chat(self, user, chat_instance):
        return chat_instance.participants.filter(id=user.id).exists()

    # НОВЫЙ ВСПОМОГАТЕЛЬНЫЙ МЕТОД ДЛЯ СОХРАНЕНИЯ СООБЩЕНИЙ И ОТПРАВКИ УВЕДОМЛЕНИЙ
    @database_sync_to_async
    def _save_message_and_send_notifications(self, sender, chat_instance, MessageModel, content, attachments_data, room_type, room_id):
        """
        Сохраняет сообщение в БД, добавляет отправителя как прочитавшего,
        и вызывает send_notification_to_user для других участников чата.
        """
        with transaction.atomic():
            if isinstance(chat_instance, ChatRoom):
                chat_message = MessageModel.objects.create(
                    chat_room=chat_instance,
                    sender=sender,
                    content=content,
                    is_edited=False
                )
            elif isinstance(chat_instance, GroupChat):
                chat_message = MessageModel.objects.create(
                    group_chat=chat_instance,
                    sender=sender,
                    content=content,
                    is_edited=False
                )
            else:
                raise ValueError("Неизвестный тип чата для сохранения сообщения.")


            recipients = []
            if room_type == 'private':
                recipients = list(chat_instance.participants.exclude(id=sender.id))
            elif room_type == 'group':
                recipients = list(chat_instance.participants.exclude(id=sender.id))
            
            # Обрезаем контент сообщения для уведомления
            display_content = content
            if len(display_content) > 50:
                display_content = display_content[:47] + '...'
            elif not display_content and attachments_data: # Если только вложения
                display_content = "Новые вложения"
            elif not display_content:
                display_content = "Пустое сообщение"

            # Формируем URL для уведомления
            notification_url = '#'
            if room_type == 'private':
                notification_url = reverse('chat:chat_room', args=[chat_instance.id])
            elif room_type == 'group':
                notification_url = reverse('chat:group_chat_room', args=[chat_instance.id])

            # Отправляем уведомления каждому получателю
            for recipient in recipients:
                notification_type_str = 'message' if room_type == 'private' else 'group_message'
                notification_content_text = f"{sender.username} написал вам: \"{display_content}\""
                if room_type == 'group':
                    notification_content_text = f"{sender.username} в группе \"{chat_instance.name}\": \"{display_content}\""
                
                print(f"DEBUG (Consumer - Notification Call): Sending notification. Recipient: {recipient.username}, Sender: {sender.username}, Type: {notification_type_str}, Content: {notification_content_text}, URL: {notification_url}")
                send_notification_to_user(
                    recipient=recipient,
                    sender=sender,
                    notification_type=notification_type_str,
                    content=notification_content_text,
                    related_object=chat_message, # Передаем объект ChatMessage
                    custom_url=notification_url
                )
                print(f"DEBUG (Consumer - Notification Call): Notification request sent for {recipient.username}.")

            # Теперь возвращаем объект сообщения, чтобы его можно было использовать для group_send в receive
            return chat_message

    @database_sync_to_async
    def save_message(self, sender, chat_instance, MessageModel, content, attachments_data):
        with transaction.atomic():
            if isinstance(chat_instance, ChatRoom):
                message = MessageModel.objects.create(
                    chat_room=chat_instance,
                    sender=sender,
                    content=content,
                    is_edited=False
                )
            elif isinstance(chat_instance, GroupChat):
                message = MessageModel.objects.create(
                    group_chat=chat_instance,
                    sender=sender,
                    content=content,
                    is_edited=False
                )
            else:
                raise ValueError("Неизвестный тип чата для сохранения сообщения.")

            # Если attachments_data переданы, значит, сообщение было отправлено через AJAX/HTTP POST
            # и вложения уже сохранены в views.py. Нам их повторно сохранять тут не нужно.
            # Если же message_type == 'chat_message' в receive, и attachments_data пуст,
            # но мы захотим отправлять вложения через WS, то логика здесь будет другая.
            # Пока предполагаем, что вложения всегда через HTTP POST.

            return message

    @database_sync_to_async
    def get_user_avatar_url(self, user):
        if hasattr(user, 'profile') and user.profile.avatar:
            return user.profile.avatar.url
        return settings.STATIC_URL + 'images/default_avatar.png'

    @database_sync_to_async
    def add_reader_to_message(self, chat_message, reader_user):
        chat_message.read_by.add(reader_user)

    @database_sync_to_async
    def add_reader_to_message_and_check(self, message_id, reader_user, MessageModel):
        try:
            message = MessageModel.objects.get(id=message_id)
            if message.sender != reader_user and reader_user not in message.read_by.all():
                message.read_by.add(reader_user)
                return True
            return False
        except MessageModel.DoesNotExist:
            return False

    @database_sync_to_async
    def get_message_read_count(self, chat_message):
        return chat_message.read_by.count()

    @database_sync_to_async
    def get_message_read_count_by_id(self, message_id, MessageModel):
        try:
            message = MessageModel.objects.get(id=message_id)
            return message.read_by.count()
        except MessageModel.DoesNotExist:
            return 0

    @database_sync_to_async
    def mark_and_notify_messages_as_read(self, user, chat_instance, MessageModel, room_group_name):
        from asgiref.sync import async_to_sync

        if isinstance(chat_instance, ChatRoom):
            messages_to_mark = MessageModel.objects.filter(
                chat_room=chat_instance
            ).exclude(sender=user).exclude(read_by=user).select_related('sender')
        elif isinstance(chat_instance, GroupChat):
            messages_to_mark = MessageModel.objects.filter(
                group_chat=chat_instance
            ).exclude(sender=user).exclude(read_by=user).select_related('sender')
        else:
            return # Неизвестный тип чата

        notifications_to_send = []
        for msg in list(messages_to_mark):
            msg.read_by.add(user)

            read_count = msg.read_by.count()

            notifications_to_send.append({
                'type': 'read_receipt_notification',
                'message_id': str(msg.id),
                'reader_id': str(user.id),
                'read_count': read_count
            })

        channel_layer = self.channel_layer
        # Имя группы здесь также должно быть определено на основе self.room_type и self.room_id
        # Это должно быть `self.room_group_name` из connect()
        for notification in notifications_to_send:
            async_to_sync(channel_layer.group_send)(
                room_group_name, # Используем уже определенное имя группы
                notification
            )