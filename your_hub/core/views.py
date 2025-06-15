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
from notifications.utils import send_notification_to_user

from .forms import PostForm, PostDeleteForm, CommentForm
from .models import Post, PostAttachment, Comment, Tag
from users.models import Friendship, Follow
from community.models import Community, CommunityPost 


User = get_user_model()

def process_and_assign_tags(post, tags_input_string):
    post.tags.clear() 

    author_tag_name_clean = f"@{post.author.username}".lower()
    
    try:
        author_tag, created = Tag.objects.get_or_create(name=author_tag_name_clean) 
        post.tags.add(author_tag)
    except Exception as e:
        print(f"Помилка при створенні/додаванні тегу автора '{author_tag_name_clean}': {e}") # Translated


    if tags_input_string:
        user_tags_clean = set(tag.strip().lower() for tag in tags_input_string.split() if tag.strip())
        
        current_user_tags_count = 0 
        
        for clean_tag_name in user_tags_clean:
            if clean_tag_name == author_tag_name_clean:
                continue
            
            if post.tags.count() >= 11:
                break

            try:
                tag_obj, created = Tag.objects.get_or_create(name=clean_tag_name)
                post.tags.add(tag_obj)
                current_user_tags_count += 1
            except Exception as e:
                print(f"Не вдалося додати тег '{clean_tag_name}': {e}") # Translated


def index(request):
    post_form = PostForm()

    context = {
        'post_form': post_form,
        'current_sort': request.GET.get('sort', 'new'),
        'current_view_type': request.GET.get('view', 'cards'),
        'current_tag_slug': request.GET.get('tag', ''),
        'current_tag_name': '',
    }

    tag_slug = request.GET.get('tag')
    if tag_slug:
        try:
            tag_obj = Tag.objects.get(slug=tag_slug)
            context['current_tag_name'] = tag_obj.name
        except Tag.DoesNotExist:
            context['current_tag_name'] = ''

    return render(request, 'core/index.html', context)


