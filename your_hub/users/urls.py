from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.custom_logout_view, name='logout'),

    path('<int:user_id>', views.profile_view, name='user_profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),


    # --- URL для Друзей и Подписок ---

    path('friends/', views.friends_list_view, name='friends_list'),
    path('send_friend_request/<int:to_user_id>/', views.send_friend_request, name='send_friend_request'),
    path('remove_friend/<int:user_id>/', views.remove_friend, name='remove_friend'),
    path('accept_friend_request/<int:friendship_id>/', views.accept_friend_request, name='accept_friend_request'),
    path('decline_friend_request/<int:friendship_id>/', views.decline_friend_request, name='decline_friend_request'),
    path('cancel_friend_request/<int:friendship_id>/', views.cancel_friend_request, name='cancel_friend_request'),
    path('follow/<int:user_id>/', views.follow_user, name='follow_user'),
    path('unfollow/<int:user_id>/', views.unfollow_user, name='unfollow_user'),
    path('set-status/', views.set_user_status, name='set_user_status'),
]