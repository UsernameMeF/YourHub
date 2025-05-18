import os
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_delete
from django.dispatch import receiver
from django.conf import settings 
from PIL import Image 


def profile_avatar_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f'avatar.{ext}'
    return os.path.join('profile_avatars', str(instance.user.id), new_filename)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(default='images/default-avatar.png', upload_to=profile_avatar_upload_path)

    def __str__(self):
        return f'{self.user.username} Profile'


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
                print(f"Error processing image for user {self.user.username}: {e}")



@receiver(post_delete, sender=Profile)
def auto_delete_avatar_on_delete(sender, instance, **kwargs):
    if instance.avatar:
        if 'default-avatar.png' not in instance.avatar.path:
            if os.path.exists(instance.avatar.path):
                os.remove(instance.avatar.path)
                user_dir = os.path.dirname(instance.avatar.path)
                if os.path.exists(user_dir) and not os.listdir(user_dir):
                     os.rmdir(user_dir)