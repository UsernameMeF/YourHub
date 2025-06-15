from django import forms
from .models import Post, Comment, Tag
import re

class PostForm(forms.ModelForm):

    tags_input = forms.CharField(
        max_length=500,
        required=False,
        label="Теги (наприклад, #музика #футбол)", # Translated
        help_text="Введіть теги через пробіл. Кожен тег повинен починатися з '#' і містити лише літери, цифри та '_'. Максимум 10 власних тегів." # Translated
    )

    class Meta:
        model = Post
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Заголовок допису'}), # Translated
            'content': forms.Textarea(attrs={'placeholder': 'Що у вас на думці?', 'rows': 5}), # Translated
        }
        
    def clean_tags_input(self):
        tags_string = self.cleaned_data.get('tags_input')
        cleaned_tags = []
        if tags_string:
            raw_tags = re.split(r'\s+', tags_string.strip())
            
            tag_input_pattern = re.compile(r'^#[\w]+$')

            for tag_with_hash in raw_tags:
                if not tag_with_hash:
                    continue
                if not tag_input_pattern.match(tag_with_hash):
                    raise forms.ValidationError(
                        f"Тег '{tag_with_hash}' має некоректний формат. Кожен тег повинен починатися з '#' і містити лише літери, цифри та нижнє підкреслення, без пробілів всередині." # Translated
                    )
                clean_tag_name = tag_with_hash[1:]
                if clean_tag_name.lower() not in [t.lower() for t in cleaned_tags]:
                    cleaned_tags.append(clean_tag_name)
            
            if len(cleaned_tags) > 10:
                raise forms.ValidationError("Ви можете додати не більше 10 власних тегів.") # Translated
        
        return ' '.join(cleaned_tags)


class PostAttachmentForm(forms.Form):
    image = forms.ImageField(label="Зображення", required=False) # Translated

class PostDeleteForm(forms.Form):
    pass

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'placeholder': 'Напишіть коментар...', 'rows': 3}), # Translated
        }