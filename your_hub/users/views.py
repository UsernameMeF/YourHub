from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.contrib import messages

from core.models import Post
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from .models import Profile, Friendship, Follow
from django.conf import settings
from django.contrib.auth.views import LogoutView as BaseLogoutView
from django.views.generic import FormView
from django.utils import timezone
from django.http import JsonResponse 
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.urls import reverse
from notifications.utils import send_notification_to_user

ONLINE_THRESHOLD_MINUTES = 5 

def register_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('users:login')
        else:
            pass

    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if hasattr(request.user, 'profile'):
                request.user.profile.last_activity = timezone.now()
                request.user.profile.save(update_fields=['last_activity'])

            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            else:
                return redirect(settings.LOGIN_REDIRECT_URL)

    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})


def custom_logout_view(request):
    if request.method == 'POST':
        logout_view = BaseLogoutView.as_view(next_page=settings.LOGOUT_REDIRECT_URL or '/')
        return logout_view(request)
    else:
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL or settings.LOGIN_URL or '/')

        return render(request, 'users/logout_confirm.html', {})


def profile_view(request, user_id):
    """Представлення для відображення профілю будь-якого користувача за ID."""
    viewed_user = get_object_or_404(User, pk=user_id)
    user_profile = viewed_user.profile 

    is_my_profile = (request.user == viewed_user)

    current_status = user_profile.status 


    calculated_actual_status = 'offline' 

    if user_profile.last_activity:
        time_since_last_activity = timezone.now() - user_profile.last_activity
        

        if time_since_last_activity < timezone.timedelta(minutes=ONLINE_THRESHOLD_MINUTES):
            if current_status == 'invisible':
                if is_my_profile:
                    calculated_actual_status = 'invisible'
                else:
                    calculated_actual_status = 'offline'
            else:
                calculated_actual_status = current_status
        else:
            calculated_actual_status = 'offline'
    else: 
        calculated_actual_status = 'offline'

    if calculated_actual_status not in [choice[0] for choice in Profile.STATUS_CHOICES] + ['offline']:
        calculated_actual_status = 'offline' 


    friendship_status = None 
    follow_status = False

    sent_request = None 
    received_request = None 

    if request.user.is_authenticated and not is_my_profile:
        sent_request = Friendship.objects.filter(
            from_user=request.user,
            to_user=viewed_user,
            status='pending'
        ).first()

        received_request = Friendship.objects.filter(
            from_user=viewed_user,
            to_user=request.user,
            status='pending'
        ).first()

        are_friends = Friendship.objects.filter(
            (Q(from_user=request.user, to_user=viewed_user) | Q(from_user=viewed_user, to_user=request.user)),
            status='accepted'
        ).exists()

        if sent_request:
            friendship_status = 'pending_sent'
        elif received_request:
            friendship_status = 'pending_received'
        elif are_friends:
            friendship_status = 'friends'
        else:
            friendship_status = 'not_friends'

        if Follow.objects.filter(follower=request.user, following=viewed_user).exists():
            follow_status = True

    latest_post = Post.objects.filter(author=viewed_user).order_by('-created_at').first()
    
    user_posts = [] 

    user_friends = User.objects.filter(
        Q(sent_friend_requests__to_user=viewed_user, sent_friend_requests__status='accepted') |
        Q(received_friend_requests__from_user=viewed_user, received_friend_requests__status='accepted')
    ).distinct().order_by('username')


    user_activity = []

    context = {
        'viewed_user': viewed_user, 
        'user_profile': user_profile, 
        'is_my_profile': is_my_profile, 
        'friendship_status': friendship_status, 
        'follow_status': follow_status, 

        'user_posts': user_posts,
        'user_friends': user_friends, 
        'user_activity': user_activity,

        'sent_request': sent_request,
        'received_request': received_request,
        'actual_status': calculated_actual_status, 
        'latest_post': latest_post,
    }
    return render(request, 'users/profile.html', context)


@login_required
def edit_profile_view(request):
    user = request.user
    user_profile = user.profile

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('users:user_profile', user.id)



    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=user_profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'users/edit_profile.html', context)