def get_posts_ajax(request):
    sort_by = request.GET.get('sort', 'new') 
    page_number = int(request.GET.get('page', 1)) 
    posts_per_page = 10
    
    tag_filter_slug = request.GET.get('tag')
    
    core_posts_queryset = Post.objects.all()
    community_posts_queryset = CommunityPost.objects.all() 

    if tag_filter_slug:
        core_posts_queryset = core_posts_queryset.filter(tags__slug=tag_filter_slug).distinct()
        community_posts_queryset = community_posts_queryset.none() 


    core_posts_queryset = core_posts_queryset.select_related('author__profile').prefetch_related(
        'attachments', 
        'likes', 'dislikes', 'reposts', 'comments', 'tags'
    )

    community_posts_queryset = community_posts_queryset.select_related(
        'posted_by__profile', 'community'
    ).prefetch_related(
        'likes', 'dislikes', 'reposts', 'comments' 
    )

    all_posts = []

    for post in core_posts_queryset:
        author_avatar_url = settings.STATIC_URL + 'images/default-avatar.png'
        if hasattr(post.author, 'profile') and post.author.profile.avatar and post.author.profile.avatar.name:
            author_avatar_url = request.build_absolute_uri(post.author.profile.avatar.url)
        
        attachments_data = [{'url': request.build_absolute_uri(att.image.url)} for att in post.attachments.all() if att.image]
        
        tags_data = []
        for tag in post.tags.all():
            is_author_tag = tag.name.startswith('@') 
            
            tag_url = None
            if not is_author_tag:
                tag_url = reverse('core:index') + f'?tag={tag.slug}' 
            
            tags_data.append({
                'name': '#' + tag.name,
                'url': tag_url 
            })

        all_posts.append({
            'id': post.pk,
            'is_community_post': False,
            'author_username': post.author.username,
            'author_id': post.author.id,
            'author_avatar_url': author_avatar_url,
            'title': post.title,
            'content': post.content,
            'created_at': post.created_at, 
            'updated_at': post.updated_at,
            'total_likes': post.total_likes, 
            'total_dislikes': post.total_dislikes, 
            'total_reposts': post.total_reposts, 
            'total_comments': post.total_comments, 
            'attachments': attachments_data,
            'tags': tags_data,
            'detail_url': reverse('core:post_detail', args=[post.pk]),
            'community_id': None,
            'community_name': None,
            'community_url': None,
        })

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
            'author_username': post.posted_by.username if post.posted_by else '[Видалений користувач]', # Translated
            'author_id': post.posted_by.id if post.posted_by else None,
            'author_avatar_url': author_avatar_url,
            'title': post.title, 
            'content': post.content,
            'created_at': post.created_at, 
            'updated_at': post.updated_at if hasattr(post, 'updated_at') and post.updated_at else post.created_at, 
            'total_likes': post.total_likes, 
            'total_dislikes': post.total_dislikes, 
            'total_reposts': post.total_reposts, 
            'total_comments': post.total_comments, 
            'attachments': [],
            'tags': [],
            'detail_url': reverse('community:community_post_detail', args=[post.community.pk, post.pk]),
            'community_id': post.community.pk,
            'community_name': post.community.name,
            'community_url': reverse('community:community_detail', args=[post.community.pk]),
            'community_avatar_url': community_avatar_url, 
        })

    if sort_by == 'popular':
        all_posts.sort(key=lambda p: (p['total_likes'] + p['total_dislikes'] + p['total_reposts'] + p['total_comments']), reverse=True)
    else:
        all_posts.sort(key=lambda p: p['created_at'], reverse=True)


    start_index = (page_number - 1) * posts_per_page
    end_index = start_index + posts_per_page
    
    posts_on_page = all_posts[start_index:end_index]
    has_next_page = len(all_posts) > end_index

    serialized_posts_data = []
    current_user_id = request.user.id if request.user.is_authenticated else None

    for post_data in posts_on_page:
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
                
                is_community_admin = False
                if request.user.is_authenticated and post_data['community_id']:
                    is_community_admin = Community.objects.filter(
                        pk=post_data['community_id'], 
                        communitymembership__user=request.user, 
                        communitymembership__is_admin=True
                    ).exists()
                
                post_data['can_edit_delete'] = (request.user.is_authenticated and 
                                                 (current_user_id == post_data['author_id'] or is_community_admin))

            else:
                post_data['is_liked'] = post_data['id'] in request.user._liked_posts_ids_cache
                post_data['is_disliked'] = post_data['id'] in request.user._disliked_posts_ids_cache
                post_data['is_reposted'] = post_data['id'] in request.user._reposted_posts_ids_cache
                
                post_data['can_edit_delete'] = (request.user.is_authenticated and 
                                                 current_user_id == post_data['author_id'])
        else:
            post_data['is_liked'] = False
            post_data['is_disliked'] = False
            post_data['is_reposted'] = False
            post_data['can_edit_delete'] = False

        post_data['created_at'] = post_data['created_at'].strftime("%d %b %Y, %H:%M")
        if 'updated_at' in post_data and post_data['updated_at']:
            post_data['updated_at'] = post_data['updated_at'].strftime("%d %b %Y, %H:%M")
        else:
            post_data['updated_at'] = None 

        serialized_posts_data.append(post_data)

    return JsonResponse({
        'posts': serialized_posts_data,
        'has_next_page': has_next_page
    })

@login_required
def create_post_page(request):
    form = PostForm()
    return render(request, 'core/create_post.html', {'form': form})


