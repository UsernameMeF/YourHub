import json
import os 
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden, Http404
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction 
from django.db.models import Count, Q
from django.conf import settings 
from django.utils import timezone 
from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse

from .forms import PostForm, PostDeleteForm, CommentForm
from .models import Post, PostAttachment, Comment 
from users.models import Friendship, Follow
from community.models import Community, CommunityPost

User = get_user_model()

# Главная страница (лента постов)
def index(request):
    post_form = PostForm()

    context = {
        'post_form': post_form,
        # Если у вас есть другие переменные контекста для главной страницы, добавьте их здесь
    }
    return render(request, 'core/index.html', context) # Передаем контекст


# НОВАЯ ФУНКЦИЯ ДЛЯ AJAX-ЗАПРОСОВ ПОСТОВ (ДОПОЛНЕНА ДЛЯ ВКЛЮЧЕНИЯ ПОСТОВ СООБЩЕСТВ)
def get_posts_ajax(request):
    sort_by = request.GET.get('sort', 'new') 
    page_number = int(request.GET.get('page', 1)) 
    posts_per_page = 10

    # Получаем все обычные посты (Post из core)
    # Используем select_related и prefetch_related для оптимизации запросов к БД
    core_posts_queryset = Post.objects.select_related('author__profile').prefetch_related(
        'attachments', # Если attachments это ManyToManyField к модели изображения
        'likes', 'dislikes', 'reposts', 'comments'
    )

    # Получаем все посты сообществ (CommunityPost)
    # Используем select_related для posted_by и community
    community_posts_queryset = CommunityPost.objects.select_related(
        'posted_by__profile', 'community'
    ).prefetch_related(
        'likes', 'dislikes', 'reposts', 'comments'
    )

    # Собираем все посты в один список
    all_posts = []

    # Добавляем обычные посты
    for post in core_posts_queryset:
        author_avatar_url = settings.STATIC_URL + 'images/default-avatar.png'
        if hasattr(post.author, 'profile') and post.author.profile.avatar and post.author.profile.avatar.name:
            author_avatar_url = request.build_absolute_uri(post.author.profile.avatar.url)
        
        # Собираем вложения (если Post имеет ManyToManyField 'attachments' к другой модели с полем 'image')
        # Если Post имеет одно поле image, то просто post.image.url
        attachments_data = [{'url': request.build_absolute_uri(att.image.url)} for att in post.attachments.all() if att.image]

        all_posts.append({
            'id': post.pk,
            'is_community_post': False, # Флаг для JS
            'author_username': post.author.username,
            'author_id': post.author.id,
            'author_avatar_url': author_avatar_url,
            'title': post.title,
            'content': post.content,
            'created_at': post.created_at, # Дата/время как объекты, чтобы сортировать
            'updated_at': post.updated_at,
            'total_likes': post.total_likes, # Предполагается @property в модели Post
            'total_dislikes': post.total_dislikes, # Предполагается @property
            'total_reposts': post.total_reposts, # Предполагается @property
            'total_comments': post.total_comments, # Предполагается @property
            'attachments': attachments_data,
            'detail_url': reverse('core:post_detail', args=[post.pk]), # URL для детальной страницы обычного поста
            # Поля community будут отсутствовать или null для обычных постов
            'community_id': None,
            'community_name': None,
            'community_url': None,
        })

    # Добавляем посты сообществ (CommunityPost)
    for post in community_posts_queryset:
        author_avatar_url = settings.STATIC_URL + 'images/default-avatar.png' 
        if hasattr(post.posted_by, 'profile') and post.posted_by.profile.avatar and post.posted_by.profile.avatar.name:
            author_avatar_url = request.build_absolute_uri(post.posted_by.profile.avatar.url)

        community_avatar_url = settings.STATIC_URL + 'images/default_community_avatar.png' 
        if hasattr(post.community, 'avatar') and post.community.avatar and post.community.avatar.name:
            community_avatar_url = request.build_absolute_uri(post.community.avatar.url)


        all_posts.append({
            'id': post.pk,
            'is_community_post': True, 
            'author_username': post.posted_by.username if post.posted_by else '[Удаленный пользователь]',
            'author_id': post.posted_by.id if post.posted_by else None,
            'author_avatar_url': author_avatar_url,
            'title': post.title, # <-- ИЗМЕНЕНО: теперь используем post.title напрямую
            'content': post.content,
            'created_at': post.created_at, 
            'updated_at': post.updated_at if hasattr(post, 'updated_at') and post.updated_at else post.created_at, # Учитываем updated_at, если добавил
            'total_likes': post.total_likes, 
            'total_dislikes': post.total_dislikes, 
            'total_reposts': post.total_reposts, 
            'total_comments': post.total_comments, 
            'detail_url': reverse('community:community_post_detail', args=[post.community.pk, post.pk]),
            'community_id': post.community.pk,
            'community_name': post.community.name,
            'community_url': reverse('community:community_detail', args=[post.community.pk]),
            'community_avatar_url': community_avatar_url, 
        })

    # Сортировка объединенного списка
    if sort_by == 'popular':
        # Сортируем по общей сумме лайков, дизлайков, репостов и комментариев
        all_posts.sort(key=lambda p: (p['total_likes'] + p['total_dislikes'] + p['total_reposts'] + p['total_comments']), reverse=True)
    else: # 'new'
        all_posts.sort(key=lambda p: p['created_at'], reverse=True)


    # Ручная пагинация (бесконечный скролл)
    start_index = (page_number - 1) * posts_per_page
    end_index = start_index + posts_per_page
    
    posts_on_page = all_posts[start_index:end_index] # Получаем посты для текущей страницы
    has_next_page = len(all_posts) > end_index # Проверяем, есть ли следующая страница

    serialized_posts_data = []
    current_user_id = request.user.id if request.user.is_authenticated else None

    for post_data in posts_on_page:
        # Теперь добавляем поля is_liked, is_disliked, is_reposted, can_edit_delete
        # (они не были в исходных словарях, т.к. values() их не тянет)
        # Это потребует дополнительного запроса к БД для каждой кнопки, 
        # или предзагрузки всех состояний пользователя.
        # Для эффективности, лучше предзагрузить лайки/дизлайки/репосты пользователя.
        
        # Оптимизация: Кэшируем ID лайков/дизлайков/репостов текущего пользователя
        # (Добавляется в request.user, чтобы не повторять запрос для каждого поста)
        if current_user_id:
            if not hasattr(request.user, '_liked_posts_ids_cache'):
                request.user._liked_posts_ids_cache = set(request.user.liked_posts.values_list('id', flat=True))
                request.user._disliked_posts_ids_cache = set(request.user.disliked_posts.values_list('id', flat=True))
                request.user._reposted_posts_ids_cache = set(request.user.reposted_posts.values_list('id', flat=True))
                request.user._liked_community_posts_ids_cache = set(request.user.liked_community_posts.values_list('id', flat=True))
                request.user._disliked_community_posts_ids_cache = set(request.user.disliked_community_posts.values_list('id', flat=True))
                request.user._reposted_community_posts_ids_cache = set(request.user.reposted_community_posts.values_list('id', flat=True))

            if post_data['is_community_post']:
                post_data['is_liked'] = post_data['id'] in request.user._liked_community_posts_ids_cache
                post_data['is_disliked'] = post_data['id'] in request.user._disliked_community_posts_ids_cache
                post_data['is_reposted'] = post_data['id'] in request.user._reposted_community_posts_ids_cache
                
                # Проверка админства сообщества для удаления
                is_community_admin = False
                if request.user.is_authenticated and post_data['community_id']:
                     is_community_admin = Community.objects.filter(
                         pk=post_data['community_id'], 
                         communitymembership__user=request.user, 
                         communitymembership__is_admin=True
                     ).exists()
                
                # can_edit_delete для CommunityPost: либо автор поста, либо админ сообщества
                post_data['can_edit_delete'] = (request.user.is_authenticated and 
                                                (current_user_id == post_data['author_id'] or is_community_admin))

            else: # Обычный пост
                post_data['is_liked'] = post_data['id'] in request.user._liked_posts_ids_cache
                post_data['is_disliked'] = post_data['id'] in request.user._disliked_posts_ids_cache
                post_data['is_reposted'] = post_data['id'] in request.user._reposted_posts_ids_cache
                
                # can_edit_delete для обычного поста: только автор поста
                post_data['can_edit_delete'] = (request.user.is_authenticated and 
                                                current_user_id == post_data['author_id'])
        else: # Неавторизованный пользователь
            post_data['is_liked'] = False
            post_data['is_disliked'] = False
            post_data['is_reposted'] = False
            post_data['can_edit_delete'] = False

        # Форматируем даты для JSON
        post_data['created_at'] = post_data['created_at'].strftime("%d %b %Y, %H:%M")
        if post_data['updated_at']:
             post_data['updated_at'] = post_data['updated_at'].strftime("%d %b %Y, %H:%M")
        else:
             post_data['updated_at'] = None # Если updated_at не отличается от created_at, делаем его None

        serialized_posts_data.append(post_data)

    return JsonResponse({
        'posts': serialized_posts_data,
        'has_next_page': has_next_page
    })


