from django.db import models
from django.conf import settings 
import os 


class Community(models.Model):
    """
    Модель для представлення спільноти за інтересами.
    """ # Translated
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Назва спільноти" # Translated
    )
    description = models.TextField(
        blank=True,
        verbose_name="Опис спільноти" # Translated
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_communities',
        verbose_name="Творець спільноти" # Translated
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='CommunityMembership',
        related_name='joined_communities',
        verbose_name="Учасники спільноти" # Translated
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата створення" # Translated
    )
    
    class Meta:
        verbose_name = "Спільнота" # Translated
        verbose_name_plural = "Спільноти" # Translated
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class CommunityMembership(models.Model):
    """
    Проміжна модель для зв'язку Many-to-Many User-Community,
    дозволяє додати додаткові поля (наприклад, is_admin).
    """ # Translated
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Користувач" # Translated
    )
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        verbose_name="Спільнота" # Translated
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата приєднання" # Translated
    )
    is_admin = models.BooleanField(
        default=False,
        verbose_name="Адміністратор спільноти" # Translated
    )

    class Meta:
        unique_together = ('user', 'community')
        verbose_name = "Членство у спільноті" # Translated
        verbose_name_plural = "Членства у спільнотах" # Translated
        ordering = ['date_joined']

    def __str__(self):
        return f"{self.user.username} у {self.community.name}" # Translated


class CommunityPost(models.Model):
    """
    Модель для постів, що публікуються від імені спільноти.
    """ # Translated
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name="Спільнота" # Translated
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='community_posts_published',
        verbose_name="Опубліковано користувачем" # Translated
    )
    title = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name="Заголовок посту" # Translated
    )
    content = models.TextField(verbose_name="Вміст посту") # Translated
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата створення" # Translated
    )
    is_edited = models.BooleanField(
        default=False,
        verbose_name="Відредаговано" # Translated
    )

    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Кількість переглядів" # Translated
    )

    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='liked_community_posts',
        blank=True,
        verbose_name="Вподобання" # Translated
    )
    dislikes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='disliked_community_posts',
        blank=True,
        verbose_name="Дизлайки" # Translated
    )
    reposts = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='reposted_community_posts',
        blank=True,
        verbose_name="Репости" # Translated
    )

    class Meta:
        verbose_name = "Пост спільноти" # Translated
        verbose_name_plural = "Пости спільнот" # Translated
        ordering = ['-created_at']

    def __str__(self):
        return f"Пост від {self.community.name} ({self.id})" # Translated

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

class CommunityComment(models.Model):
    """
    Модель для коментарів до постів спільнот.
    """ # Translated
    post = models.ForeignKey(
        'CommunityPost',
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name="Пост спільноти" # Translated
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='community_comments',
        verbose_name="Автор коментаря" # Translated
    )
    text = models.TextField(verbose_name="Текст коментаря") # Translated
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата створення" # Translated
    )

    class Meta:
        verbose_name = "Коментар до посту спільноти" # Translated
        verbose_name_plural = "Коментарі до постів спільнот" # Translated
        ordering = ['created_at']

    def __str__(self):
        return f"Коментар від {self.author.username} до посту спільноти {self.post.id}" # Translated