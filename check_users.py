import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Learning.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

print(f"User Count: {User.objects.count()}")
for u in User.objects.all():
    print(f"ID: {u.id} | Username: {u.username} | Role: {u.role} | Email: {u.email}")