@require_POST
@login_required
def set_user_status(request):
    if not hasattr(request.user, 'profile'):
        return JsonResponse({'status': 'error', 'message': 'Не вдалося знайти профіль користувача.'}, status=404)

    chosen_status = request.POST.get('status_type')

    try:
        valid_statuses = [choice[0] for choice in Profile.STATUS_CHOICES]
    except AttributeError:
        return JsonResponse({'status': 'error', 'message': 'Помилка: Не можу отримати список статусів. Перевірте модель Profile.'}, status=500)
    except NameError:
        return JsonResponse({'status': 'error', 'message': 'Помилка: Модель Profile не імпортована або недоступна.'}, status=500)


    if chosen_status not in valid_statuses:
        return JsonResponse({'status': 'error', 'message': 'Недійсний статус'}, status=400)

    
    try:
        profile = request.user.profile
        profile.status = chosen_status
        profile.last_activity = timezone.now() 
        profile.save(update_fields=['status', 'last_activity'])

        display_status = 'offline' if chosen_status == 'invisible' else chosen_status


        return JsonResponse({
            'status': 'success', 
            'message': '',
            'new_status': display_status,
            'chosen_status': chosen_status 
        })

    except Exception as e:
        print(f"Помилка при зміні статусу: {e}") 
        return JsonResponse({'status': 'error', 'message': f'Сталася помилка при зміні статусу: {str(e)}'}, status=500)





@login_required
def friends_list_view(request):
    friends = User.objects.filter(
        Q(sent_friend_requests__to_user=request.user, sent_friend_requests__status='accepted') |
        Q(received_friend_requests__from_user=request.user, received_friend_requests__status='accepted')
    ).distinct().order_by('username')

    received_requests = Friendship.objects.filter(to_user=request.user, status='pending').order_by('-created_at')

    sent_requests = Friendship.objects.filter(from_user=request.user, status='pending').order_by('-created_at')

    context = {
        'friends': friends,
        'received_requests': received_requests,
        'sent_requests': sent_requests,
    }
    return render(request, 'users/friends_list.html', context)


@require_POST
@login_required
def send_friend_request(request, to_user_id):
    to_user = get_object_or_404(User, pk=to_user_id)

    if request.user == to_user:
        return JsonResponse({'status': 'error', 'message': "Ви не можете відправити запит дружби самому собі."}, status=400)

    friendship_status = 'not_friends'
    sent_request = None
    received_request = None

    try:
        existing_friendship = Friendship.objects.filter(
            Q(from_user=request.user, to_user=to_user) | Q(from_user=to_user, to_user=request.user)
        ).first()

        is_new_request = False

        if existing_friendship:
            if existing_friendship.status == 'accepted':
                friendship_status = 'friends'
                message = "Ви вже друзі."
            elif existing_friendship.status == 'pending':
                if existing_friendship.from_user == request.user:
                    friendship_status = 'pending_sent'
                    sent_request = existing_friendship
                    message = "Запит дружби вже відправлено."
                else:
                    friendship_status = 'pending_received'
                    received_request = existing_friendship
                    message = "Вам вже надіслано запит дружби від цього користувача."
            else:
                # Should not happen with current status choices, but as a fallback
                existing_friendship.from_user = request.user
                existing_friendship.to_user = to_user
                existing_friendship.status = 'pending'
                existing_friendship.created_at = timezone.now()
                existing_friendship.save()
                friendship_status = 'pending_sent'
                sent_request = existing_friendship
                is_new_request = True
                message = "Запит дружби відправлено."
        else:
            friendship = Friendship.objects.create(from_user=request.user, to_user=to_user, status='pending')
            friendship_status = 'pending_sent'
            sent_request = friendship
            is_new_request = True
            message = "Запит дружби відправлено."

        if is_new_request:
            recipient = to_user
            sender_user = request.user
            notification_type = 'friend_request'
            content = f"{sender_user.username} надіслав(-ла) вам запит на дружбу."
            related_object = sent_request
            custom_url = reverse('users:profile', args=[sender_user.id])

            send_notification_to_user(
                recipient=recipient,
                sender=sender_user,
                notification_type=notification_type,
                content=content,
                related_object=related_object,
                custom_url=custom_url
            )
            print(f"DEBUG: Notification 'friend_request' sent to {recipient.username} from {sender_user.username}")


        follow_status = Follow.objects.filter(follower=request.user, following=to_user).exists()

        new_button_html = render_to_string('profile_actions_snippet.html', {
            'viewed_user': to_user,
            'is_my_profile': False,
            'friendship_status': friendship_status,
            'follow_status': follow_status,
            'user': request.user,
            'sent_request': sent_request,
            'received_request': received_request,
        }, request=request)

        return JsonResponse({'status': 'success', 'message': message, 'new_button_html': new_button_html})

    except IntegrityError:
        print("IntegrityError caught in send_friend_request. Re-evaluating friendship status.")
        message = "Запит дружби вже існує або ви вже друзі."

        current_friendship = Friendship.objects.filter(
            (Q(from_user=request.user, to_user=to_user) | Q(from_user=to_user, to_user=request.user))
        ).first()

        if current_friendship:
            if current_friendship.status == 'accepted':
                friendship_status = 'friends'
                message = "Ви вже друзі."
            elif current_friendship.status == 'pending':
                if current_friendship.from_user == request.user:
                    friendship_status = 'pending_sent'
                    sent_request = current_friendship
                    message = "Запит дружби вже відправлено."
                else:
                    friendship_status = 'pending_received'
                    received_request = current_friendship
                    message = "Вам вже надіслано запит дружби від цього користувача."
            else:
                friendship_status = 'not_friends' # Fallback for unknown status
        else:
            friendship_status = 'not_friends'

        follow_status = Follow.objects.filter(follower=request.user, following=to_user).exists()

        new_button_html = render_to_string('profile_actions_snippet.html', {
            'viewed_user': to_user,
            'is_my_profile': False,
            'friendship_status': friendship_status,
            'follow_status': follow_status,
            'user': request.user,
            'sent_request': sent_request,
            'received_request': received_request,
        }, request=request)

        return JsonResponse({
            'status': 'info',
            'message': message,
            'new_button_html': new_button_html
        }, status=200)

    except Exception as e:
        print(f"An unexpected error occurred in send_friend_request: {e}")
        return JsonResponse({'status': 'error', 'message': 'Сталася невідома помилка.'}, status=500)


