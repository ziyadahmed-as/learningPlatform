from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Category, Course, Module, Lesson

User = get_user_model()

class CourseAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.instructor = User.objects.create_user(
            username='instructor_test',
            password='password123',
            role='INSTRUCTOR'
        )
        self.student = User.objects.create_user(
            username='student_test',
            password='password123',
            role='STUDENT'
        )
        self.category = Category.objects.create(name='Programming', slug='programming')
        self.course = Course.objects.create(
            title='Django REST Framework',
            slug='django-rest-framework',
            description='Learn DRF from scratch',
            instructor=self.instructor,
            category=self.category,
            price=49.99
        )
        self.module = Module.objects.create(course=self.course, title='Introduction', order=1)
        self.lesson = Lesson.objects.create(module=self.module, title='Setup', content='Install Django and DRF', order=1)

    def test_get_courses_list(self):
        """Ensure anyone can get the list of courses"""
        response = self.client.get('/api/courses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_course_instructor(self):
        """Ensure instructors can create courses"""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'title': 'React basics',
            'slug': 'react-basics',
            'description': 'React basics course',
            'category': self.category.id,
            'price': 19.99
        }
        response = self.client.post('/api/courses/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 2)

    def test_create_course_student(self):
        """Ensure students cannot create courses"""
        self.client.force_authenticate(user=self.student)
        data = {
            'title': 'Vue basics',
            'slug': 'vue-basics',
            'description': 'Vue basics course',
            'category': self.category.id
        }
        response = self.client.post('/api/courses/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_course(self):
        """Ensure admins can create courses"""
        admin = User.objects.create_user(
            username='admin_tester',
            password='password123',
            role='ADMIN'
        )
        self.client.force_authenticate(user=admin)
        data = {
            'title': 'Admin course',
            'slug': 'admin-course',
            'description': 'Admin course',
            'category': self.category.id
        }
        response = self.client.post('/api/courses/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_student_enroll_free_course(self):
        """Student enrolls in a free course"""
        self.client.force_authenticate(user=self.student)
        free_course = Course.objects.create(
            title='Free Course',
            slug='free-course',
            description='A free DRF course',
            instructor=self.instructor,
            category=self.category,
            price=0.00
        )
        response = self.client.post(f'/api/courses/{free_course.id}/enroll/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_paid'])

    def test_student_enroll_paid_course(self):
        """Student enrolls in a paid course, is_paid is False initially"""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['is_paid'])

    def test_student_cannot_enroll_twice(self):
        """Ensure duplicate enrollments return 400 bad request"""
        self.client.force_authenticate(user=self.student)
        # first enroll
        self.client.post(f'/api/courses/{self.course.id}/enroll/')
        # second enroll
        response2 = self.client.post(f'/api/courses/{self.course.id}/enroll/')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
