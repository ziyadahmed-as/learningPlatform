from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Category, Course, Lesson

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
        self.admin = User.objects.create_user(
            username='admin_test',
            password='password123',
            role='ADMIN'
        )
        self.category = Category.objects.create(name='Programming', slug='programming')
        # Approved course visible to students
        self.course = Course.objects.create(
            title='Django REST Framework',
            slug='django-rest-framework',
            description='Learn DRF from scratch',
            instructor=self.instructor,
            category=self.category,
            price=49.99,
            is_published=True,
            is_approved=True,  # Approved so students can see and enroll
        )
        self.lesson = Lesson.objects.create(course=self.course, title='Setup', content='Install Django and DRF', order=1)

    def test_get_courses_list(self):
        """Students/anonymous only see approved courses"""
        # Create an unapproved course to confirm it's hidden
        Course.objects.create(
            title='Hidden Course',
            slug='hidden-course',
            description='Not approved',
            instructor=self.instructor,
            category=self.category,
            price=0,
            is_published=True,
            is_approved=False,
        )
        response = self.client.get('/api/courses/courses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only the approved setUp course should appear
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
        response = self.client.post('/api/courses/courses/', data)
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
        response = self.client.post('/api/courses/courses/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_course(self):
        """Ensure admins can create courses"""
        self.client.force_authenticate(user=self.admin)
        data = {
            'title': 'Admin course',
            'slug': 'admin-course',
            'description': 'Admin course',
            'category': self.category.id
        }
        response = self.client.post('/api/courses/courses/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_admin_can_approve_course(self):
        """Ensure admins can approve a course"""
        unapproved = Course.objects.create(
            title='Pending Course',
            slug='pending-course',
            description='Awaiting approval',
            instructor=self.instructor,
            category=self.category,
            price=0,
            is_published=True,
            is_approved=False,
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(f'/api/courses/courses/{unapproved.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        unapproved.refresh_from_db()
        self.assertTrue(unapproved.is_approved)

    def test_instructor_cannot_approve_course(self):
        """Ensure instructors cannot approve courses"""
        unapproved = Course.objects.create(
            title='Pending Course 2',
            slug='pending-course-2',
            description='Awaiting approval',
            instructor=self.instructor,
            category=self.category,
            price=0,
            is_published=True,
            is_approved=False,
        )
        self.client.force_authenticate(user=self.instructor)
        response = self.client.post(f'/api/courses/courses/{unapproved.id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_category(self):
        """Ensure admins can create categories"""
        self.client.force_authenticate(user=self.admin)
        data = {'name': 'Data Science', 'slug': 'data-science'}
        response = self.client.post('/api/courses/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_instructor_cannot_create_category(self):
        """Ensure instructors cannot create categories (admin-only)"""
        self.client.force_authenticate(user=self.instructor)
        data = {'name': 'AI', 'slug': 'ai'}
        response = self.client.post('/api/courses/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_enroll_free_course(self):
        """Student enrolls in a free approved course"""
        self.client.force_authenticate(user=self.student)
        free_course = Course.objects.create(
            title='Free Course',
            slug='free-course',
            description='A free DRF course',
            instructor=self.instructor,
            category=self.category,
            price=0.00,
            is_published=True,
            is_approved=True,
        )
        response = self.client.post(f'/api/courses/courses/{free_course.id}/enroll/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['is_paid'])

    def test_student_enroll_paid_course(self):
        """Student enrolls in a paid course, is_paid is False initially"""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(f'/api/courses/courses/{self.course.id}/enroll/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['is_paid'])

    def test_student_cannot_enroll_twice(self):
        """Ensure duplicate enrollments return 400 bad request"""
        self.client.force_authenticate(user=self.student)
        self.client.post(f'/api/courses/courses/{self.course.id}/enroll/')
        response2 = self.client.post(f'/api/courses/courses/{self.course.id}/enroll/')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unapproved_course_hidden_from_students(self):
        """Unapproved courses must not be accessible to students"""
        unapproved = Course.objects.create(
            title='Private Course',
            slug='private-course',
            description='Not yet approved',
            instructor=self.instructor,
            category=self.category,
            price=0,
            is_published=True,
            is_approved=False,
        )
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/courses/courses/{unapproved.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_record_view(self):
        """Ensure record_view increments view count and deduplicates"""
        # First view
        response = self.client.post(f'/api/courses/courses/{self.course.id}/record_view/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['views_count'], 1)
        
        # Second view from same IP (unauthenticated) within 24h should not increment
        response2 = self.client.post(f'/api/courses/courses/{self.course.id}/record_view/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(response2.data['views_count'], 1)
        
        # View from different user
        self.client.force_authenticate(user=self.student)
        response3 = self.client.post(f'/api/courses/courses/{self.course.id}/record_view/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(response3.data['views_count'], 2)

    def test_instructor_stats(self):
        """Ensure instructor_stats returns accurate aggregated data"""
        from .models import Enrollment, LessonProgress
        
        # Create an enrollment
        Enrollment.objects.create(student=self.student, course=self.course, is_paid=True)
        # Mark lesson completed
        LessonProgress.objects.create(student=self.student, lesson=self.lesson, is_completed=True)
        # Record a view
        self.client.post(f'/api/courses/courses/{self.course.id}/record_view/', REMOTE_ADDR='127.0.0.1')
        
        self.client.force_authenticate(user=self.instructor)
        response = self.client.get('/api/courses/courses/instructor_stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data
        self.assertEqual(data['total_courses'], 1)
        self.assertEqual(data['total_enrollments'], 1)
        self.assertEqual(data['total_views'], 1)
        
        course_stat = data['courses'][0]
        self.assertEqual(course_stat['id'], self.course.id)
        self.assertEqual(course_stat['enrollment_count'], 1)
        self.assertEqual(course_stat['views_count'], 1)
        self.assertEqual(course_stat['completion_percentage'], 100.0)

    def test_instructor_stats_forbidden_for_students(self):
        """Ensure students cannot access instructor stats"""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/courses/courses/instructor_stats/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
