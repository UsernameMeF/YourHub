from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_list_view, name='chat_list'),
    path('<int:room_id>/', views.chat_room_view, name='chat_room'),
    path('start_chat/<int:other_user_id>/', views.get_or_create_private_chat, name='start_private_chat'),
    path('upload_attachment/', views.upload_attachment, name='upload_attachment'),
    path('<int:room_id>/load_more_messages/', views.load_more_messages, name='load_more_messages'),
    path('<int:room_id>/edit_message/<int:message_id>/', views.edit_message, name='edit_message'),
    path('<int:room_id>/delete_message/<int:message_id>/', views.delete_message, name='delete_message'),
]