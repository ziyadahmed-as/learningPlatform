from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

class AdminUserTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='admin_test',
            password='password123',
            role='ADMIN'
        )
        self.student = User.objects.create_user(
            username='student_test',
            password='password123',
            role='STUDENT'
        )

    def test_admin_can_access_user_manage(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/users/manage/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return both admin and student
        self.assertEqual(len(response.data), 2)

    def test_student_cannot_access_user_manage(self):
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/users/manage/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
