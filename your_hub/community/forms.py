from django import forms
from .models import Community, CommunityPost, CommunityComment

class CommunityCreationForm(forms.ModelForm):
    """
    Форма для створення нового співтовариства.
    """ # Translated
    class Meta:
        model = Community
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Назва спільноти'}), # Translated
            'description': forms.Textarea(attrs={'placeholder': 'Короткий опис спільноти (необов\'язково)', 'rows': 4}), # Translated
        }
        labels = {
            'name': 'Назва спільноти', # Translated
            'description': 'Опис спільноти (необов\'язково)', # Translated
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        return name

class CommunityUpdateForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ['name', 'description'] 
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Назва спільноти', 'readonly': 'readonly'}), # Translated
            'description': forms.Textarea(attrs={'placeholder': 'Короткий опис вашої спільноти'}), # Translated
        }
        labels = {
            'name': 'Назва', # Translated
            'description': 'Опис', # Translated
        }
        help_texts = {
            'name': 'Назву спільноти не можна змінити після створення.', # Translated
            'description': 'Оновіть опис вашої спільноти.', # Translated
        }


class CommunityPostForm(forms.ModelForm):
    """
    Форма для створення нової публікації у співтоваристві.
    """ # Translated
    class Meta:
        model = CommunityPost
        fields = ['title', 'content'] 
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Заголовок публікації', # Translated
                'class': 'community-post-title-input'
            }),
            'content': forms.Textarea(attrs={
                'placeholder': 'Що нового у спільноті?', # Translated
                'rows': 7, 
                'class': 'community-post-content-input' 
            }),
        }
        labels = {
            'content': 'Текст публікації', # Translated
        }


class CommunityCommentForm(forms.ModelForm):
    """
    Форма для додавання коментаря до допису спільноти.
    """ # Translated
    class Meta:
        model = CommunityComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'placeholder': 'Напишіть коментар...', # Translated
                'rows': 3,
                'class': 'community-comment-text-input'
            }),
        }
        labels = {
            'text': 'Ваш коментар', # Translated
        }