@login_required
def get_post_reposts_list(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    current_user = request.user

    all_repost_users = post.reposts.all()

    repost_users_data = []

    friends = set()
    accepted_friendships = Friendship.objects.filter(
        Q(from_user=current_user) | Q(to_user=current_user),
        status='accepted'
    ).select_related('from_user', 'to_user') # Оптимизация: избегаем лишних запросов к БД

    for fs in accepted_friendships:
        if fs.from_user == current_user:
            friends.add(fs.to_user)
        else:
            friends.add(fs.from_user)

    # Получаем ID пользователей, на которых подписан текущий пользователь
    following_ids = set(current_user.following.values_list('following__id', flat=True))

    for user in all_repost_users:
        # Убедимся, что user.profile существует, чтобы избежать AttributeError
        avatar_url = user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else '/media/images/default-avatar.png'
        
        if user == current_user:
            repost_users_data.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': avatar_url,
                'relationship': 'Вы (репостнули)', # Оставляем для полноты данных, хоть и не используем в HTML
            })
        elif user in friends:
            repost_users_data.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': avatar_url,
                'relationship': 'Друг',
            })
        elif user.id in following_ids: # Сравниваем по ID, так как following_ids это set из ID
            repost_users_data.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': avatar_url,
                'relationship': 'Подписка',
            })
        # Остальные пользователи не включаются в список, как было оговорено

    # Добавляем количество отфильтрованных репостов в ответ
    return JsonResponse({
        'reposts': repost_users_data,
        'filtered_count': len(repost_users_data)
    })




