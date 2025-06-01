# SOCIAL_NETWORK/your_hub/core/admin.py

from django.contrib import admin
from django.db.models import Count 
from .models import Post, PostAttachment, Comment 

# Inline для PostAttachment
class PostAttachmentInline(admin.TabularInline): 
    model = PostAttachment
    extra = 1 
    max_num = 5 # Ограничение на 5 вложений
    fields = ['image'] 

# Inline для Comment
# Мы можем создать inline для комментариев, если хотим видеть их в форме поста
# Но если мы не хотим, чтобы их можно было создавать через админку вообще, то этот inline тоже не нужен,
# и модель Comment не должна регистрироваться отдельно.
# class CommentInline(admin.TabularInline):
#     model = Comment
#     extra = 0 # Не добавлять пустые формы по умолчанию
#     readonly_fields = ('author', 'created_at',) # Возможно, сделать их только для чтения
#     fields = ('text', 'author', 'created_at',)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'created_at', 'views_count', 'total_likes', 'total_dislikes', 'total_reposts', 'total_comments')
    list_filter = ('created_at', 'author')
    search_fields = ('title', 'content', 'author__username')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    # Добавляем PostAttachmentInline к модели Post
    inlines = [PostAttachmentInline] # <--- Вложения будут доступны только через форму поста
    # Если вы хотите видеть комментарии в админке поста, но не создавать их как отдельные сущности,
    # можете добавить CommentInline сюда:
    # inlines = [PostAttachmentInline, CommentInline]

    fieldsets = (
        (None, {
            'fields': ('author', 'title', 'content', 'views_count') 
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _total_likes=Count('likes', distinct=True),
            _total_dislikes=Count('dislikes', distinct=True),
            _total_reposts=Count('reposts', distinct=True),
            _total_comments=Count('comments', distinct=True)
        )
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


#

# @admin.register(Comment)
# class CommentAdmin(admin.ModelAdmin):
#     list_display = ('text', 'author', 'post', 'created_at')
#     list_filter = ('created_at', 'author', 'post')
#     search_fields = ('text', 'author__username', 'post__title')
#     date_hierarchy = 'created_at'

# @admin.register(PostAttachment)
# class PostAttachmentAdmin(admin.ModelAdmin):
#     list_display = ('post', 'image')
#     list_filter = ('post',)
#     search_fields = ('post__title',)