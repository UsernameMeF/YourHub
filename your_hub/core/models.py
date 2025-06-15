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
                message="Имя тега должно содержать только буквы (латинские/кириллица), цифры и нижнее подчеркивание."
            )
        ]
    )
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

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
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts', verbose_name="Автор")
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    content = models.TextField(verbose_name="Содержимое поста")
    
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_posts', blank=True, verbose_name="Лайки")
    dislikes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='disliked_posts', blank=True, verbose_name="Дизлайки")
    reposts = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='reposted_posts', blank=True, verbose_name="Репосты")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)
    
    views_count = models.PositiveIntegerField(default=0, verbose_name="Количество просмотров")

    class Meta:
        verbose_name = "Пост"
        verbose_name_plural = "Посты"
        ordering = ['-created_at'] 

    def __str__(self):
        return f"{self.title} by {self.author.username}"

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
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='attachments', verbose_name="Пост")
    image = models.ImageField(upload_to=post_attachment_upload_to, verbose_name="Изображение")

    class Meta:
        verbose_name = "Вложение к посту"
        verbose_name_plural = "Вложения к постам"

    def __str__(self):
        return f"Attachment for Post {self.post.id}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="Пост")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments', verbose_name="Автор")
    text = models.TextField(verbose_name="Текст комментария")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['created_at'] 

    def __str__(self):
        return f"Comment by {self.author.username} on Post {self.post.id}"