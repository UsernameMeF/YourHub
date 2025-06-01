# SOCIAL_NETWORK/your_hub/core/models.py
from django.db import models
from django.conf import settings
from django.urls import reverse
import os
from django.utils import timezone # Добавлен импорт timezone

def post_attachment_upload_to(instance, filename):
    # Путь для сохранения вложений: media/posts_attachments/{user_id}/{post_id}/{filename}
    # Используем user_id из instance.post.author.id
    # post_id будет доступен после сохранения поста
    # Если пост еще не сохранен (нет pk), сохраним его во временную папку или используем 0
    # В идеале, после создания поста, нужно будет переместить файлы в правильную папку
    # или обновлять путь в PostAttachment. Это более сложная логика, пока делаем упрощенно
    user_id = instance.post.author.id if instance.post.pk else 'temp'
    post_id = instance.post.pk if instance.post.pk else 'temp'
    return os.path.join('posts_attachments', str(user_id), str(post_id), filename)

class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts', verbose_name="Автор")
    title = models.CharField(max_length=255, verbose_name="Заголовок")
    content = models.TextField(verbose_name="Содержимое поста")
    
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_posts', blank=True, verbose_name="Лайки")
    dislikes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='disliked_posts', blank=True, verbose_name="Дизлайки")
    reposts = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='reposted_posts', blank=True, verbose_name="Репосты")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    views_count = models.PositiveIntegerField(default=0, verbose_name="Количество просмотров")

    class Meta:
        verbose_name = "Пост"
        verbose_name_plural = "Посты"
        ordering = ['-created_at'] 

    def __str__(self):
        return f"{self.title} by {self.author.username}"

    def get_absolute_url(self):
        return reverse('post_detail', args=[str(self.id)])

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
    def total_comments(self): # Добавлено: Свойство для подсчета комментариев
        return self.comments.count()


class PostAttachment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='attachments', verbose_name="Пост")
    image = models.ImageField(upload_to=post_attachment_upload_to, verbose_name="Изображение")

    class Meta:
        verbose_name = "Вложение к посту"
        verbose_name_plural = "Вложения к постам"

    def __str__(self):
        return f"Attachment for Post {self.post.id}"


# НОВАЯ МОДЕЛЬ ДЛЯ КОММЕНТАРИЕВ
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name="Пост")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments', verbose_name="Автор")
    text = models.TextField(verbose_name="Текст комментария")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['created_at'] # Сортировка по умолчанию: старые сверху

    def __str__(self):
        return f"Comment by {self.author.username} on Post {self.post.id}"