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

    # URL для страницы управления друзьями (список друзей и запросы текущего пользователя)
    path('friends/', views.friends_list_view, name='friends_list'),

    # URL для отправки запроса на дружбу (принимает ID пользователя, которому отправляем)
    # Используется формами на странице профиля другого пользователя
    path('send_friend_request/<int:to_user_id>/', views.send_friend_request, name='send_friend_request'),

    path('remove_friend/<int:user_id>/', views.remove_friend, name='remove_friend'),

    # URL для принятия запроса на дружбу (принимает ID объекта Friendship)
    # Используется AJAX формами на странице friends_list
    path('accept_friend_request/<int:friendship_id>/', views.accept_friend_request, name='accept_friend_request'),

    # URL для отклонения запроса на дружбу (принимает ID объекта Friendship)
    # Используется AJAX формами на странице friends_list
    path('decline_friend_request/<int:friendship_id>/', views.decline_friend_request, name='decline_friend_request'),

    # URL для отмены отправленного запроса на дружбу (принимает ID объекта Friendship)
    # Используется AJAX формами на странице friends_list (или профиля получателя, если там будет такая кнопка)
    path('cancel_friend_request/<int:friendship_id>/', views.cancel_friend_request, name='cancel_friend_request'),

    # URL для подписки на пользователя (принимает ID пользователя, на которого подписываемся)
    # Используется формами на странице профиля другого пользователя
    path('follow/<int:user_id>/', views.follow_user, name='follow_user'),

    # URL для отписки от пользователя (принимает ID пользователя, от которого отписываемся)
    # Используется формами на странице профиля другого пользователя
    path('unfollow/<int:user_id>/', views.unfollow_user, name='unfollow_user'),

    path('set-status/', views.set_user_status, name='set_user_status'),
]