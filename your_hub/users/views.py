from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from .models import Profile, Friendship, Follow
from django.conf import settings
from django.contrib.auth.views import LogoutView as BaseLogoutView
from django.views.generic import FormView
from django.utils import timezone
from django.http import JsonResponse # Для AJAX
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string# HTML сниппеты

ONLINE_THRESHOLD_MINUTES = 5 # "Порог" времени для определения статуса онлайн

def register_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            # messages.success(request, f'Аккаунт создан для {user.username}! Теперь вы можете войти.') # Убираем это сообщение
            return redirect('login')
        else:
            # Ошибки формы будут отображены в шаблоне
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


# @login_required # Профиль может быть доступен и неавторизованным пользователям для просмотра (но не для действий)
def profile_view(request, user_id):
    """Представление для отображения профиля любого пользователя по ID."""
    viewed_user = get_object_or_404(User, pk=user_id)
    user_profile = viewed_user.profile 

    is_my_profile = (request.user == viewed_user)

    # --- Корректное определение actual_status для отображения ---
    current_status = user_profile.status # Берем текущий статус из профиля пользователя

    # Инициализируем статус, который будет отображаться
    calculated_actual_status = 'offline' 

    if user_profile.last_activity:
        time_since_last_activity = timezone.now() - user_profile.last_activity
        
        # Если пользователь был активен недавно
        if time_since_last_activity < timezone.timedelta(minutes=ONLINE_THRESHOLD_MINUTES):
            # Логика для "невидимого" статуса:
            if current_status == 'invisible':
                if is_my_profile:
                    # Если это мой профиль и я "невидимый", показываем "невидимый"
                    calculated_actual_status = 'invisible'
                else:
                    # Если это ЧУЖОЙ профиль и он "невидимый", показываем "оффлайн"
                    calculated_actual_status = 'offline'
            else:
                # Если статус не "невидимый" и пользователь активен, показываем его реальный статус
                calculated_actual_status = current_status
        else:
            # Если пользователь неактивен дольше ONLINE_THRESHOLD_MINUTES, он всегда "оффлайн"
            calculated_actual_status = 'offline'
    else: 
        # Если нет информации о последней активности, считаем оффлайн
        calculated_actual_status = 'offline'

    # Дополнительная проверка на случай, если status_profile был пуст или содержал невалидное значение
    # Хотя благодаря default='offline' в модели Profile и Profile.STATUS_CHOICES, это менее вероятно.
    if calculated_actual_status not in [choice[0] for choice in Profile.STATUS_CHOICES] + ['offline']:
        calculated_actual_status = 'offline' # Устанавливаем дефолтное значение, если что-то пошло не так.


    # --- Остальная часть вашей функции (без изменений, так как она уже работает) ---
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
        'actual_status': calculated_actual_status, # Передаем вычисленный статус в контекст
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
            # messages.success(request, 'Профиль успешно обновлен!') # Убираем это сообщение
            return redirect('user_profile', user.id)
        # else:
             # Ошибки формы будут отображены в шаблоне
             # pass


    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=user_profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'users/edit_profile.html', context)


# users/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse 
from django.views.decorators.http import require_POST
from .models import Profile # Убедитесь, что Profile импортирован правильно
from django.utils import timezone # Добавьте импорт timezone

@require_POST
@login_required
def set_user_status(request):
    # Эта проверка хороша, но если profile не существует,
    # request.user.profile все равно вызовет DoesNotExist
    # до того, как эта проверка сработает, если access profile через related_name.
    # Более надежно это делать через try-except Profile.DoesNotExist, как я предлагал ранее,
    # или убедиться, что у всех пользователей есть профили.
    if not hasattr(request.user, 'profile'):
        # Это сработает, если request.user.profile не был создан.
        return JsonResponse({'status': 'error', 'message': 'Не удалось найти профиль пользователя.'}, status=404) # Добавьте status=404

    chosen_status = request.POST.get('status_type')

    # Убедитесь, что Profile импортирован, иначе Profile.STATUS_CHOICES вызовет NameError
    try: # Добавим try-except вокруг получения valid_statuses на случай, если Profile не импортирован или проблема с атрибутом
        valid_statuses = [choice[0] for choice in Profile.STATUS_CHOICES]
    except AttributeError:
        return JsonResponse({'status': 'error', 'message': 'Ошибка: Не могу получить список статусов. Проверьте модель Profile.'}, status=500)
    except NameError:
         return JsonResponse({'status': 'error', 'message': 'Ошибка: Модель Profile не импортирована или недоступна.'}, status=500)


    if chosen_status not in valid_statuses:
        return JsonResponse({'status': 'error', 'message': 'Недопустимый статус'}, status=400) # Добавьте status=400

    
    try:
        profile = request.user.profile
        profile.status = chosen_status
        profile.last_activity = timezone.now() # Добавьте это, если у вас есть поле last_activity
        profile.save(update_fields=['status', 'last_activity'])

        # Исправлено:
        display_status = 'offline' if chosen_status == 'invisible' else chosen_status


        return JsonResponse({
            'status': 'success', # Здесь было 'succes', изменил на 'success'
            'message': '',
            'new_status': display_status, # Это фактический статус для отображения
            'chosen_status': chosen_status # Это статус, который выбрал пользователь
        })

    except Exception as e:
        # Важно: В продакшене не выводите str(e) напрямую пользователю,
        # но для отладки это полезно
        print(f"Ошибка при изменении статуса: {e}") # Это сообщение появится в консоли Django-сервера
        return JsonResponse({'status': 'error', 'message': f'Произошла ошибка при изменении статуса: {str(e)}'}, status=500)





