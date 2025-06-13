# community/urls.py
from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    path('create/', views.community_create_view, name='community_create'),
    path('<int:pk>/', views.community_detail_view, name='community_detail'),
    path('<int:pk>/toggle_membership/', views.community_toggle_membership, name='community_toggle_membership'),
    path('my/', views.user_communities_view, name='user_communities'),

    # URL для поиска сообществ
    path('find/', views.community_search_view, name='community_search'),
    
    # URL-ы для постов сообщества
    path('<int:pk>/posts/create/', views.community_post_create_view, name='community_post_create'),
    path('<int:pk>/posts/<int:post_pk>/', views.community_post_detail_view, name='community_post_detail'),

    # URL-ы для лайков/дизлайков/репостов/комментариев к постам сообществ
    path('<int:pk>/posts/<int:post_pk>/like/', views.community_post_like, name='community_post_like'),
    path('<int:pk>/posts/<int:post_pk>/dislike/', views.community_post_dislike, name='community_post_dislike'),
    path('<int:pk>/posts/<int:post_pk>/repost/', views.community_post_repost, name='community_post_repost'),
    path('<int:pk>/posts/<int:post_pk>/comment/', views.community_add_comment, name='community_add_comment'),

    # НОВЫЕ URL-Ы
    path('<int:pk>/posts/<int:post_pk>/reposts/ajax/', views.community_post_reposts_ajax, name='community_post_reposts_ajax'),
    path('<int:pk>/posts/<int:post_pk>/delete/ajax/', views.community_post_delete_ajax, name='community_post_delete_ajax'),

    path('<int:pk>/edit/', views.community_edit_view, name='community_edit'),
    path('<int:pk>/delete/', views.community_delete_view, name='community_delete'),
]
