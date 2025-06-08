from django.contrib import admin
from .models import ChatRoom, ChatMessage, ChatAttachment 

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_participants', 'created_at')
    filter_horizontal = ('participants',) 
    search_fields = ('participants__username',) 

    def display_participants(self, obj):
        return ", ".join([user.username for user in obj.participants.all()])
    display_participants.short_description = "Участники"


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat_room', 'sender', 'timestamp', 'content_preview', 'is_edited')
    list_filter = ('chat_room', 'sender', 'timestamp', 'is_edited')
    search_fields = ('content', 'sender__username', 'chat_room__id')
    readonly_fields = ('timestamp',)
    raw_id_fields = ('chat_room', 'sender') 

    def content_preview(self, obj):
        return obj.content[:75] + '...' if len(obj.content) > 75 else obj.content
    content_preview.short_description = "Содержимое"


@admin.register(ChatAttachment)
class ChatAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'file_type', 'original_filename', 'file_link', 'thumbnail_link')
    list_filter = ('file_type',)
    search_fields = ('original_filename', 'message__content')
    readonly_fields = ('file_link', 'thumbnail_link', 'message', 'original_filename', 'file_type')

    def file_link(self, obj):
        if obj.file:
            return f'<a href="{obj.file.url}" target="_blank">{obj.file.name.split("/")[-1]}</a>'
        return "Нет файла"
    file_link.allow_tags = True
    file_link.short_description = "Файл"

    def thumbnail_link(self, obj):
        if obj.thumbnail:
            return f'<a href="{obj.thumbnail.url}" target="_blank"><img src="{obj.thumbnail.url}" width="50" height="50"/></a>'
        return "Нет миниатюры"
    thumbnail_link.allow_tags = True
    thumbnail_link.short_description = "Миниатюра"