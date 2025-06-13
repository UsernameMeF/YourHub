# community/forms.py
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
        # Дополнительная проверка на уникальность названия, если нужно более сложное поведение,
        # чем стандартный unique=True в модели. Пока достаточно уникальности на уровне модели.
        name = self.cleaned_data['name']
        # Можно добавить проверку на минимальную длину или запрещенные символы
        return name

# Новая форма для редактирования сообщества
class CommunityUpdateForm(forms.ModelForm):
    class Meta:
        model = Community
        # В этой форме можно редактировать описание.
        # Название сообщества 'name' сделаем readonly, если требуется.
        # Если название должно быть редактируемым, просто включите 'name' в fields.
        fields = ['name', 'description'] 
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Название сообщества', 'readonly': 'readonly'}), # Название пока readonly
            'description': forms.Textarea(attrs={'placeholder': 'Краткое описание вашего сообщества'}),
        }
        labels = {
            'name': 'Название',
            'description': 'Описание',
        }
        help_texts = {
            'name': 'Название сообщества нельзя изменить после создания.', # Или изменить, если сделаем его редактируемым
            'description': 'Обновите описание вашего сообщества.',
        }



# НОВЫЕ ФОРМЫ ДЛЯ ПОСТОВ СООБЩЕСТВ И КОММЕНТАРИЕВ


class CommunityPostForm(forms.ModelForm):
    """
    Форма для создания новой публикации в сообществе.
    """
    class Meta:
        model = CommunityPost
        fields = ['title', 'content'] 
        widgets = {
            'title': forms.TextInput(attrs={ # <-- ДОБАВЛЕНО
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