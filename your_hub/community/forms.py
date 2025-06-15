from django import forms
from .models import Community, CommunityPost, CommunityComment

class CommunityCreationForm(forms.ModelForm):
    """
    Форма для создания нового сообщества.
    """
    class Meta:
        model = Community
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Название сообщества'}),
            'description': forms.Textarea(attrs={'placeholder': 'Краткое описание сообщества (необязательно)', 'rows': 4}),
        }
        labels = {
            'name': 'Название сообщества',
            'description': 'Описание сообщества (необязательно)',
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        return name

class CommunityUpdateForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ['name', 'description'] 
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Название сообщества', 'readonly': 'readonly'}),
            'description': forms.Textarea(attrs={'placeholder': 'Краткое описание вашего сообщества'}),
        }
        labels = {
            'name': 'Название',
            'description': 'Описание',
        }
        help_texts = {
            'name': 'Название сообщества нельзя изменить после создания.',
            'description': 'Обновите описание вашего сообщества.',
        }


class CommunityPostForm(forms.ModelForm):
    """
    Форма для создания новой публикации в сообществе.
    """
    class Meta:
        model = CommunityPost
        fields = ['title', 'content'] 
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Заголовок публикации',
                'class': 'community-post-title-input'
            }),
            'content': forms.Textarea(attrs={
                'placeholder': 'Что нового в сообществе?',
                'rows': 7, 
                'class': 'community-post-content-input' 
            }),
        }
        labels = {
            'content': 'Текст публикации',
        }


class CommunityCommentForm(forms.ModelForm):
    """
    Форма для добавления комментария к посту сообщества.
    """
    class Meta:
        model = CommunityComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'placeholder': 'Напишите комментарий...',
                'rows': 3,
                'class': 'community-comment-text-input'
            }),
        }
        labels = {
            'text': 'Ваш комментарий',
        }