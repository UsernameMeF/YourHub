from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm 
from .models import Profile 
from django.conf import settings
from django.contrib.auth.views import LogoutView as BaseLogoutView 
from django.views.generic import FormView 


def register_view(request):
    if request.user.is_authenticated: 
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            messages.success(request, f'Аккаунт создан для {user.username}! Теперь вы можете войти.')
            return redirect('login')
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



@login_required 
def profile_view(request):
    user = request.user
    user_profile = user.profile

    user_posts = []
    user_friends = []
    user_activity = []

    context = {
        'user': user,
        'user_profile': user_profile,
        'user_posts': user_posts,
        'user_friends': user_friends,
        'user_activity': user_activity,
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
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
        # else:
             

    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileUpdateForm(instance=user_profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'users/edit_profile.html', context)

