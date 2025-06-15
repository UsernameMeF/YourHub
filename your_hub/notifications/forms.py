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
            'notification_sound': 'Звук сповіщення', # Translated
            'volume': 'Гучність звуку', # Translated
            'receive_messages_notifications': 'Особисті повідомлення', # Translated
            'receive_group_messages_notifications': 'Повідомлення в групах', # Translated
            'receive_friend_requests_notifications': 'Запити в друзі', # Translated
            'receive_approved_friend_requests_notifications': 'Схвалені запити в друзі', # Translated
            'receive_comments_notifications': 'Коментарі', # Translated
            'receive_likes_notifications': 'Вподобання', # Translated
            'receive_reposts_notifications': 'Репости', # Translated
            'receive_follows_notifications': 'Підписки', # Translated
            'do_not_disturb': 'Не турбувати (вимкнути всі звуки сповіщень)', # Translated
        }