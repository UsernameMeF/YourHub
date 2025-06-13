from django import forms
from .models import UserNotificationSettings

class UserNotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = UserNotificationSettings
        fields = [
            'notification_sound',
            'volume',
            'receive_messages_notifications',
            'receive_group_messages_notifications',
            'receive_friend_requests_notifications',
            'receive_approved_friend_requests_notifications',
            'receive_comments_notifications',
            'receive_likes_notifications',
            'receive_reposts_notifications',
            'receive_follows_notifications',
            'do_not_disturb',
        ]
        widgets = {
            'notification_sound': forms.Select(attrs={'class': 'form-select'}),
            'volume': forms.NumberInput(attrs={
                'type': 'range',
                'min': '0.0',
                'max': '1.0',
                'step': '0.05',
                'class': 'form-range-slider'
            }),
            'receive_messages_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_group_messages_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_friend_requests_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_approved_friend_requests_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_comments_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_likes_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_reposts_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receive_follows_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'do_not_disturb': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'notification_sound': 'Звук уведомления',
            'volume': 'Громкость звука',
            'receive_messages_notifications': 'Личные сообщения',
            'receive_group_messages_notifications': 'Сообщения в группах',
            'receive_friend_requests_notifications': 'Запросы в друзья',
            'receive_approved_friend_requests_notifications': 'Одобренные запросы в друзья',
            'receive_comments_notifications': 'Комментарии',
            'receive_likes_notifications': 'Лайки',
            'receive_reposts_notifications': 'Репосты',
            'receive_follows_notifications': 'Подписки',
            'do_not_disturb': 'Не беспокоить (отключить все звуки уведомлений)',
        }