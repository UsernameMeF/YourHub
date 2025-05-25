from django.utils import timezone
from django.db import connection


class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile'):
                def update_activity():
                    request.user.profile.last_activity = timezone.now()
                    request.user.profile.save(update_fields=['last_activity'])

                connection.on_commit(update_activity)

        return response
