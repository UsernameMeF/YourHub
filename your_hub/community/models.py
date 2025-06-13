# community/models.py
from django.db import models
from django.conf import settings 
import os 


class Community(models.Model):
    """
    Модель для представления сообщества по интересам.
    """
    name = models.CharField(
        max_length=100,
        unique=True, # Название сообщества должно быть уникальным
        verbose_name="Название сообщества"
    )
    description = models.TextField(
        blank=True, # Описание может быть необязательным
        verbose_name="Описание сообщества"
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Если создатель удален, сообщество остается, но creator становится NULL
        null=True, # Разрешаем NULL для creator
        related_name='created_communities',
        verbose_name="Создатель сообщества"
    )
    # Используем ManyToManyField для участников, через CommunityMembership для гибкости
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='CommunityMembership', # Указываем промежуточную модель
        related_name='joined_communities',
        verbose_name="Участники сообщества"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    

    class Meta:
        verbose_name = "Сообщество"
        verbose_name_plural = "Сообщества"
        ordering = ['-created_at'] # Сортировка по дате создания по умолчанию

    def __str__(self):
        return self.name

class CommunityMembership(models.Model):
    """
    Промежуточная модель для Many-to-Many отношения User-Community,
    позволяет добавить дополнительные поля (например, is_admin).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        verbose_name="Сообщество"
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата присоединения"
    )
    is_admin = models.BooleanField(
        default=False,
        verbose_name="Администратор сообщества"
    ) # Для будущей реализации модерации

    class Meta:
        unique_together = ('user', 'community') # Пользователь может быть участником сообщества только один раз
        verbose_name = "Членство в сообществе"
        verbose_name_plural = "Членства в сообществах"
        ordering = ['date_joined']

    def __str__(self):
        return f"{self.user.username} в {self.community.name}"


class CommunityPost(models.Model):
    """
    Модель для постов, публикуемых от имени сообщества.
    """
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name="Сообщество"
    )
    # Это поле будет хранить того, кто физически опубликовал пост из администраторов.
    # Но "автором" поста будет считаться само сообщество.
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # Если пользователь удален, пост остается, но posted_by становится NULL
        null=True,
        related_name='community_posts_published',
        verbose_name="Опубликовано пользователем"
    )
    title = models.CharField( # <-- ДОБАВЛЯЕМ ЭТО ПОЛЕ
        max_length=200, 
        blank=True, 
        verbose_name="Заголовок поста"
    )
    content = models.TextField(verbose_name="Содержимое поста")
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )
    is_edited = models.BooleanField(
        default=False,
        verbose_name="Отредактировано"
    )

    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Количество просмотров"
    )

    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='liked_community_posts',
        blank=True,
        verbose_name="Лайки"
    )
    dislikes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='disliked_community_posts',
        blank=True,
        verbose_name="Дизлайки"
    )
    reposts = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='reposted_community_posts',
        blank=True,
        verbose_name="Репосты"
    )

    class Meta:
        verbose_name = "Пост сообщества"
        verbose_name_plural = "Посты сообществ"
        ordering = ['-created_at'] # Сортировка по дате создания по умолчанию

    def __str__(self):
        return f"Пост от {self.community.name} ({self.id})"

    # --- ДОБАВЛЕНЫ СВОЙСТВА ---
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
        return self.comments.count() # Ссылка на related_name в CommunityComment

class CommunityComment(models.Model):
    """
    Модель для комментариев к постам сообществ.
    """
    post = models.ForeignKey(
        'CommunityPost', # Ссылка на CommunityPost
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Пост сообщества"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='community_comments',
        verbose_name="Автор комментария"
    )
    text = models.TextField(verbose_name="Текст комментария")
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    class Meta:
        verbose_name = "Комментарий к посту сообщества"
        verbose_name_plural = "Комментарии к постам сообществ"
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on Community Post {self.post.id}"