# --- Представления для Друзей и Подписок ---

@login_required
def friends_list_view(request):
    """Представление для отображения списка друзей и запросов на дружбу текущего пользователя."""
    # Получаем список друзей текущего пользователя (accepted в обе стороны)
    # Ищем User объекты, которые являются from_user или to_user в accepted Friendship,
    # где другой стороной является request.user
    friends = User.objects.filter(
        Q(sent_friend_requests__to_user=request.user, sent_friend_requests__status='accepted') |
        Q(received_friend_requests__from_user=request.user, received_friend_requests__status='accepted')
    ).distinct().order_by('username') # distinct() чтобы избежать дублирования, order_by для сортировки

    # Получаем входящие запросы на дружбу (текущий пользователь - to_user, статус 'pending')
    received_requests = Friendship.objects.filter(to_user=request.user, status='pending').order_by('-created_at')

    # Получаем исходящие запросы на дружбу (текущий пользователь - from_user, статус 'pending')
    sent_requests = Friendship.objects.filter(from_user=request.user, status='pending').order_by('-created_at')

    # TODO: Реализовать пагинацию для списков друзей и запросов

    context = {
        'friends': friends, # Список объектов User, которые являются друзьями
        'received_requests': received_requests, # Список объектов Friendship (входящие запросы)
        'sent_requests': sent_requests, # Список объектов Friendship (исходящие запросы)
    }
    return render(request, 'users/friends_list.html', context)


