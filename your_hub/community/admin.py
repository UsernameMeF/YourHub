from django.contrib import admin
from .models import Community, CommunityMembership, CommunityPost, CommunityComment

@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator', 'created_at', 'members_count_display')
    search_fields = ('name', 'description', 'creator__username')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
    
    def members_count_display(self, obj):
        return obj.members.count()
    members_count_display.short_description = "Кількість учасників" # Translated


@admin.register(CommunityMembership)
class CommunityMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'community', 'date_joined', 'is_admin')
    list_filter = ('date_joined', 'is_admin', 'community')
    search_fields = ('user__username', 'community__name')
    readonly_fields = ('date_joined',)
    raw_id_fields = ('user', 'community')


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ('community', 'posted_by', 'content_snippet', 'created_at', 'total_likes', 'total_dislikes', 'views_count', 'is_edited')
    list_filter = ('created_at', 'is_edited', 'community')
    search_fields = ('community__name', 'posted_by__username', 'content')
    readonly_fields = ('created_at', 'views_count')
    inlines = []
    
    def content_snippet(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_snippet.short_description = "Вміст (фрагмент)" # Translated


@admin.register(CommunityComment)
class CommunityCommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'author', 'text_snippet', 'created_at')
    list_filter = ('created_at', 'post__community')
    search_fields = ('author__username', 'text', 'post__content')
    readonly_fields = ('created_at',)
    raw_id_fields = ('post', 'author')

    def text_snippet(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_snippet.short_description = "Текст (фрагмент)" # Translated