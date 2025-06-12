from django.db import models
from django.conf import settings
from django.utils.text import slugify
import uuid
import os

# Create your models here.

def group_chat_attachment_path(instance, filename):
    """Определяет путь для загрузки вложений группового чата."""
    # instance.message здесь будет GroupChatMessage
    group_chat_id = instance.message.group_chat.id
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_{slugify(name)}{ext}"
    return f"group_chats/{group_chat_id}/attachments/{unique_filename}"


def group_chat_thumbnail_path(instance, filename):
    """Определяет путь для загрузки миниатюр вложений группового чата."""
    # instance.message здесь будет GroupChatMessage
    group_chat_id = instance.message.group_chat.id
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_thumbnail_{slugify(name)}{ext}"
    return f"group_chats/{group_chat_id}/thumbnails/{unique_filename}"


def chat_attachment_path(instance, filename):

    chat_room_id = instance.message.chat_room.id
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_{slugify(name)}{ext}"
    
    return f"chats/{chat_room_id}/{unique_filename}"


def chat_thumbnail_path(instance, filename):

    chat_room_id = instance.message.chat_room.id
    name, ext = os.path.splitext(filename)
    unique_filename = f"{uuid.uuid4().hex}_thumbnail_{slugify(name)}{ext}"

    return f"chats/{chat_room_id}/thumbnails/{unique_filename}"


class ChatRoom(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.pk:
            return f"Чат между {', '.join(str(user) for user in self.participants.all())}"
        return "Новый чат" # Если ещё не существует


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
        return f"От {self.sender} в {self.timestamp.strftime('%d.%d.%Y %H:%M')}: {self.content[:50]}..."


class ChatAttachment(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='chat_attachments/')
    file_type = models.CharField(max_length=10, choices=[
        ('image', 'Изображение'),
        ('video', 'Видео'),
        ('document', 'Документ'),
    ])
    thumbnail = models.ImageField(upload_to='chat_thumbnails/', blank=True, null=True)
    original_filename = models.CharField(max_length=255)

    def __str__(self):
        return f"Вложение к сообщению {self.message.id}: {self.original_filename}"

    def delete(self, *args, **kwargs):
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        if self.thumbnail:
            if os.path.isfile(self.thumbnail.path):
                os.remove(self.thumbnail.path)

        super().delete(*args, **kwargs)


# --- Новые Модели для Групповых Чатов ---

class GroupChat(models.Model):
    """Модель для представления группового чата."""
    name = models.CharField(max_length=255, verbose_name="Название группы")
    # Участники группового чата
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='group_chats_participated')
    # Владелец группы (тот, кто ее создал), может быть null, если пользователь удален
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_group_chats')
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, verbose_name="Описание группы")
    # Можно добавить поле для аватара группы и т.п.

    class Meta:
        verbose_name = "Групповой чат"
        verbose_name_plural = "Групповые чаты"

    def __str__(self):
        return f"Группа: {self.name}"

class GroupChatMessage(models.Model):
    """Модель для сообщений в групповом чате."""
    group_chat = models.ForeignKey(GroupChat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='read_group_messages', blank=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp'] 
        verbose_name = "Сообщение группового чата"
        verbose_name_plural = "Сообщения групповых чатов"

    def __str__(self):
        return f"Группа '{self.group_chat.name}' | От {self.sender}: {self.content[:50]}..."


class GroupChatAttachment(models.Model):
    """Модель для вложений в сообщениях группового чата."""
    message = models.ForeignKey(GroupChatMessage, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=group_chat_attachment_path)
    file_type = models.CharField(max_length=10, choices=[
        ('image', 'Изображение'),
        ('video', 'Видео'),
        ('document', 'Документ'),
    ])
    thumbnail = models.ImageField(upload_to=group_chat_thumbnail_path, blank=True, null=True)
    original_filename = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Вложение группового чата"
        verbose_name_plural = "Вложения групповых чатов"

    def __str__(self):
        return f"Вложение к сообщению группы {self.message.id}: {self.original_filename}"

    def delete(self, *args, **kwargs):
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        if self.thumbnail:
            if os.path.isfile(self.thumbnail.path):
                os.remove(self.thumbnail.path)
        super().delete(*args, **kwargs)