@require_POST
@login_required
def accept_friend_request(request, friendship_id):
    friendship_request = get_object_or_404(Friendship, pk=friendship_id)

    if request.user == friendship_request.to_user and friendship_request.status == 'pending':
        friendship_request.accept()

        recipient = friendship_request.from_user
        sender_user = request.user
        notification_type = 'friend_accept'
        content = f"{sender_user.username} прийняв(-ла) ваш запит на дружбу."
        related_object = friendship_request
        custom_url = reverse('users:profile', args=[sender_user.id])

        send_notification_to_user(
            recipient=recipient,
            sender=sender_user,
            notification_type=notification_type,
            content=content,
            related_object=related_object,
            custom_url=custom_url
        )
        print(f"DEBUG: Notification 'friend_accept' sent to {recipient.username} from {sender_user.username}")
        
        viewed_user_on_profile = friendship_request.from_user

        friendship_status = 'friends'
        follow_status = Follow.objects.filter(follower=request.user, following=viewed_user_on_profile).exists()

        sent_request_after = None 
        received_request_after = None

        new_button_html = render_to_string('profile_actions_snippet.html', {
            'viewed_user': viewed_user_on_profile,
            'is_my_profile': False,
            'friendship_status': friendship_status,
            'follow_status': follow_status,
            'user': request.user,
            'sent_request': sent_request_after,
            'received_request': received_request_after,
        }, request=request)

        return JsonResponse({
            'status': 'success',
            'message': 'Запит дружби прийнято.',
            'request_id': friendship_id,
            'new_button_html': new_button_html
        })
    else:
        return JsonResponse({'status': 'error', 'message': 'Не вдалося прийняти запит дружби.'}, status=400)


@require_POST
@login_required
def decline_friend_request(request, friendship_id):
    friendship_request = get_object_or_404(Friendship, pk=friendship_id)

    if request.user == friendship_request.to_user and friendship_request.status == 'pending':
        friendship_request.delete()
        
        viewed_user_on_profile = friendship_request.from_user

        friendship_status = 'not_friends'
        follow_status = Follow.objects.filter(follower=request.user, following=viewed_user_on_profile).exists()

        sent_request_after = None
        received_request_after = None

        new_button_html = render_to_string('profile_actions_snippet.html', {
            'viewed_user': viewed_user_on_profile,
            'is_my_profile': False,
            'friendship_status': friendship_status,
            'follow_status': follow_status,
            'user': request.user,
            'sent_request': sent_request_after,
            'received_request': received_request_after,
        }, request=request)

        return JsonResponse({
            'status': 'success',
            'message': 'Запит дружби відхилено.',
            'request_id': friendship_id,
            'new_button_html': new_button_html
        })
    else:
        return JsonResponse({'status': 'error', 'message': 'Не вдалося відхилити запит дружби.'}, status=400)


@require_POST
@login_required
def cancel_friend_request(request, friendship_id):
    friendship_request = get_object_or_404(Friendship, pk=friendship_id, from_user=request.user, status='pending')

    viewed_user_on_profile = friendship_request.to_user

    friendship_request.delete()

    friendship_status = 'not_friends'
    follow_status = Follow.objects.filter(follower=request.user, following=viewed_user_on_profile).exists()

    sent_request_after = None
    received_request_after = None

    new_button_html = render_to_string('profile_actions_snippet.html', {
        'viewed_user': viewed_user_on_profile,
        'is_my_profile': False,
        'friendship_status': friendship_status,
        'follow_status': follow_status,
        'user': request.user,
        'sent_request': sent_request_after,
        'received_request': received_request_after,
    }, request=request)

    return JsonResponse({
        'status': 'success',
        'message': 'Запит дружби скасовано.',
        'request_id': friendship_id,
        'new_button_html': new_button_html
    })

