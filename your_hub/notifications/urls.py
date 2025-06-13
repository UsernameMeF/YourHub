from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('settings/', views.NotificationSettingsView.as_view(), name='settings'),
    path('', views.NotificationListView.as_view(), name='list'),
    path('api/settings/', views.UserNotificationSettingsAPIView.as_view(), name='api_settings'),
    path('api/recent/', views.RecentNotificationsAPIView.as_view(), name='api_recent'), # API для последних уведомлений
    path('api/mark-read/<int:notification_id>/', views.MarkNotificationAsReadAPIView.as_view(), name='api_mark_read'),
    path('api/unread-count/', views.UnreadNotificationCountAPIView.as_view(), name='api_unread_count'), # API для счетчика
    path('api/notification/<int:notification_id>/', views.NotificationDetailAPIView.as_view(), name='api_notification_detail'),
]