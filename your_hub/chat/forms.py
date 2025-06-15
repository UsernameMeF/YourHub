from django import forms
from django.contrib.auth import get_user_model
from .models import GroupChat

User = get_user_model()

class GroupChatCreateForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        label="Назва групи",
        widget=forms.TextInput(attrs={'placeholder': 'Назва групового чату'})
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Короткий опис групи (необов\'язково)'}),
        label="Опис групи (необов'язково)",
        required=False
    )

    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Оберіть учасників",
        help_text="Оберіть користувачів, яких ви хочете додати до групи."
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
            raise forms.ValidationError("Для створення групового чату необхідно обрати щонайменше одного іншого користувача.")
        return participants