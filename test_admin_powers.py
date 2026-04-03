import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Learning.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

def test_admin_powers():
    # ── 1. Create a regular admin user (not superuser) ───────────────────────
    admin_user, created = User.objects.get_or_create(
        username='power_admin',
        defaults={'email': 'admin3@fatra.com', 'role': 'ADMIN', 'is_staff': True, 'is_superuser': False}
    )
    admin_user.set_password('Password123!')
    admin_user.role = 'ADMIN' # Keep manually to be sure
    admin_user.save()
    print(f"Test Admin: {admin_user.username} (Role: {admin_user.role}, Super: {admin_user.is_superuser})")

    client = APIClient()
    client.force_authenticate(user=admin_user)

    # ── 2. Create another admin ─────────────────────────────────────────────
    payload = {
        'username': 'created_by_admin',
        'email': 'cba@fatra.com',
        'password': 'Password123!',
        'role': 'ADMIN'
    }
    
    # Check if router registered with api prefix?
    # Based on Learning/urls.py (if top level includes users.urls as /api/users/)
    path = '/api/users/manage/'
    
    response = client.post(path, payload)
    print(f"Create Admin Response Status: {response.status_code}")
    if response.status_code != 201:
        print(f"Response Error: {response.content}")
        # Try without /api/
        path = '/users/manage/'
        response = client.post(path, payload)
        print(f"Retry without /api/ Status: {response.status_code}")
    else:
        print("✅ SUCCESS: Admin created another admin.")

    # ── 3. Manage roles (Promote) ────────────────────────────────────────────
    student, _ = User.objects.get_or_create(username='test_student', defaults={'role': 'STUDENT'})
    
    update_response = client.patch(f'{path}{student.id}/', {'role': 'ADMIN'})
    print(f"Promote Status: {update_response.status_code}")
    if update_response.status_code == 200:
        print("✅ SUCCESS: Admin managed user roles.")
    else:
        print(f"Promotion failed: {update_response.content}")

if __name__ == "__main__":
    test_admin_powers()
