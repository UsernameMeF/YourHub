# SOCIAL_NETWORK/your_hub/core/forms.py

from django import forms
from .models import Post, Comment # Импортируем вашу модель Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        # УДАЛИТЕ 'images' ОТСЮДА
        fields = ['title', 'content'] # Только поля, которые напрямую относятся к Post
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Заголовок поста'}),
            'content': forms.Textarea(attrs={'placeholder': 'Что у вас на уме?', 'rows': 5}),
        }

# Добавим форму для каждого отдельного вложения (хотя это не всегда используется напрямую)
# Это скорее для Django FormSets, но пока нам не нужно напрямую создавать FormSet
# Это может быть полезно для валидации отдельных файлов.
class PostAttachmentForm(forms.Form):
    image = forms.ImageField(label="Изображение", required=False) # required=False, если вы не требуете изображение для каждого вложения

# Также убедимся, что у вас есть формы для удаления и комментариев, как вы упоминали в base.html
class PostDeleteForm(forms.Form):
    # Эта форма может быть пустой, так как подтверждение идет через hidden input и ID поста в URL
    pass

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'placeholder': 'Напишите комментарий...', 'rows': 3}),
        }