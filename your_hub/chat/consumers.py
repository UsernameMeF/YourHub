import json 
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings 

from .models import ChatRoom, ChatMessage, ChatAttachment
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f"chat_{self.room_id}"

        self.user = self.scope['user']

        if self.user.is_authenticated:
            self.chat_room = await self.get_chat_room(self.room_id)
            if not self.chat_room or not await self.is_user_in_chat_room(self.user, self.chat_room):
                await self.close()
                return
        else:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # При подключении пользователя, помечаем все сообщения, предназначенные ему, как прочитанные
        # И отправляем уведомления об этом
        await self.mark_and_notify_messages_as_read(self.user, self.chat_room)


    async def disconnect(self, close_code):
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

            if message_content:
                chat_message = await self.save_message(self.user, self.chat_room, message_content)
                
                # Добавляем отправителя в список прочитавших (т.к. он сам свое сообщение "прочитал" при отправке)
                await self.add_reader_to_message(chat_message, self.user)

                sender_id = self.user.id
                sender_avatar_url = await self.get_user_avatar_url(self.user)

                # Получаем текущее количество прочитавших (для нового сообщения будет 1 - сам отправитель)
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
                        'message_id': str(chat_message.id), # Приводим к str для JS
                        'attachments': [],
                        'read_count': read_count, 
                        'is_edited': False, 
                    }
                )
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
                message_updated = await self.add_reader_to_message_and_check(message_id, self.user)
                
                if message_updated:
                    # После успешной отметки в БД, получаем обновленное количество прочитавших
                    updated_read_count = await self.get_message_read_count_by_id(message_id)

                    # Отправляем уведомление о прочтении всем в чате
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
            'new_content': event['new_content']
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event['message_id']
        }))


    @database_sync_to_async
    def get_chat_room(self, room_id):
        try:
            return ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def is_user_in_chat_room(self, user, chat_room):
        return chat_room.participants.filter(id=user.id).exists()

    @database_sync_to_async
    def save_message(self, sender, chat_room, content):
        return ChatMessage.objects.create(
            chat_room=chat_room,
            sender=sender,
            content=content,
            is_edited=False 
        )

    @database_sync_to_async
    def get_user_avatar_url(self, user):
        if hasattr(user, 'profile') and user.profile.avatar:
            return user.profile.avatar.url
        return settings.STATIC_URL + 'images/default_avatar.png' 


    @database_sync_to_async
    def add_reader_to_message(self, chat_message, reader_user):
        chat_message.read_by.add(reader_user)

    @database_sync_to_async
    def add_reader_to_message_and_check(self, message_id, reader_user):
        try:
            message = ChatMessage.objects.get(id=message_id)
            if message.sender != reader_user and reader_user not in message.read_by.all():
                message.read_by.add(reader_user)
                return True 
            return False 
        except ChatMessage.DoesNotExist:
            return False

    @database_sync_to_async
    def get_message_read_count(self, chat_message):
        return chat_message.read_by.count()


    @database_sync_to_async
    def get_message_read_count_by_id(self, message_id):
        try:
            message = ChatMessage.objects.get(id=message_id)
            return message.read_by.count()
        except ChatMessage.DoesNotExist:
            return 0


    @database_sync_to_async
    def mark_and_notify_messages_as_read(self, user, chat_room):
        from asgiref.sync import async_to_sync 

        messages_to_mark = ChatMessage.objects.filter(
            chat_room=chat_room
        ).exclude(sender=user).exclude(read_by=user).select_related('sender') 

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
        for notification in notifications_to_send:
            async_to_sync(channel_layer.group_send)(
                self.room_group_name,
                notification
            )