@login_required 
@require_POST 
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST) 
        
        images_files = request.FILES.getlist('images') 

        if form.is_valid():
            with transaction.atomic(): # Используем транзакцию для сохранения поста и вложений
                post = form.save(commit=False)
                post.author = request.user
                post.save() 

                for img_file in images_files:
                    PostAttachment.objects.create(post=post, image=img_file)
            
            return JsonResponse({'success': True, 'message': 'Пост успешно создан!', 'post_id': post.id})
        else:
            errors = json.dumps(form.errors.as_data())
            return JsonResponse({'success': False, 'message': 'Ошибка при создании поста.', 'errors': errors}, status=400)
    return JsonResponse({'success': False, 'message': 'Недопустимый метод запроса.'}, status=405)


@login_required
@require_POST
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        images_files = request.FILES.getlist('images') 
        
        if form.is_valid():
            with transaction.atomic(): # Используем транзакцию для сохранения поста и вложений
                form.save()

                # Добавление новых изображений
                for img_file in images_files:
                    PostAttachment.objects.create(post=post, image=img_file)

                # TODO: Если нужно удалять существующие изображения, нужна отдельная логика.
                # Например, можно передавать список ID изображений, которые нужно сохранить,
                # и удалять те, которых нет в списке.
            
            return JsonResponse({'success': True, 'message': 'Пост успешно обновлен!'})
        else:
            errors = json.dumps(form.errors.as_data())
            return JsonResponse({'success': False, 'message': 'Ошибка при обновлении поста.', 'errors': errors}, status=400)
    return JsonResponse({'success': False, 'message': 'Недопустимый метод запроса.'}, status=405)