@login_required
def edit_post_page(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    
    initial_tags_for_form = []
    for tag in post.tags.all():
        if not tag.name.startswith('@'):
            initial_tags_for_form.append(f'#{tag.name}')
    initial_tags_string = " ".join(initial_tags_for_form)

    post_images = []
    for attachment in post.attachments.all().order_by('id'):
        if attachment.image:
            post_images.append({
                'id': attachment.id,
                'url': attachment.image.url 
            })
    
    form = PostForm(instance=post, initial={'tags_input': initial_tags_string})
    
    return render(request, 'core/edit_post.html', {
        'form': form, 
        'post': post, 
        'post_images_json': json.dumps(post_images, cls=DjangoJSONEncoder)
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
    ).select_related('from_user', 'to_user') 

    for fs in accepted_friendships:
        if fs.from_user == current_user:
            friends.add(fs.to_user)
        else:
            friends.add(fs.from_user)

    following_ids = set(current_user.following.values_list('following__id', flat=True))

    for user in all_repost_users:
        avatar_url = user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else '/media/images/default-avatar.png'
        
        if user == current_user:
            repost_users_data.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': avatar_url,
                'relationship': 'Ви (репостнули)', # Translated
            })
        elif user in friends:
            repost_users_data.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': avatar_url,
                'relationship': 'Друг', # Translated
            })
        elif user.id in following_ids: 
            repost_users_data.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': avatar_url,
                'relationship': 'Підписка', # Translated
            })

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
            with transaction.atomic(): 
                post = form.save(commit=False)
                post.author = request.user
                post.save() 
                
                tags_input_string = form.cleaned_data.get('tags_input')
                process_and_assign_tags(post, tags_input_string)

                for img_file in images_files:
                    PostAttachment.objects.create(post=post, image=img_file)
            
            return redirect(reverse('core:post_detail', args=[post.id]))
        else:
            return render(request, 'core/create_post.html', {'form': form})
    return redirect('core:index')


