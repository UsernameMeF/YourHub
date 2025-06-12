from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # --- УНИВЕРСАЛЬНЫЕ МАРШРУТЫ ДЛЯ AJAX-ОПЕРАЦИЙ С СООБЩЕНИЯМИ (ДОЛЖНЫ БЫТЬ ВЫШЕ!) ---
    path('<str:room_type>/<int:room_id>/upload_attachment/', views.upload_attachment, name='upload_attachment_universal'),
    path('<str:room_type>/<int:room_id>/load_more_messages/', views.load_more_messages, name='load_more_messages_universal'),
    path('<str:room_type>/<int:room_id>/edit_message/<int:message_id>/', views.edit_message, name='edit_message_universal'),
    path('<str:room_type>/<int:room_id>/delete_message/<int:message_id>/', views.delete_message, name='delete_message_universal'),

    # --- Маршруты для СТРАНИЦ ЧАТОВ и их создания (теперь ниже универсальных) ---
    path('', views.chat_list_view, name='chat_list'), # Список чатов
    path('private/<int:room_id>/', views.chat_room_view, name='chat_room'), # Приватный чат (e.g., /chat/private/123/)
    path('start_chat/<int:other_user_id>/', views.get_or_create_private_chat, name='start_private_chat'), # Создание приватного чата

    # Группы
    path('group/create/', views.create_group_chat_view, name='create_group_chat'),
    path('group/create_ajax/', views.create_group_chat_ajax, name='create_group_chat_ajax'), # Создание группы через AJAX
    path('group/room/<int:group_chat_id>/', views.group_chat_room_view, name='group_chat_room'), # Страница группового чата (e.g., /chat/group/room/123/)
]
