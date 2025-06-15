from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/posts/', views.get_posts_ajax, name='get_posts_ajax'),

    path('create/', views.create_post_page, name='create_post_page'), 
    path('edit/<int:pk>/', views.edit_post_page, name='edit_post_page'), 

    path('post/create_submit/', views.post_create, name='post_create_submit'), 
    path('post/<int:pk>/edit_submit/', views.post_edit, name='post_edit_submit'), 

    path('post/<int:pk>/delete/', views.post_delete, name='post_delete'),



    path('post/<int:pk>/like/', views.post_like, name='post_like'),
    path('post/<int:pk>/dislike/', views.post_dislike, name='post_dislike'),
    path('post/<int:pk>/repost/', views.post_repost, name='post_repost'),
    path('post/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'), 
    path('post/<int:post_id>/reposts/ajax/', views.get_post_reposts_list, name='get_post_reposts_list'),


]