@require_POST
@login_required
def send_friend_request(request, to_user_id):
    """Представление для отправки запроса на дружбу по AJAX."""
    to_user = get_object_or_404(User, pk=to_user_id)

    # Нельзя отправить запрос самому себе
    if request.user == to_user:
        return JsonResponse({'status': 'error', 'message': ""}, status=400)

    friendship_status = 'not_friends'
    sent_request = None
    received_request = None

    try:
        # Попытаться найти существующий запрос на дружбу между этими двумя пользователями
        # в любом направлении и статусе (включая 'declined', 'cancelled' и т.д.)
        existing_friendship = Friendship.objects.filter(
            Q(from_user=request.user, to_user=to_user) | Q(from_user=to_user, to_user=request.user)
        ).first()

        if existing_friendship:
            # Логика для обработки уже существующего отношения
            if existing_friendship.status == 'accepted':
                friendship_status = 'friends'
                # В случае, если уже друзья, возможно, хотим вернуть 'info' статус,
                # но для обновления кнопок 'success' тоже подойдет.
            elif existing_friendship.status == 'pending':
                if existing_friendship.from_user == request.user:
                    friendship_status = 'pending_sent'
                    sent_request = existing_friendship
                else: # existing_friendship.to_user == request.user
                    friendship_status = 'pending_received'
                    received_request = existing_friendship
            else: # Статус был 'declined', 'cancelled' или другой неактивный
                # Обновляем существующую запись до 'pending'
                # Это ключевой момент для предотвращения IntegrityError при повторной отправке
                existing_friendship.from_user = request.user # Убедимся, что отправитель - текущий пользователь
                existing_friendship.to_user = to_user        # Убедимся, что получатель - целевой пользователь
                existing_friendship.status = 'pending'
                existing_friendship.created_at = timezone.now() # Обновляем время создания
                existing_friendship.save()
                friendship_status = 'pending_sent'
                sent_request = existing_friendship
        else:
            # Если записи не существует (по обоим направлениям), создаем новую
            friendship = Friendship.objects.create(from_user=request.user, to_user=to_user, status='pending')
            friendship_status = 'pending_sent'
            sent_request = friendship

        # Обновляем статус подписки (не связан с дружбой напрямую, но нужен для рендеринга кнопок)
        follow_status = Follow.objects.filter(follower=request.user, following=to_user).exists()

        # Рендерим новый HTML для кнопок
        new_button_html = render_to_string('profile_actions_snippet.html', {
            'viewed_user': to_user,
            'is_my_profile': False, # Всегда False для профиля другого пользователя
            'friendship_status': friendship_status,
            'follow_status': follow_status,
            'user': request.user, # Текущий авторизованный пользователь
            'sent_request': sent_request, # Передаем объект запроса, если он есть
            'received_request': received_request, # Передаем объект запроса, если он есть
        }, request=request)

        # Возвращаем успешный JSON ответ
        return JsonResponse({'status': 'success', 'message': '', 'new_button_html': new_button_html})

    except IntegrityError:
        # Если произошла IntegrityError (например, из-за race condition),
        # пытаемся получить актуальное состояние, чтобы отправить корректный HTML без ошибки.
        # Это более мягкое поведение, чем просто возврат 500.
        print("IntegrityError caught in send_friend_request. Re-evaluating friendship status.")

        # Повторно запрашиваем статус отношений, так как база данных могла измениться
        # между нашим первым запросом и попыткой создания.
        current_friendship = Friendship.objects.filter(
            Q(from_user=request.user, to_user=to_user) | Q(from_user=to_user, to_user=request.user)
        ).first()

        if current_friendship:
            if current_friendship.status == 'accepted':
                friendship_status = 'friends'
            elif current_friendship.status == 'pending':
                if current_friendship.from_user == request.user:
                    friendship_status = 'pending_sent'
                    sent_request = current_friendship
                else:
                    friendship_status = 'pending_received'
                    received_request = current_friendship
            else: # Возможно, был 'declined' или 'cancelled', но IntegrityError все равно сработал
                # В этом случае, если произошла ошибка, но записи нет или она неактивна,
                # мы можем считать ее 'not_friends' для отображения кнопок
                friendship_status = 'not_friends'
        else:
            # Крайне маловероятно после IntegrityError, но на всякий случай
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

        # Возвращаем статус 'info' и сообщение, что действие, возможно, уже обработано.
        # Это позволит фронтенду обновить кнопки, не показывая пользователю "ошибку".
        return JsonResponse({
            'status': 'info',
            'message': '',
            'new_button_html': new_button_html
        }, status=200)

    except Exception as e:
        # Ловим любые другие неожиданные ошибки
        print(f"An unexpected error occurred in send_friend_request: {e}")
        return JsonResponse({'status': 'error', 'message': ''}, status=500)


@require_POST # Ожидаем только POST запрос для AJAX
@login_required
def accept_friend_request(request, friendship_id):
    """Представление для принятия запроса на дружбу по AJAX."""
    # Получаем объект запроса или возвращаем 404, если не существует
    friendship_request = get_object_or_404(Friendship, pk=friendship_id)

    # Проверяем, что текущий пользователь является получателем запроса и статус 'pending'
    if request.user == friendship_request.to_user and friendship_request.status == 'pending':
        friendship_request.accept() # Метод accept должен изменить статус на 'accepted'
        
        viewed_user_on_profile = friendship_request.from_user

        # После принятия, статус дружбы становится 'friends'
        friendship_status = 'friends'
        follow_status = Follow.objects.filter(follower=request.user, following=viewed_user_on_profile).exists()

        # После принятия запроса, не должно быть активных pending запросов между этими двумя пользователями
        # sent_request и received_request будут None, так как отношения установились
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
            'message': '', # Оставляем сообщение пустым
            'request_id': friendship_id, # Возвращаем ID запроса для JS на странице друзей
            'new_button_html': new_button_html # HTML для кнопки на странице профиля отправителя запроса (если там приняли)
        })
    else:
        return JsonResponse({'status': 'error', 'message': ''}, status=400)


@require_POST # Ожидаем только POST запрос для AJAX
@login_required
def decline_friend_request(request, friendship_id):
    """Представление для отклонения запроса на дружбу по AJAX."""
    friendship_request = get_object_or_404(Friendship, pk=friendship_id)

    if request.user == friendship_request.to_user and friendship_request.status == 'pending':
        # Вместо удаления, меняем статус на 'declined' (предполагая, что такой статус есть в модели)
        # Если такого статуса нет, то можно просто удалить запись.
        # Но если есть unique_together без статуса, удаление - единственный путь,
        # или нужно убедиться, что unique_together включает статус.
        # Для решения проблемы с UNIQUE constraint, лучше удалить или обновить.
        # Если UNIQUE constraint только на (from_user, to_user), тогда удаляем.
        friendship_request.delete() # Метод decline должен удалить объект Friendship
        
        viewed_user_on_profile = friendship_request.from_user

        # После отклонения, статус дружбы становится 'not_friends'
        friendship_status = 'not_friends'
        follow_status = Follow.objects.filter(follower=request.user, following=viewed_user_on_profile).exists()

        # Обновляем sent_request и received_request для корректного рендеринга
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
            'message': '', # Оставляем сообщение пустым
            'request_id': friendship_id, # Возвращаем ID запроса для JS на странице друзей
            'new_button_html': new_button_html # HTML для кнопки на странице профиля отправителя запроса (если там отклоняют)
        })
    else:
        return JsonResponse({'status': 'error', 'message': ''}, status=400)


