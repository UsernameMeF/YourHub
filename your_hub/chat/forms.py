from django import forms
from django.contrib.auth import get_user_model
from .models import GroupChat

User = get_user_model()

class GroupChatCreateForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        label="Название группы",
        widget=forms.TextInput(attrs={'placeholder': 'Название группового чата'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Краткое описание группы (необязательно)'}),
        label="Описание группы (необязательно)",
        required=False 
    )

    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Выберите участников",
        help_text="Выберите пользователей, которых вы хотите добавить в группу."
    )

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        if self.request_user:
            self.fields['participants'].queryset = User.objects.exclude(id=self.request_user.id).order_by('username')

    def clean_participants(self):
        participants = self.cleaned_data['participants']
        if self.request_user:
            if self.request_user not in participants:
                participants = list(participants) + [self.request_user]
        if len(participants) < 2:
            raise forms.ValidationError("Для создания группового чата необходимо выбрать как минимум одного другого пользователя.")
        return participants