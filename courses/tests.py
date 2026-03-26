from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import Category, Course, Chapter, Lesson, ContentBlock, LessonProgress, Enrollment
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile

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
            is_approved=True,
        )
        self.chapter = Chapter.objects.create(course=self.course, title='Getting Started', order=1)
        # Lesson no longer has 'content' field
        self.lesson = Lesson.objects.create(chapter=self.chapter, title='Setup', order=1)
        # Add a text content block to the lesson
        self.block = ContentBlock.objects.create(
            lesson=self.lesson, 
            type='text', 
            text_content='Install Django and DRF', 
            order=1
        )

    def test_get_courses_list(self):
        """Students/anonymous only see approved courses"""
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

    def test_student_enroll_free_course(self):
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

    def test_lesson_detail_includes_blocks(self):
        """Verify lesson detail API returns nested content blocks"""
        self.client.force_authenticate(user=self.instructor)
        response = self.client.get(f'/api/courses/lessons/{self.lesson.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['content_blocks']), 1)
        self.assertEqual(response.data['content_blocks'][0]['text_content'], 'Install Django and DRF')

    def test_create_content_block_instructor(self):
        """Instructor can add blocks to their lesson"""
        self.client.force_authenticate(user=self.instructor)
        data = {
            'lesson': self.lesson.id,
            'type': 'video_link',
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'title': 'Intro Video',
            'order': 2
        }
        response = self.client.post('/api/courses/content-blocks/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContentBlock.objects.count(), 2)

    def test_create_content_block_unauthorized(self):
        """Student cannot add blocks"""
        self.client.force_authenticate(user=self.student)
        data = {
            'lesson': self.lesson.id,
            'type': 'text',
            'text_content': 'Hacker content'
        }
        response = self.client.post('/api/courses/content-blocks/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_lesson_progress_watched_seconds(self):
        """Student can update watched_seconds for engagement analytics"""
        # Enroll first
        Enrollment.objects.create(student=self.student, course=self.course, is_paid=True)
        self.client.force_authenticate(user=self.student)
        
        data = {'watched_seconds': 120}
        response = self.client.post(f'/api/courses/lessons/{self.lesson.id}/update_progress/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        progress = LessonProgress.objects.get(student=self.student, lesson=self.lesson)
        self.assertEqual(progress.watched_seconds, 120)

    def test_sequential_progression(self):
        """Verify students must complete previous lesson to mark next as completed"""
        Enrollment.objects.create(student=self.student, course=self.course, is_paid=True)
        lesson2 = Lesson.objects.create(chapter=self.chapter, title='Second Lesson', order=2)
        
        self.client.force_authenticate(user=self.student)
        # Try to complete lesson2 without completing lesson1
        response = self.client.post(f'/api/courses/lessons/{lesson2.id}/mark_completed/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('previous lesson', response.data['detail'])

        # Complete lesson1
        self.client.post(f'/api/courses/lessons/{self.lesson.id}/mark_completed/')
        
        # Now lesson2 should work
        response = self.client.post(f'/api/courses/lessons/{lesson2.id}/mark_completed/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_instructor_stats_completion_rate(self):
        """Verify instructor stats calculates completion % correctly with new blocks"""
        Enrollment.objects.create(student=self.student, course=self.course, is_paid=True)
        LessonProgress.objects.create(student=self.student, lesson=self.lesson, is_completed=True)
        
        self.client.force_authenticate(user=self.instructor)
        response = self.client.get('/api/courses/courses/instructor_stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        course_stat = response.data['courses'][0]
        self.assertEqual(course_stat['completion_percentage'], 100.0)

    def test_file_upload_content_block(self):
        """Test image upload to a content block"""
        self.client.force_authenticate(user=self.instructor)
        image = SimpleUploadedFile("test.jpg", b"file_content", content_type="image/jpeg")
        data = {
            'lesson': self.lesson.id,
            'type': 'image',
            'file': image,
            'order': 3
        }
        response = self.client.post('/api/courses/content-blocks/', data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ContentBlock.objects.get(id=response.data['id']).file.name.endswith('.jpg'))
