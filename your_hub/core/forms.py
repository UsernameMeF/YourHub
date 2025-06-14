# SOCIAL_NETWORK/your_hub/core/forms.py

from django import forms
from .models import Post, Comment, Tag
import re

class PostForm(forms.ModelForm):

    tags_input = forms.CharField(
        max_length=500,
        required=False,
        label="Теги (например, #музыка #футбол)",
        help_text="Введите теги через пробел. Каждый тег должен начинаться с '#' и содержать только буквы, цифры и '_'. Максимум 10 пользовательских тегов."
    )

    class Meta:
        model = Post
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Заголовок поста'}),
            'content': forms.Textarea(attrs={'placeholder': 'Что у вас на уме?', 'rows': 5}),
        }
        
    def clean_tags_input(self):
        tags_string = self.cleaned_data.get('tags_input')
        cleaned_tags = []
        if tags_string:
            raw_tags = re.split(r'\s+', tags_string.strip())
            
            # Обновлено: регулярное выражение проверяет формат, но без #
            # Мы будем удалять # перед передачей в валидатор модели
            # и потом добавлять обратно для отображения
            tag_input_pattern = re.compile(r'^#[\w]+$') # Это для валидации ввода пользователя

            for tag_with_hash in raw_tags:
                if not tag_with_hash:
                    continue
                if not tag_input_pattern.match(tag_with_hash):
                    raise forms.ValidationError(
                        f"Тег '{tag_with_hash}' имеет некорректный формат. Каждый тег должен начинаться с '#' и содержать только буквы, цифры и нижнее подчеркивание, без пробелов внутри."
                    )
                # Удаляем '#' перед добавлением в cleaned_tags для дальнейшей обработки
                clean_tag_name = tag_with_hash[1:]
                # Добавляем тег в список без дубликатов (без учета регистра)
                if clean_tag_name.lower() not in [t.lower() for t in cleaned_tags]:
                    cleaned_tags.append(clean_tag_name)
            
            if len(cleaned_tags) > 10: # Ограничение на количество ПОЛЬЗОВАТЕЛЬСКИХ тегов
                raise forms.ValidationError("Вы можете добавить не более 10 пользовательских тегов.")
        
        return ' '.join(cleaned_tags) # Возвращаем очищенные теги (без #) обратно в строку, разделенные пробелами


class PostAttachmentForm(forms.Form):
    image = forms.ImageField(label="Изображение", required=False)

class PostDeleteForm(forms.Form):
    pass

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'placeholder': 'Напишите комментарий...', 'rows': 3}),
        }