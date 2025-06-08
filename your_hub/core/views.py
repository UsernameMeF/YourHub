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

from .forms import PostForm, PostDeleteForm, CommentForm
from .models import Post, PostAttachment, Comment 
from users.models import Friendship, Follow

User = get_user_model()

# Главная страница (лента постов)
def index(request):
    post_form = PostForm()

    context = {
        'post_form': post_form,
        # Если у вас есть другие переменные контекста для главной страницы, добавьте их здесь
    }
    return render(request, 'core/index.html', context) # Передаем контекст


# НОВАЯ ФУНКЦИЯ ДЛЯ AJAX-ЗАПРОСОВ ПОСТОВ
def get_posts_ajax(request):
    sort_by = request.GET.get('sort', 'new') 
    page = int(request.GET.get('page', 1)) 
    posts_per_page = 10

    posts_queryset = Post.objects.select_related('author__profile').prefetch_related(
        'attachments', 'likes', 'dislikes', 'reposts', 'comments'
    ).annotate(
        # Добавляем аннотации для всех счетчиков
        likes_count_annotated=Count('likes', distinct=True),
        dislikes_count_annotated=Count('dislikes', distinct=True),
        reposts_count_annotated=Count('reposts', distinct=True),
        comments_count_annotated=Count('comments', distinct=True)
    )

    if sort_by == 'popular':
        posts_queryset = posts_queryset.annotate(likes_count=Count('likes')).order_by('-likes_count', '-created_at')
    else: 
        posts_queryset = posts_queryset.order_by('-created_at')

    # Измененная логика пагинации: запрашиваем на 1 пост больше, чтобы определить has_next_page
    start_index = (page - 1) * posts_per_page
    end_index = start_index + posts_per_page

    # Запрашиваем на один элемент больше, чтобы понять, есть ли следующая страница
    # Если мы получили N+1 элементов, значит, N-ый элемент - последний на текущей странице,
    # а (N+1)-ый элемент означает, что есть следующая страница.
    posts_with_next_check = posts_queryset[start_index : end_index + 1]
    
    has_next_page = len(posts_with_next_check) > posts_per_page
    posts = posts_with_next_check[:posts_per_page] # Обрезаем до нужного количества постов для текущей страницы

    posts_data = []
    for post in posts:
        is_liked = False
        is_disliked = False
        is_reposted = False
        
        if request.user.is_authenticated:
            is_liked = post.likes.filter(id=request.user.id).exists()
            is_disliked = post.dislikes.filter(id=request.user.id).exists()
            is_reposted = post.reposts.filter(id=request.user.id).exists()

        author_avatar_url = request.build_absolute_uri(settings.STATIC_URL + 'images/default-avatar.png')
        if hasattr(post.author, 'profile') and post.author.profile.avatar:
            author_avatar_url = request.build_absolute_uri(post.author.profile.avatar.url)

        posts_data.append({
            'id': post.id,
            'author_username': post.author.username,
            'author_id': post.author.id,
            'author_avatar_url': author_avatar_url,
            'title': post.title,
            'content': post.content,
            'created_at': post.created_at.strftime("%d %b %Y %H:%M"),
            'updated_at': post.updated_at.strftime("%d %b %Y %H:%M") if post.updated_at and post.updated_at != post.created_at else None,
            'total_likes': post.total_likes, 
            'total_dislikes': post.total_dislikes, 
            'total_reposts': post.total_reposts, 
            'total_comments': post.total_comments, 
            'attachments': [{'url': att.image.url} for att in post.attachments.all()],
            'is_liked': is_liked,
            'is_disliked': is_disliked,
            'is_reposted': is_reposted,
            'can_edit_delete': request.user.is_authenticated and request.user == post.author 
        })

    return JsonResponse({
        'posts': posts_data,
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