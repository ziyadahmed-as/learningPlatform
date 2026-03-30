from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Category, Course, Chapter, Lesson, ContentBlock, LiveStream
)
from interactions.models import Enrollment, LessonProgress
from .serializers import (
    CategorySerializer, CourseSerializer, ChapterSerializer,
    LessonSerializer, ContentBlockSerializer, LiveStreamSerializer
)
from django.db.models import Sum
from ai.services import AIService
import decimal

def is_admin(user):
    return user.is_authenticated and (user.role == 'ADMIN' or user.is_superuser)

class IsAdminOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_admin(request.user)

class IsAdminOrInstructorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.role in ['ADMIN', 'INSTRUCTOR'] or request.user.is_superuser)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if is_admin(request.user):
            return True
        if hasattr(obj, 'instructor'):
            return obj.instructor == request.user
        if hasattr(obj, 'course'):
            return obj.course.instructor == request.user
        if hasattr(obj, 'chapter'):
            return obj.chapter.course.instructor == request.user
        if hasattr(obj, 'lesson'):
            return obj.lesson.chapter.course.instructor == request.user
        return False

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOnly]

class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (is_admin(user) or user.role == 'INSTRUCTOR'):
            return Course.objects.all().select_related('instructor', 'category').prefetch_related('chapters__lessons')
        return Course.objects.filter(is_approved=True).select_related('instructor', 'category').prefetch_related('chapters__lessons')

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if not is_admin(request.user):
            return Response({'detail': 'Only admins can approve.'}, status=403)
        course = self.get_object()
        course.is_approved = True
        course.save()
        return Response({'detail': f'Course {course.title} approved.'})

    @action(detail=True, methods=['post'])
    def submit_for_approval(self, request, pk=None):
        course = self.get_object()
        course.is_submitted = True
        course.save()
        return Response({'detail': 'Submitted for approval.'})

    @action(detail=True, methods=['post'], url_path='generate-ai-description')
    def generate_ai_description(self, request, pk=None):
        """AI tool for instructors to generate course descriptions."""
        course = self.get_object()
        keywords = request.data.get('keywords', '')
        audience = request.data.get('audience', '')
        
        description = AIService.generate_course_description(course.title, audience, keywords)
        course.description = description
        course.save(update_fields=['description'])
        
        return Response({'description': description})

    @action(detail=True, methods=['post'], url_path='generate-ai-curriculum')
    def generate_ai_curriculum(self, request, pk=None):
        """AI tool for instructors to generate a suggested course structure."""
        course = self.get_object()
        curriculum = AIService.generate_course_curriculum(course.title)
        
        # Optionally auto-create chapters and lessons if requested
        auto_create = request.data.get('auto_create', False)
        if auto_create and isinstance(curriculum, list):
            for i, chap_data in enumerate(curriculum):
                chapter = Chapter.objects.create(
                    course=course, 
                    title=chap_data.get('chapter_title', f'Chapter {i+1}'),
                    order=i
                )
                for j, lesson_title in enumerate(chap_data.get('lessons', [])):
                    Lesson.objects.create(
                        chapter=chapter,
                        title=lesson_title,
                        order=j
                    )
        
        return Response({'curriculum': curriculum})

    @action(detail=False, methods=['get'])
    def instructor_stats(self, request):
        user = request.user
        if user.role not in ['INSTRUCTOR', 'ADMIN'] and not user.is_superuser:
            return Response({'detail': 'Forbidden.'}, status=403)

        courses = Course.objects.filter(instructor=user) if user.role == 'INSTRUCTOR' else Course.objects.all()
        
        total_enrollments = Enrollment.objects.filter(course__in=courses).count()
        total_views = courses.aggregate(total=Sum('views_count'))['total'] or 0

        return Response({
            'total_courses': courses.count(),
            'total_enrollments': total_enrollments,
            'total_views': total_views,
            'approved_count': courses.filter(is_approved=True).count(),
        })

class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]

class ContentBlockViewSet(viewsets.ModelViewSet):
    queryset = ContentBlock.objects.all()
    serializer_class = ContentBlockSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]

    @action(detail=True, methods=['post'], url_path='generate-ai-quiz')
    def generate_ai_quiz(self, request, pk=None):
        """AI tool for instructors to generate a quiz for this lesson."""
        lesson = self.get_object()
        count = request.data.get('count', 5)
        difficulty = request.data.get('difficulty', 'medium')
        
        quiz = AIService.generate_quiz(lesson.title, count, difficulty)
        return Response({'quiz': quiz})

class LiveStreamViewSet(viewsets.ModelViewSet):
    queryset = LiveStream.objects.all()
    serializer_class = LiveStreamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)
