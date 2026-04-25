from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
        ADMIN = 'ADMIN', 'Admin'
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'

    role = models.CharField(max_length=50, choices=Role.choices, default=Role.STUDENT)
    
    def save(self, *args, **kwargs):
        # Superuser logic mapping to SUPER_ADMIN role
        if self.is_superuser:
            self.role = self.Role.SUPER_ADMIN
        
        # Access for Django admin panel (Admins & Super Admins)
        if self.role in [self.Role.ADMIN, self.Role.SUPER_ADMIN, self.Role.INSTRUCTOR]:
            self.is_staff = True
        else:
            self.is_staff = False
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

class InstructorProfile(models.Model):
    class InstructorType(models.TextChoices):
        VIDEO_CREATOR = 'VIDEO_CREATOR', 'Video Creator'
        LIVE_STREAMER = 'LIVE_STREAMER', 'Live Streamer'
        BOTH = 'BOTH', 'Both'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    instructor_type = models.CharField(max_length=20, choices=InstructorType.choices, default=InstructorType.VIDEO_CREATOR)
    expertise = models.CharField(max_length=255, blank=True, null=True)
    education_level = models.CharField(max_length=255, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    cv_file = models.FileField(upload_to='instructor_cvs/', blank=True, null=True)
    website = models.URLField(max_length=255, blank=True, null=True)
    portfolio = models.URLField(max_length=255, blank=True, null=True)
    proposed_courses = models.TextField(blank=True, null=True)
    is_approved_instructor = models.BooleanField(default=False)

    def __str__(self):
        return f"Instructor Profile of {self.user.username}"

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    points = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Student Profile of {self.user.username}"

# Signals to auto-create profiles
@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        InstructorProfile.objects.create(user=instance)
        StudentProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profiles(sender, instance, **kwargs):
    instance.profile.save()
    instance.instructor_profile.save()
    instance.student_profile.save()