@require_POST # Ожидаем только POST запрос для AJAX
@login_required
def cancel_friend_request(request, friendship_id):
    """Представление для отмены отправленного запроса на дружбу по AJAX."""
    # Получаем объект запроса, проверяя, что текущий пользователь является отправителем и статус 'pending'
    friendship_request = get_object_or_404(Friendship, pk=friendship_id, from_user=request.user, status='pending')

    # Пользователь, чей профиль просматриваем - это получатель запроса (friendship_request.to_user)
    viewed_user_on_profile = friendship_request.to_user

    friendship_request.delete() # Удаляем запрос

    # После отмены, определяем новый статус и рендерим кнопки для страницы профиля
    friendship_status = 'not_friends' # Статус стал 'not_friends'
    follow_status = Follow.objects.filter(follower=request.user, following=viewed_user_on_profile).exists()


    # После отмены, не должно быть активных pending запросов между этими двумя пользователями
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
        'message': '', # Оставляем сообщение пустым
        'request_id': friendship_id, # Возвращаем ID запроса для JS на странице друзей
        'new_button_html': new_button_html # HTML для кнопки на странице профиля получателя запроса (если там отменяют)
    })

@require_POST
@login_required
def remove_friend(request, user_id):
    """Представление для удаления друга по AJAX."""
    friend_to_remove = get_object_or_404(User, pk=user_id)

    # Проверяем, являются ли пользователи друзьями
    # Ищем записи Friendship, где статус 'accepted' и одна из сторон - request.user, а другая - friend_to_remove
    friendship_instance = Friendship.objects.filter(
        (Q(from_user=request.user, to_user=friend_to_remove) | Q(from_user=friend_to_remove, to_user=request.user)),
        status='accepted'
    ).first()

    if friendship_instance:
        friendship_instance.delete() # Удаляем запись о дружбе
        message_text = '' # Сообщение не нужно

        # После удаления, статус дружбы становится 'not_friends'
        friendship_status = 'not_friends'
        follow_status = Follow.objects.filter(follower=request.user, following=friend_to_remove).exists()

        new_button_html = render_to_string('profile_actions_snippet.html', {
            'viewed_user': friend_to_remove,
            'is_my_profile': False,
            'friendship_status': friendship_status,
            'follow_status': follow_status,
            'user': request.user,
            # После удаления запросов нет, поэтому sent_request и received_request будут None
            'sent_request': None,
            'received_request': None,
        }, request=request)

        return JsonResponse({'status': 'success', 'message': message_text, 'new_button_html': new_button_html})
    else:
        return JsonResponse({'status': 'error', 'message': ''}, status=400)


@require_POST # Ожидаем только POST запрос
@login_required
def follow_user(request, user_id):
    """Представление для подписки на пользователя по AJAX."""
    following_user = get_object_or_404(User, pk=user_id)

    if request.user == following_user:
        return JsonResponse({'status': 'error', 'message': ""}, status=400)

    # Важно: здесь мы не управляем friendship_status, только follow_status.
    # Если вы хотите, чтобы подписка/отписка влияла на кнопки дружбы,
    # то нужно определить friendship_status здесь, как это делается в profile_view.
    follow_instance, created = Follow.objects.get_or_create(
        follower=request.user,
        following=following_user
    )

    if created:
        status_response = 'success'
        message_response = ''
        follow_status = True
    else:
        status_response = 'info'
        message_response = ''
        follow_status = True

    # Определяем friendship_status для корректного рендеринга кнопок в сниппете
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


@require_POST # Ожидаем только POST запрос
@login_required
def unfollow_user(request, user_id):
    """Представление для отписки от пользователя по AJAX."""
    following_user = get_object_or_404(User, pk=user_id)

    follow_instance = Follow.objects.filter(follower=request.user, following=following_user).first()

    if follow_instance:
        follow_instance.delete()

        status_response = 'success'
        message_response = ''
        follow_status = False
    else:
        status_response = 'info'
        message_response = ''
        follow_status = False

    # Определяем friendship_status для корректного рендеринга кнопок в сниппете
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
