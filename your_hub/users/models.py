import os
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_delete, post_save
from django.dispatch import receiver
from django.conf import settings 
from PIL import Image 
from django.utils import timezone


def profile_avatar_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f'avatar.{ext}'
    return os.path.join('profile_avatars', str(instance.user.id), new_filename)


class Profile(models.Model):
    STATUS_CHOICES = (
        ('online', 'В мережі'),
        ('away', 'Немає на місці'),
        ('dnd', 'Не турбувати'),
        ('invisible', 'Невидимий'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(default='images/default-avatar.png', upload_to=profile_avatar_upload_path)
    bio = models.TextField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="offline")
    last_activity = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        return f'Профіль {self.user.username}'


    def save(self, *args, **kwargs):
        try:
            old_profile = Profile.objects.get(pk=self.pk)
            if old_profile.avatar and self.avatar != old_profile.avatar:
                default_avatar_path = os.path.join(settings.STATIC_ROOT, 'images/default-avatar.png')
                if 'default-avatar.png' not in old_profile.avatar.path:
                    if os.path.exists(old_profile.avatar.path):
                        os.remove(old_profile.avatar.path)
                        user_dir = os.path.dirname(old_profile.avatar.path)
                        if os.path.exists(user_dir) and not os.listdir(user_dir):
                             os.rmdir(user_dir)

        except Profile.DoesNotExist:
            pass

        super().save(*args, **kwargs)


        if self.avatar:
            try:
                img = Image.open(self.avatar.path)

                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.avatar.path)
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"Помилка обробки зображення для користувача {self.user.username}: {e}")



@receiver(post_delete, sender=Profile)
def auto_delete_avatar_on_delete(sender, instance, **kwargs):
    if instance.avatar:
        if 'default-avatar.png' not in instance.avatar.path:
            if os.path.exists(instance.avatar.path):
                os.remove(instance.avatar.path)
                user_dir = os.path.dirname(instance.avatar.path)
                if os.path.exists(user_dir) and not os.listdir(user_dir):
                     os.rmdir(user_dir)


class Friendship(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Очікує підтвердження'),
        ('accepted', 'Прийнято'),
    )

    from_user = models.ForeignKey(User, related_name='sent_friend_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_friend_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('from_user', 'to_user')
        ordering = ['-created_at']


    def __str__(self):
        return f"Запит дружби від {self.from_user.username} до {self.to_user.username} ({self.status})"


    def accept(self):
        if self.status == 'pending':
            self.status = 'accepted'
            self.accepted_at = models.fields.timezone.now()
            self.save()


    def decline(self):
        if self.status == 'pending':
            self.delete()


class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    following = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    
    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.follower.username} підписаний на {self.following.username}'