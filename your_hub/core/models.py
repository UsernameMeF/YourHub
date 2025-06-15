from django.db import models
from django.conf import settings
from django.urls import reverse
import os
from django.utils import timezone
from django.utils.text import slugify
from django.core.validators import RegexValidator

def post_attachment_upload_to(instance, filename):
    user_id = instance.post.author.id if instance.post.pk else 'temp'
    post_id = instance.post.pk if instance.post.pk else 'temp'
    return os.path.join('posts_attachments', str(user_id), str(post_id), filename)

class Tag(models.Model):
    name = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_\u0400-\u04FF]+$',
                message="Ім'я тегу повинно містити лише літери (латинські/кирилиця), цифри та нижнє підкреслення." # Translated
            )
        ]
    )
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Тег" # Translated
        verbose_name_plural = "Теги" # Translated

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
            original_slug = self.slug
            count = 1
            while Tag.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('core:index') + f'?tag={self.slug}'


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts', verbose_name="Автор") # Translated
    title = models.CharField(max_length=255, verbose_name="Заголовок") # Translated
    content = models.TextField(verbose_name="Вміст допису") # Translated
    
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_posts', blank=True, verbose_name="Вподобання") # Translated
    dislikes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='disliked_posts', blank=True, verbose_name="Дизлайки") # Translated
    reposts = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='reposted_posts', blank=True, verbose_name="Репости") # Translated
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення") # Translated
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата оновлення") # Translated
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)
    
    views_count = models.PositiveIntegerField(default=0, verbose_name="Кількість переглядів") # Translated

    class Meta:
        verbose_name = "Допис" # Translated
        verbose_name_plural = "Дописи" # Translated
        ordering = ['-created_at'] 

    def __str__(self):
        return f"{self.title} від {self.author.username}" # Translated

    def get_absolute_url(self):
        return reverse('core:post_detail', args=[str(self.id)])

    @property
    def total_likes(self):
        return self.likes.count()

    @property
    def total_dislikes(self):
        return self.dislikes.count()

    @property
    def total_reposts(self):
        return self.reposts.count()

    @property
    def total_comments(self):
        return self.comments.count()


class PostAttachment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='attachments', verbose_name="Допис") # Translated
    image = models.ImageField(upload_to=post_attachment_upload_to, verbose_name="Зображення") # Translated

    class Meta:
        verbose_name = "Вкладення до допису" # Translated
        verbose_name_plural = "Вкладення до дописів" # Translated

    def __str__(self):
        return f"Вкладення для допису {self.post.id}" # Translated


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="Допис") # Translated
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments', verbose_name="Автор") # Translated
    text = models.TextField(verbose_name="Текст коментаря") # Translated
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата створення") # Translated

    class Meta:
        verbose_name = "Коментар" # Translated
        verbose_name_plural = "Коментарі" # Translated
        ordering = ['created_at'] 

    def __str__(self):
        return f"Коментар від {self.author.username} до допису {self.post.id}" # Translated