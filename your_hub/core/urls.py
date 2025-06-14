# SOCIAL_NETWORK/your_hub/core/urls.py

from django.urls import path
from . import views

app_name = 'core' # << Убедитесь, что это установлено для namespace

urlpatterns = [
    path('', views.index, name='index'),
    path('api/posts/', views.get_posts_ajax, name='get_posts_ajax'),
    # НОВЫЙ URL для получения деталей конкретного поста (для JS-загрузки в модалку)

    # Новые URL-пути для отдельных страниц создания/редактирования постов
    path('create/', views.create_post_page, name='create_post_page'), # URL для страницы создания
    path('edit/<int:pk>/', views.edit_post_page, name='edit_post_page'), # URL для страницы редактирования

    path('post/create_submit/', views.post_create, name='post_create_submit'), # Переименовал, чтобы не путать
    path('post/<int:pk>/edit_submit/', views.post_edit, name='post_edit_submit'), # Переименовал
    # URL для удаления поста (остался AJAX)
    path('post/<int:pk>/delete/', views.post_delete, name='post_delete'),


    # URL для действий с постами
    path('post/<int:pk>/like/', views.post_like, name='post_like'), # Убедитесь, что эти views существуют
    path('post/<int:pk>/dislike/', views.post_dislike, name='post_dislike'),
    path('post/<int:pk>/repost/', views.post_repost, name='post_repost'),
    path('post/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'), # Детальная страница поста, если она нужна
    path('post/<int:post_id>/reposts/ajax/', views.get_post_reposts_list, name='get_post_reposts_list'),


]