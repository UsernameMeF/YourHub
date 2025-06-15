from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.db import transaction
from django.db.models import Count, Q
from .forms import CommunityCreationForm 
from .models import Community, CommunityMembership 
from django.views.decorators.http import require_POST
from django.urls import reverse
import json
from django.conf import settings
from users.models import Profile, Friendship

from .forms import CommunityCreationForm, CommunityUpdateForm, CommunityPostForm, CommunityCommentForm
from .models import Community, CommunityMembership, CommunityPost, CommunityComment 

@login_required
def community_create_view(request):
    if request.method == 'POST':
        form = CommunityCreationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                community = form.save(commit=False)
                community.creator = request.user
                community.save()
                
                CommunityMembership.objects.create(
                    user=request.user,
                    community=community,
                    is_admin=True
                )
            return redirect('community:community_detail', pk=community.id)
        else:
            pass
    else:
        form = CommunityCreationForm()
    
    return render(request, 'community/community_create.html', {'form': form})


@login_required
def community_detail_view(request, pk):
    community = get_object_or_404(
        Community.objects.prefetch_related('members').annotate(
            members_count=Count('members', distinct=True)
        ),
        id=pk
    )
    
    is_member = False
    is_creator = False
    if request.user.is_authenticated:
        is_member = community.members.filter(id=request.user.id).exists()
        is_creator = (request.user == community.creator)
    

    first_members = community.members.all().order_by('?')[:7]

    last_post = CommunityPost.objects.filter(community=community).order_by('-created_at').first()

    context = {
        'community': community,
        'is_member': is_member,
        'is_creator': is_creator,
        'first_members': first_members,
        'last_post': last_post,
    }

    return render(request, 'community/community_detail.html', context)


@login_required
@transaction.atomic
def community_toggle_membership(request, pk):
    community = get_object_or_404(Community, id=pk)
    user = request.user
    
    membership_exists = CommunityMembership.objects.filter(user=user, community=community).exists()
    
    if membership_exists:
        if user == community.creator:
            return JsonResponse({'success': False, 'message': 'Создатель не может отписаться от своего сообщества.'}, status=403)
        
        CommunityMembership.objects.filter(user=user, community=community).delete()
        action = 'left'
        message = 'Вы успешно отписались от сообщества.'
    else:
        CommunityMembership.objects.create(user=user, community=community)
        action = 'joined'
        message = 'Вы успешно присоединились к сообществу!'
    
    updated_members_count = community.members.count()

    return JsonResponse({
        'success': True,
        'action': action,
        'members_count': updated_members_count,
        'is_member': not membership_exists,
        'message': message
    })


@login_required
def community_edit_view(request, pk):
    community = get_object_or_404(Community, pk=pk)

    if request.user != community.creator:
        return redirect('community:community_detail', pk=community.pk)

    if request.method == 'POST':
        form = CommunityUpdateForm(request.POST, instance=community)
        if form.is_valid():
            form.save()
            return redirect('community:community_detail', pk=community.pk)
    else:
        form = CommunityUpdateForm(instance=community)
    
    context = {
        'form': form,
        'community': community,
    }
    return render(request, 'community/community_edit.html', context)


@login_required
def community_delete_view(request, pk):
    community = get_object_or_404(Community, pk=pk)

    if request.user != community.creator:
        return redirect('community:community_detail', pk=community.pk)

    if request.method == 'POST':
        community.delete()
        return redirect('community:user_communities')
    
    context = {
        'community': community,
    }
    return render(request, 'community/community_confirm_delete.html', context)

@login_required
def user_communities_view(request):
    user_communities = Community.objects.filter(
        members=request.user
    ).annotate(
        members_count=Count('members', distinct=True)
    ).order_by('-created_at')

    return render(request, 'community/user_communities.html', {
        'user_communities': user_communities
    })

@login_required
@transaction.atomic 
def community_post_create_view(request, pk):
    community = get_object_or_404(Community, pk=pk)

    if request.user != community.creator:
        return HttpResponseForbidden("Только создатель сообщества может создавать публикации.")

    if request.method == 'POST':
        post_form = CommunityPostForm(request.POST)

        if post_form.is_valid():
            post = post_form.save(commit=False)
            post.community = community
            post.posted_by = request.user
            post.save() 
            
            return redirect('community:community_detail', pk=community.pk)
        else:
            print(post_form.errors)
    else:
        post_form = CommunityPostForm()
    
    context = {
        'community': community,
        'post_form': post_form,
    }
    return render(request, 'community/community_post_create.html', context)