@login_required
@require_POST
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == 'POST':
        post_id = post.id
        with transaction.atomic(): # Используем транзакцию для удаления поста
            post.delete()
        return JsonResponse({'success': True, 'message': 'Пост успешно удален.', 'deleted_post_id': post_id})
    return JsonResponse({'success': False, 'message': 'Недопустимый метод запроса.'}, status=405)


# Представление для детального просмотра поста
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # Увеличиваем счетчик просмотров
    # Для более надежного подсчета просмотров, особенно если у вас много трафика,
    # можно использовать кэширование, сессии или Celery для асинхронного обновления.
    # А пока такой простой вариант, он работает.
    post.views_count += 1
    post.save(update_fields=['views_count']) 

    # Форма для добавления комментария
    comment_form = CommentForm()

    # Для отображения лайкнул ли пользователь на детальной странице
    is_liked_by_user = False
    is_disliked_by_user = False
    is_reposted_by_user = False
    if request.user.is_authenticated:
        is_liked_by_user = post.likes.filter(id=request.user.id).exists()
        is_disliked_by_user = post.dislikes.filter(id=request.user.id).exists()
        is_reposted_by_user = post.reposts.filter(id=request.user.id).exists()

    post_images = []
    # post.attachments.all() предполагает, что у Post есть related_name 'attachments'
    # если это не так, вам нужно будет обратиться к PostAttachment.objects.filter(post=post)
    for attachment in post.attachments.all().order_by('id'):
        if attachment.image:
            post_images.append({
                'id': attachment.id,
                'url': request.build_absolute_uri(attachment.image.url) # Используем absolute_uri для полной URL
            })

    # Сериализуем список словарей в JSON-строку
    post_images_json = json.dumps(post_images, cls=DjangoJSONEncoder)

    return render(request, 'core/post_detail.html', {
        'post': post,
        'comment_form': comment_form,
        'is_liked': is_liked_by_user,
        'is_disliked': is_disliked_by_user,
        'is_reposted': is_reposted_by_user,
        'post_images_json': post_images_json,
    })


# Представления для лайков/дизлайков/репостов и комментариев
@login_required
@require_POST
def post_like(request, pk):
    post = get_object_or_404(Post, pk=pk)
    user = request.user
    
    action = 'liked'
    if user in post.likes.all():
        post.likes.remove(user)
        action = 'unliked'
    else:
        post.likes.add(user)
        # Если пользователь лайкнул, убираем дизлайк, если он был
        if user in post.dislikes.all():
            post.dislikes.remove(user)
    
    return JsonResponse({
        'success': True,
        'action': action,
        'likes_count': post.total_likes,
        'dislikes_count': post.total_dislikes
    })

@login_required
@require_POST
def post_dislike(request, pk):
    post = get_object_or_404(Post, pk=pk)
    user = request.user
    
    action = 'disliked'
    if user in post.dislikes.all():
        post.dislikes.remove(user)
        action = 'undisliked'
    else:
        post.dislikes.add(user)
        # Если пользователь дизлайкнул, убираем лайк, если он был
        if user in post.likes.all():
            post.likes.remove(user)

    return JsonResponse({
        'success': True,
        'action': action,
        'likes_count': post.total_likes,
        'dislikes_count': post.total_dislikes
    })

@login_required
@require_POST
def post_repost(request, pk):
    post = get_object_or_404(Post, pk=pk)
    user = request.user
    
    action = 'reposted'
    if user in post.reposts.all():
        post.reposts.remove(user)
        action = 'unreposted'
    else:
        post.reposts.add(user)

    return JsonResponse({
        'success': True,
        'action': action,
        'reposts_count': post.total_reposts
    })

@login_required
@require_POST
def add_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()

        # Возвращаем информацию о новом комментарии
        return JsonResponse({
            'success': True, 
            'message': 'Комментарий успешно добавлен!',
            'comment': {
                'id': comment.id,
                'author_username': comment.author.username,
                'text': comment.text,
                'created_at': comment.created_at.isoformat(), 
                'total_comments': post.total_comments, 
            }
        })
    else:
        errors = json.dumps(form.errors.as_data())
        return JsonResponse({'success': False, 'message': 'Ошибка при добавлении комментария.', 'errors': errors}, status=400)