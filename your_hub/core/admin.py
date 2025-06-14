from django.contrib import admin
from django.db.models import Count
from .models import Post, PostAttachment, Comment, Tag 

# Inline для PostAttachment
class PostAttachmentInline(admin.TabularInline):
    model = PostAttachment
    extra = 1
    max_num = 5
    fields = ['image']

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'display_tags', 'created_at', 'views_count', 'total_likes', 'total_dislikes', 'total_reposts', 'total_comments') # <--- Добавили 'display_tags'
    list_filter = ('created_at', 'author', 'tags') # <--- Добавили 'tags' в фильтр
    search_fields = ('title', 'content', 'author__username', 'tags__name') # <--- Добавили 'tags__name' в поиск
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    # Добавляем PostAttachmentInline к модели Post
    inlines = [PostAttachmentInline]

    fieldsets = (
        (None, {
            'fields': ('author', 'title', 'content', 'views_count', 'tags') # <--- Добавили 'tags' в fieldsets
        }),
    )

    # Метод для отображения тегов в list_display
    def display_tags(self, obj):
        return ", ".join([tag.name for tag in obj.tags.all()])
    display_tags.short_description = 'Теги'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _total_likes=Count('likes', distinct=True),
            _total_dislikes=Count('dislikes', distinct=True),
            _total_reposts=Count('reposts', distinct=True),
            _total_comments=Count('comments', distinct=True)
        ).prefetch_related('tags') # <--- Добавили prefetch_related('tags') для оптимизации запросов
        return queryset

    def total_likes(self, obj):
        return obj._total_likes
    total_likes.admin_order_field = '_total_likes'
    total_likes.short_description = 'Лайки'

    def total_dislikes(self, obj):
        return obj._total_dislikes
    total_dislikes.admin_order_field = '_total_dislikes'
    total_dislikes.short_description = 'Дизлайки'

    def total_reposts(self, obj):
        return obj._total_reposts
    total_reposts.admin_order_field = '_total_reposts'
    total_reposts.short_description = 'Репосты'

    def total_comments(self, obj):
        return obj._total_comments
    total_comments.admin_order_field = '_total_comments'
    total_comments.short_description = 'Комментарии'


# Регистрируем модель Tag в админке
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)} # Автоматическое заполнение slug на основе name
    ordering = ('name',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'author', 'post', 'created_at')
    list_filter = ('created_at', 'author', 'post')
    search_fields = ('text', 'author__username', 'post__title')
    date_hierarchy = 'created_at'

@admin.register(PostAttachment)
class PostAttachmentAdmin(admin.ModelAdmin):
    list_display = ('post', 'image')
    list_filter = ('post',)
    search_fields = ('post__title',)