def community_post_detail_view(request, pk, post_pk):
    community = get_object_or_404(Community, pk=pk)
    post = get_object_or_404(
        CommunityPost.objects.select_related('posted_by'), 
        pk=post_pk, 
        community=community
    )

    post.views_count += 1
    post.save(update_fields=['views_count']) 

    comment_form = CommunityCommentForm()
    comments = post.comments.select_related('author__profile').order_by('created_at')

    is_liked_by_user = False
    is_disliked_by_user = False
    is_reposted_by_user = False
    if request.user.is_authenticated:
        is_liked_by_user = post.likes.filter(id=request.user.id).exists()
        is_disliked_by_user = post.dislikes.filter(id=request.user.id).exists()
        is_reposted_by_user = post.reposts.filter(id=request.user.id).exists()

    context = {
        'community': community,
        'post': post,
        'comment_form': comment_form,
        'comments': comments,
        'is_liked': is_liked_by_user,
        'is_disliked': is_disliked_by_user,
        'is_reposted': is_reposted_by_user,
    }
    return render(request, 'community/community_post_detail.html', context)


@login_required
@require_POST
def community_post_like(request, pk, post_pk):
    post = get_object_or_404(CommunityPost, pk=post_pk, community__pk=pk)
    user = request.user
    
    action = 'liked'
    if user in post.likes.all():
        post.likes.remove(user)
        action = 'unliked'
    else:
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
def community_post_dislike(request, pk, post_pk):
    post = get_object_or_404(CommunityPost, pk=post_pk, community__pk=pk)
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
def community_post_repost(request, pk, post_pk):
    post = get_object_or_404(CommunityPost, pk=post_pk, community__pk=pk)
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
def community_post_reposts_ajax(request, pk, post_pk):
    community = get_object_or_404(Community, pk=pk)
    post = get_object_or_404(CommunityPost, pk=post_pk, community=community)
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

    following_ids = set(current_user.following.all().values_list('following__id', flat=True))
    
    for user in all_repost_users:
        avatar_url = user.profile.avatar.url if hasattr(user, 'profile') and user.profile.avatar else settings.STATIC_URL + 'images/default_avatar.png'
        
        if user == current_user:
            repost_users_data.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': avatar_url,
                'relationship': 'Вы', 
            })
        elif user in friends:
            repost_users_data.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': avatar_url,
                'relationship': 'Друг',
            })
        elif user.id in following_ids:
            repost_users_data.append({
                'id': user.id,
                'username': user.username,
                'avatar_url': avatar_url,
                'relationship': 'Подписка',
            })

    repost_users_data.sort(key=lambda x: (x['relationship'] != 'Вы', x['relationship'] != 'Друг', x['relationship'] != 'Подписка', x['username']))

    return JsonResponse({
        'success': True,
        'reposts': repost_users_data,
        'reposts_count': post.total_reposts,
        'filtered_count': len(repost_users_data)
    })

@login_required
@require_POST
def community_add_comment(request, pk, post_pk):
    community = get_object_or_404(Community, pk=pk)
    post = get_object_or_404(CommunityPost, pk=post_pk, community=community)
    
    form = CommunityCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()

        author_avatar_url = comment.author.profile.avatar.url if hasattr(comment.author, 'profile') and comment.author.profile.avatar else settings.STATIC_URL + 'images/default_avatar.png'
        
        return JsonResponse({
            'success': True,
            'comment': {
                'author_id': comment.author.id,
                'author_username': comment.author.username,
                'author_avatar_url': author_avatar_url,
                'text': comment.text,
                'created_at': comment.created_at.strftime("%d %b %Y, %H:%M"), 
                'total_comments': post.total_comments, 
            }
        })
    else:
        errors = form.errors.as_json()
        return JsonResponse({
            'success': False,
            'message': 'Ошибка валидации комментария. Возможно, текст слишком короткий или длинный.',
            'errors': json.loads(errors)
        }, status=400) 


@login_required
@require_POST
def community_post_delete_ajax(request, pk, post_pk):
    community = get_object_or_404(Community, pk=pk)
    post = get_object_or_404(CommunityPost, pk=post_pk, community=community)

    is_community_admin = CommunityMembership.objects.filter(
        user=request.user, community=community, is_admin=True
    ).exists()

    if request.user == post.posted_by or is_community_admin:
        post.delete()
        return JsonResponse({'success': True, 'message': 'Пост успешно удален.'})
    else:
        return JsonResponse({'success': False, 'message': 'У вас нет прав для удаления этого поста.'}, status=403) 


def community_search_view(request):
    query = request.GET.get('q')
    communities = Community.objects.all()

    if query:
        communities = communities.filter(Q(name__icontains=query)).annotate(
            members_count=Count('members', distinct=True)
        ).order_by('name')
    else:
        communities = communities.annotate(
            members_count=Count('members', distinct=True)
        ).order_by('-created_at')

    context = {
        'communities': communities,
        'query': query if query else '',
        'title': 'Поиск сообществ',
    }
    return render(request, 'community/community_search.html', context)