@require_POST
@login_required
def remove_friend(request, user_id):
    friend_to_remove = get_object_or_404(User, pk=user_id)

    friendship_instance = Friendship.objects.filter(
        (Q(from_user=request.user, to_user=friend_to_remove) | Q(from_user=friend_to_remove, to_user=request.user)),
        status='accepted'
    ).first()

    if friendship_instance:
        friendship_instance.delete()
        message_text = 'Друга видалено.'

        friendship_status = 'not_friends'
        follow_status = Follow.objects.filter(follower=request.user, following=friend_to_remove).exists()

        new_button_html = render_to_string('profile_actions_snippet.html', {
            'viewed_user': friend_to_remove,
            'is_my_profile': False,
            'friendship_status': friendship_status,
            'follow_status': follow_status,
            'user': request.user,
            'sent_request': None,
            'received_request': None,
        }, request=request)

        return JsonResponse({'status': 'success', 'message': message_text, 'new_button_html': new_button_html})
    else:
        return JsonResponse({'status': 'error', 'message': 'Користувача не знайдено серед ваших друзів.'}, status=400)


@require_POST
@login_required
def follow_user(request, user_id):
    following_user = get_object_or_404(User, pk=user_id)

    if request.user == following_user:
        return JsonResponse({'status': 'error', 'message': 'Ви не можете підписатися на самого себе.'}, status=400)

    follow_instance, created = Follow.objects.get_or_create(
        follower=request.user,
        following=following_user
    )

    if created:
        status_response = 'success'
        message_response = 'Ви успішно підписалися.'
        follow_status = True

        recipient = following_user
        sender_user = request.user
        notification_type = 'follow'
        content = f"{sender_user.username} підписався(-ась) на вас."
        related_object = follow_instance
        custom_url = reverse('users:profile', args=[sender_user.id])

        send_notification_to_user(
            recipient=recipient,
            sender=sender_user,
            notification_type=notification_type,
            content=content,
            related_object=related_object,
            custom_url=custom_url
        )
        print(f"DEBUG: Notification 'follow' sent to {recipient.username} from {sender_user.username}")

    else:
        status_response = 'info'
        message_response = 'Ви вже підписані на цього користувача.'
        follow_status = True

    sent_request = Friendship.objects.filter(
        from_user=request.user,
        to_user=following_user,
        status='pending'
    ).first()

    received_request = Friendship.objects.filter(
        from_user=following_user,
        to_user=request.user,
        status='pending'
    ).first()

    are_friends = Friendship.objects.filter(
        (Q(from_user=request.user, to_user=following_user) | Q(from_user=following_user, to_user=request.user)),
        status='accepted'
    ).exists()

    if are_friends:
        friendship_status = 'friends'
    elif sent_request:
        friendship_status = 'pending_sent'
    elif received_request:
        friendship_status = 'pending_received'
    else:
        friendship_status = 'not_friends'


    new_button_html = render_to_string('profile_actions_snippet.html', {
        'viewed_user': following_user,
        'is_my_profile': False,
        'friendship_status': friendship_status,
        'follow_status': follow_status,
        'user': request.user,
        'sent_request': sent_request,
        'received_request': received_request,
    }, request=request)

    return JsonResponse({'status': status_response, 'message': message_response, 'new_button_html': new_button_html}, status=200)


@require_POST
@login_required
def unfollow_user(request, user_id):
    following_user = get_object_or_404(User, pk=user_id)

    follow_instance = Follow.objects.filter(follower=request.user, following=following_user).first()

    if follow_instance:
        follow_instance.delete()

        status_response = 'success'
        message_response = 'Ви успішно відписалися.'
        follow_status = False
    else:
        status_response = 'info'
        message_response = 'Ви не підписані на цього користувача.'
        follow_status = False

    sent_request = Friendship.objects.filter(
        from_user=request.user,
        to_user=following_user,
        status='pending'
    ).first()

    received_request = Friendship.objects.filter(
        from_user=following_user,
        to_user=request.user,
        status='pending'
    ).first()

    are_friends = Friendship.objects.filter(
        (Q(from_user=request.user, to_user=following_user) | Q(from_user=following_user, to_user=request.user)),
        status='accepted'
    ).exists()

    if are_friends:
        friendship_status = 'friends'
    elif sent_request:
        friendship_status = 'pending_sent'
    elif received_request:
        friendship_status = 'pending_received'
    else:
        friendship_status = 'not_friends'


    new_button_html = render_to_string('profile_actions_snippet.html', {
        'viewed_user': following_user,
        'is_my_profile': False,
        'friendship_status': friendship_status,
        'follow_status': follow_status,
        'user': request.user,
        'sent_request': sent_request,
        'received_request': received_request,
    }, request=request)

    return JsonResponse({'status': status_response, 'message': message_response, 'new_button_html': new_button_html}, status=200)