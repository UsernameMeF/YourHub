from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from django.http import Http404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .models import Notification, UserNotificationSettings
from .forms import UserNotificationSettingsForm

class NotificationSettingsView(LoginRequiredMixin, View):
    template_name = 'settings/notification_settings.html'

    def get(self, request, *args, **kwargs):
        settings, created = UserNotificationSettings.objects.get_or_create(user=request.user)
        form = UserNotificationSettingsForm(instance=settings)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        settings = get_object_or_404(UserNotificationSettings, user=request.user)
        form = UserNotificationSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            return redirect('notifications:settings')
        return render(request, self.template_name, {'form': form})

class NotificationListView(LoginRequiredMixin, View):
    template_name = 'notifications/notification_list.html'
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        notifications = Notification.objects.filter(recipient=request.user).order_by('-timestamp')
        paginator = Paginator(notifications, self.paginate_by)
        page = request.GET.get('page', 1)

        try:
            notifications = paginator.page(page)
        except PageNotAnInteger:
            notifications = paginator.page(1)
        except EmptyPage:
            notifications = paginator.page(paginator.num_pages)
            if not notifications:
                notifications = []

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            html_content = ""
            for notification in notifications:
                html_content += render_to_string(
                    'notifications/_single_notification.html', 
                    {'notification': notification}, 
                    request=request
                )
            return JsonResponse({'notifications_html': html_content, 'has_next_page': notifications.has_next()})

        return render(request, self.template_name, {'notifications': notifications})

class UserNotificationSettingsAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        settings, created = UserNotificationSettings.objects.get_or_create(user=request.user)
        settings_data = model_to_dict(settings, exclude=['user'])
        return JsonResponse(settings_data)

class RecentNotificationsAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        one_week_ago = timezone.now() - timedelta(days=7)
        recent_notifications = Notification.objects.filter(
            recipient=request.user,
            timestamp__gte=one_week_ago
        ).order_by('-timestamp')[:10]

        notifications_data = []
        for notification in recent_notifications:
            data = {
                'id': notification.id,
                'type': notification.notification_type,
                'content': notification.content,
                'is_read': notification.is_read,
                'timestamp': notification.timestamp.isoformat(),
                'sender_username': notification.sender.username if notification.sender else None,
                'url': notification.get_absolute_url(),
            }
            notifications_data.append(data)
        return JsonResponse({'notifications': notifications_data})

class MarkNotificationAsReadAPIView(LoginRequiredMixin, View):
    def post(self, request, notification_id, *args, **kwargs):
        try:
            notification = Notification.objects.get(id=notification_id, recipient=request.user)
            if not notification.is_read:
                notification.is_read = True
                notification.save()
                return JsonResponse({'status': 'success', 'notification_id': notification_id})
            return JsonResponse({'status': 'already_read'})
        except Notification.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Уведомление не найдено'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

class UnreadNotificationCountAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return JsonResponse({'unread_count': unread_count})

class NotificationDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, notification_id, *args, **kwargs):
        try:
            notification = Notification.objects.get(id=notification_id, recipient=request.user)
            notification_html = render_to_string(
                'notifications/_single_notification.html',
                {'notification': notification},
                request=request
            )
            return JsonResponse({'status': 'success', 'notification_html': notification_html})
        except Notification.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Уведомление не найдено'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)