@login_required
@require_http_methods(["POST", "GET"])
def post_edit(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    
    if request.method == 'POST':
        initial_tags_for_form = []
        for tag in post.tags.all():
            if not tag.name.startswith('@'):
                initial_tags_for_form.append(f'#{tag.name}')
        initial_tags_string = " ".join(initial_tags_for_form)

        form = PostForm(request.POST, instance=post, initial={'tags_input': initial_tags_string})
        
        images_files = request.FILES.getlist('images') 
        
        if form.is_valid():
            with transaction.atomic(): 
                form.save()

                tags_input_string = form.cleaned_data.get('tags_input') 
                process_and_assign_tags(post, tags_input_string)

                existing_image_ids_json = request.POST.get('existing_image_ids')
                if existing_image_ids_json:
                    try:
                        existing_image_ids = json.loads(existing_image_ids_json)
                        post.attachments.exclude(id__in=existing_image_ids).delete()
                    except json.JSONDecodeError:
                        print("Помилка декодування JSON для existing_image_ids під час редагування допису.") # Translated
                else:
                    post.attachments.all().delete() 

                for img_file in images_files:
                    if img_file:
                        PostAttachment.objects.create(post=post, image=img_file)
            
            return redirect(reverse('core:post_detail', args=[post.id]))
        else:
            post_images = []
            for attachment in post.attachments.all().order_by('id'):
                if attachment.image:
                    post_images.append({
                        'id': attachment.id,
                        'url': attachment.image.url 
                    })
            return render(request, 'core/edit_post.html', {
                'form': form, 
                'post': post, 
                'post_images_json': json.dumps(post_images, cls=DjangoJSONEncoder)
            })
    else:
        raise Http404("Сторінка редагування доступна через окремий URL.") # Translated


@login_required
@require_POST
def post_delete(request, pk):
    post = get_object_or_404(Post, pk=pk, author=request.user)
    if request.method == 'POST':
        post_id = post.id
        with transaction.atomic(): 
            post.delete()
        return JsonResponse({'success': True, 'message': 'Допис успішно видалено.', 'deleted_post_id': post_id, 'redirect_url': reverse('core:index')}) # Translated
    return JsonResponse({'success': False, 'message': 'Недопустимий метод запиту.'}, status=405) # Translated



def post_detail(request, pk):
    post = get_object_or_404(Post.objects.select_related('author__profile').prefetch_related('tags', 'comments__author__profile', 'attachments'), pk=pk) 
    
    post.views_count += 1
    post.save(update_fields=['views_count']) 

    comment_form = CommentForm()

    is_liked_by_user = False
    is_disliked_by_user = False
    is_reposted_by_user = False
    if request.user.is_authenticated:
        is_liked_by_user = post.likes.filter(id=request.user.id).exists()
        is_disliked_by_user = post.dislikes.filter(id=request.user.id).exists()
        is_reposted_by_user = post.reposts.filter(id=request.user.id).exists()

    post_images = []
    for attachment in post.attachments.all().order_by('id'):
        if attachment.image:
            post_images.append({
                'id': attachment.id,
                'url': request.build_absolute_uri(attachment.image.url) 
            })

    post_tags = []
    for tag in post.tags.all(): 
        is_author_tag = tag.name.startswith('@') 
        
        tag_url = None
        if not is_author_tag:
            tag_url = reverse('core:index') + f'?tag={tag.slug}' 
        
        post_tags.append({
            'name': '#' + tag.name,
            'url': tag_url 
        })
    

    post_images_json = json.dumps(post_images, cls=DjangoJSONEncoder)

    return render(request, 'core/post_detail.html', {
        'post': post,
        'comment_form': comment_form,
        'is_liked': is_liked_by_user,
        'is_disliked': is_disliked_by_user,
        'is_reposted': is_reposted_by_user,
        'post_images_json': post_images_json,
        'post_tags': post_tags, 
    })


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
        if post.author != user:
            recipient = post.author
            sender_user = user
            notification_type = 'like'
            content = f"{sender_user.username} оцінив(ла) ваш допис: \"{post.title}\"" # Translated
            related_object = post 
            custom_url = reverse('core:post_detail', args=[post.id]) 

            send_notification_to_user(
                recipient=recipient,
                sender=sender_user,
                notification_type=notification_type,
                content=content,
                related_object=related_object,
                custom_url=custom_url
            )
            print(f"DEBUG: Сповіщення 'вподобання' надіслано {recipient.username} від {sender_user.username} щодо допису {post.id}") # Translated
        post.likes.add(user)
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
        if post.author != user:
            recipient = post.author
            sender_user = user
            notification_type = 'repost'
            content = f"{sender_user.username} репостнув(ла) ваш допис: \"{post.title}\"" # Translated
            related_object = post 
            custom_url = reverse('core:post_detail', args=[post.id]) 

            send_notification_to_user(
                recipient=recipient,
                sender=sender_user,
                notification_type=notification_type,
                content=content,
                related_object=related_object,
                custom_url=custom_url
            )
            print(f"DEBUG: Сповіщення 'репост' надіслано {recipient.username} від {sender_user.username} щодо допису {post.id}") # Translated
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

        if post.author != request.user:
            recipient = post.author
            sender_user = request.user
            notification_type = 'comment'
            display_content = comment.text
            if len(display_content) > 50:
                display_content = display_content[:47] + '...'
            
            content = f"{sender_user.username} прокоментував(ла) ваш допис: \"{display_content}\"" # Translated
            related_object = comment 
            custom_url = reverse('core:post_detail', args=[post.id]) 

            send_notification_to_user(
                recipient=recipient,
                sender=sender_user,
                notification_type=notification_type,
                content=content,
                related_object=related_object,
                custom_url=custom_url
            )
            print(f"DEBUG: Сповіщення 'коментар' надіслано {recipient.username} від {sender_user.username} щодо допису {post.id}") # Translated

        return JsonResponse({
            'success': True, 
            'message': 'Коментар успішно додано!', # Translated
            'comment': {
                'id': comment.id,
                'author_username': comment.author.username,
                'text': comment.text,
                'created_at': comment.created_at.isoformat(), 
                'total_comments': post.total_comments, 
            }
        })
    else:
        errors = {field: form.errors[field] for field in form.errors} 
        return JsonResponse({'success': False, 'message': 'Помилка при додаванні коментаря.', 'errors': errors}, status=400) # Translated