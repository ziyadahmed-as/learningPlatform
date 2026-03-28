from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
        ADMIN = 'ADMIN', 'Admin'

    role = models.CharField(max_length=50, choices=Role.choices, default=Role.STUDENT)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Instructor specific info
    expertise = models.CharField(max_length=255, blank=True, null=True)
    education_level = models.CharField(max_length=255, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    cv_url = models.URLField(blank=True, null=True) # or FileField for real CVs later

    def save(self, *args, **kwargs):
        # Ensure superusers are always recognized as ADMIN role in the frontend
        if self.is_superuser:
            self.role = self.Role.ADMIN
        
        # Admins and Instructors get staff access to the Django admin panel
        if self.role in [self.Role.ADMIN, self.Role.INSTRUCTOR]:
            self.is_staff = True
        else:
            self.is_staff = False
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
