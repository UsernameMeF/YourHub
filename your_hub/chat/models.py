from django.db import models
from django.conf import settings
from django.utils.text import slugify
import uuid
import os

# Create your models here.

def group_chat_attachment_path(instance, filename):
    """Визначає шлях для завантаження вкладень групового чату.""" # Translated
    group_chat_id = instance.message.group_chat.id
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_{slugify(name)}{ext}"
    return f"group_chats/{group_chat_id}/attachments/{unique_filename}"


def group_chat_thumbnail_path(instance, filename):
    """Визначає шлях для завантаження мініатюр вкладень групового чату.""" # Translated
    group_chat_id = instance.message.group_chat.id
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_thumbnail_{slugify(name)}{ext}"
    return f"group_chats/{group_chat_id}/thumbnails/{unique_filename}"


def chat_attachment_path(instance, filename):

    chat_room_id = instance.message.chat_room.id
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_{slugify(name)}{ext}"
    
    return f"chat_attachments/{chat_room_id}/{unique_filename}"


def chat_thumbnail_path(instance, filename):

    chat_room_id = instance.message.chat_room.id
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_thumbnail_{slugify(name)}{ext}"

    return f"chat_attachments/{chat_room_id}/thumbnails/{unique_filename}"


class ChatRoom(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.pk:
            return f"Чат між {', '.join(str(user) for user in self.participants.all())}" # Translated
        return "Новий чат" # Translated


class ChatMessage(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='read_messages', blank=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Від {self.sender} о {self.timestamp.strftime('%d.%d.%Y %H:%M')}: {self.content[:50]}..." # Translated


class ChatAttachment(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=chat_attachment_path)
    file_type = models.CharField(max_length=10, choices=[
        ('image', 'Зображення'), # Translated
        ('video', 'Відео'), # Translated
        ('document', 'Документ'), # Translated
    ])
    thumbnail = models.ImageField(upload_to='chat_thumbnails/', blank=True, null=True)
    original_filename = models.CharField(max_length=255)

    def __str__(self):
        return f"Вкладення до повідомлення {self.message.id}: {self.original_filename}" # Translated

    def delete(self, *args, **kwargs):
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        if self.thumbnail:
            if os.path.isfile(self.thumbnail.path):
                os.remove(self.thumbnail.path)

        super().delete(*args, **kwargs)



class GroupChat(models.Model):
    """Модель для представлення групового чату.""" # Translated
    name = models.CharField(max_length=255, verbose_name="Назва групи") # Translated
    # Участники группового чата
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='group_chats_participated')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_group_chats')
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, verbose_name="Опис групи") # Translated

    class Meta:
        verbose_name = "Груповий чат" # Translated
        verbose_name_plural = "Групові чати" # Translated

    def __str__(self):
        return f"Група: {self.name}" # Translated

class GroupChatMessage(models.Model):
    """Модель для повідомлень у груповому чаті.""" # Translated
    group_chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='read_group_messages', blank=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        verbose_name = "Повідомлення групового чату" # Translated
        verbose_name_plural = "Повідомлення групових чатів" # Translated

    def __str__(self):
        return f"Група '{self.group_chat.name}' | Від {self.sender}: {self.content[:50]}..." # Translated


class GroupChatAttachment(models.Model):
    """Модель для вкладень у повідомленнях групового чату.""" # Translated
    message = models.ForeignKey(GroupChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=group_chat_attachment_path)
    file_type = models.CharField(max_length=10, choices=[
        ('image', 'Зображення'), # Translated
        ('video', 'Відео'), # Translated
        ('document', 'Документ'), # Translated
    ])
    thumbnail = models.ImageField(upload_to=group_chat_thumbnail_path, blank=True, null=True)
    original_filename = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Вкладення групового чату" # Translated
        verbose_name_plural = "Вкладення групових чатів" # Translated

    def __str__(self):
        return f"Вкладення до повідомлення групи {self.message.id}: {self.original_filename}" # Translated

    def delete(self, *args, **kwargs):
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        if self.thumbnail:
            if os.path.isfile(self.thumbnail.path):
                os.remove(self.thumbnail.path)
        super().delete(*args, **kwargs)