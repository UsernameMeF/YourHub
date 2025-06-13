from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.forms.models import model_to_dict
from django.utils import timezone # Для фильтрации по дате
from datetime import timedelta # Для фильтрации по дате
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
            # Можно добавить сообщение об успешном сохранении
            # messages.success(request, 'Настройки уведомлений успешно сохранены.')
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
            notifications = paginator.page(paginator.num_pages) # Возвращаем последнюю страницу, если пользователь листает слишком далеко
            if not notifications: # Если даже на последней странице ничего нет (например, уведомлений вообще нет)
                notifications = []

        # Если это AJAX-запрос, отдаем только HTML фрагменты
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Используем тот же _single_notification.html для рендеринга каждого
            html_content = ""
            for notification in notifications:
                html_content += render_to_string(
                    'notifications/_single_notification.html', 
                    {'notification': notification}, 
                    request=request
                )
            return JsonResponse({'notifications_html': html_content, 'has_next_page': notifications.has_next()})

        return render(request, self.template_name, {'notifications': notifications})

# API для получения настроек уведомлений пользователя (для JavaScript)
class UserNotificationSettingsAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        settings, created = UserNotificationSettings.objects.get_or_create(user=request.user)
        settings_data = model_to_dict(settings, exclude=['user'])
        return JsonResponse(settings_data)

# API для получения последних уведомлений (для выпадающего меню)
class RecentNotificationsAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Уведомления за последнюю неделю, например
        one_week_ago = timezone.now() - timedelta(days=7)
        # Fetch recent notifications, order by timestamp, limit to a reasonable number
        recent_notifications = Notification.objects.filter(
            recipient=request.user,
            timestamp__gte=one_week_ago
        ).order_by('-timestamp')[:10] # Например, последние 10 уведомлений

        notifications_data = []
        for notification in recent_notifications:
            # Преобразование уведомления в словарь для JSON
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

# API для отметки уведомления как прочитанного
class MarkNotificationAsReadAPIView(LoginRequiredMixin, View):
    def post(self, request, notification_id, *args, **kwargs):
        try:
            notification = Notification.objects.get(id=notification_id, recipient=request.user)
            if not notification.is_read: # Помечаем как прочитанное только если еще не прочитано
                notification.is_read = True
                notification.save()
                return JsonResponse({'status': 'success', 'notification_id': notification_id})
            return JsonResponse({'status': 'already_read'})
        except Notification.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Уведомление не найдено'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# API для получения количества непрочитанных уведомлений
class UnreadNotificationCountAPIView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return JsonResponse({'unread_count': unread_count})

class NotificationDetailAPIView(LoginRequiredMixin, View):
    def get(self, request, notification_id, *args, **kwargs):
        try:
            notification = Notification.objects.get(id=notification_id, recipient=request.user)
            # Рендерим ОДНО уведомление с использованием того же шаблона, что и для списка
            # Но только часть, соответствующую одному li.notification-item
            notification_html = render_to_string(
                'notifications/_single_notification.html', # Создадим этот частичный шаблон
                {'notification': notification},
                request=request # Передаем request, чтобы работали {% static %} и другие контекстные переменные
            )
            return JsonResponse({'status': 'success', 'notification_html': notification_html})
        except Notification.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Уведомление не найдено'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
