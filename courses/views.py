from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Category, Course, Chapter, Lesson, ContentBlock, LiveStream, LiveSession
)
from interactions.models import Enrollment, LessonProgress, LiveStreamEnrollment, InstructorReview
from .serializers import (
    CategorySerializer, CourseSerializer, ChapterSerializer,
    LessonSerializer, ContentBlockSerializer, LiveStreamSerializer, LiveSessionSerializer
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
        if hasattr(obj, 'live_stream'):
            return obj.live_stream.instructor == request.user
        if hasattr(obj, 'live_session'):
            return obj.live_session.live_stream.instructor == request.user
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
        qs = Course.objects.all().select_related('instructor', 'category').prefetch_related('chapters__lessons')
        
        if not user.is_authenticated:
            return qs.filter(is_approved=True)

        # Dashboard dynamic filtering
        is_enrolled_filter = self.request.query_params.get('enrolled', 'false') == 'true'
        is_mine_filter = self.request.query_params.get('mine', 'false') == 'true'

        if is_enrolled_filter:
            return qs.filter(enrollments__student=user)
        
        if is_mine_filter:
            return qs.filter(instructor=user)

        if is_admin(user) or user.role == 'INSTRUCTOR':
            return qs
            
        return qs.filter(is_approved=True)

    def perform_create(self, serializer):
        user = self.request.user
        if is_admin(user) and serializer.validated_data.get('instructor'):
            serializer.save()
        else:
            serializer.save(instructor=user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if not is_admin(request.user):
            return Response({'detail': 'Only admins can approve.'}, status=403)
        course = self.get_object()
        course.is_approved = True
        course.save()
        return Response({'detail': f'Course {course.title} approved.'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if not is_admin(request.user):
            return Response({'detail': 'Only admins can reject.'}, status=403)
        course = self.get_object()
        course.is_approved = False
        course.is_submitted = False  # Return to instructor for revision
        course.save()
        return Response({'detail': f'Course {course.title} rejected and returned for revision.'})

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

        # High-fidelity financial sync
        wallet, _ = getattr(user, 'wallet_record', (None, None))
        if not wallet:
            from finance.models import Wallet
            wallet, _ = Wallet.objects.get_or_create(user=user)

        return Response({
            'total_courses': courses.count(),
            'total_enrollments': total_enrollments,
            'total_views': total_views,
            'approved_count': courses.filter(is_approved=True).count(),
            'wallet_balance': float(wallet.balance),
            'total_earned': float(wallet.total_earned)
        })

    @action(detail=False, methods=['get'])
    def instructor_analytics(self, request):
        """Tier-1 Time-series Analytics for individual faculty nodes."""
        from django.utils import timezone
        from datetime import timedelta
        import calendar
        from finance.models import Payment
        
        user = request.user
        courses = Course.objects.filter(instructor=user)
        now = timezone.now()
        
        monthly_data = []
        for i in range(5, -1, -1):
            month_start = (now - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0)
            last_day = calendar.monthrange(month_start.year, month_start.month)[1]
            month_end = month_start.replace(day=last_day, hour=23, minute=59, second=59)

            enrollments = Enrollment.objects.filter(
                course__in=courses, created_at__gte=month_start, created_at__lte=month_end
            ).count()
            
            revenue = Payment.objects.filter(
                enrollment__course__in=courses,
                is_successful=True,
                created_at__gte=month_start,
                created_at__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            
            monthly_data.append({
                'month': month_start.strftime('%b'),
                'enrollments': enrollments,
                'revenue': float(revenue)
            })
            
        return Response({'monthly_data': monthly_data})

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def platform_stats(self, request):
        from users.models import User
        
        # Real counts
        actual_students = User.objects.filter(role='STUDENT').count()
        actual_instructors = User.objects.filter(role='INSTRUCTOR', instructor_profile__is_approved_instructor=True).count()
        actual_courses = Course.objects.filter(is_approved=True).count()
        
        # Structure as requested with base offsets
        return Response({
            'students_count': 45000 + actual_students,
            'instructors_count': 2000 + actual_instructors,
            'countries_count': 115,
            'courses_count': 12000 + actual_courses,
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def popular(self, request):
        courses = Course.objects.filter(is_approved=True).order_by('-views_count')[:12]
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)

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
    serializer_class = LiveStreamSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = LiveStream.objects.all().select_related('instructor').prefetch_related('live_sessions')

        if not user.is_authenticated:
            return qs

        is_enrolled_filter = self.request.query_params.get('enrolled', 'false') == 'true'
        is_mine_filter = self.request.query_params.get('mine', 'false') == 'true'

        if is_enrolled_filter:
            return qs.filter(enrollments__student=user)
        
        if is_mine_filter:
            return qs.filter(instructor=user)

        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if is_admin(user) and serializer.validated_data.get('instructor'):
            serializer.save()
        else:
            serializer.save(instructor=user)

    @action(detail=True, methods=['post'])
    def enroll(self, request, pk=None):
        live_stream = self.get_object()
        user = request.user
        
        if LiveStreamEnrollment.objects.filter(live_stream=live_stream).count() >= live_stream.max_students:
            return Response({'detail': 'Live stream is full.'}, status=status.HTTP_400_BAD_REQUEST)
        
        enrollment, created = LiveStreamEnrollment.objects.get_or_create(student=user, live_stream=live_stream)
        if not created:
            return Response({'detail': 'Already enrolled.'}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({'detail': 'Enrolled successfully.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOnly])
    def duplicate(self, request, pk=None):
        live_stream = self.get_object()
        new_instructor_id = request.data.get('instructor_id')
        import copy
        new_stream = copy.copy(live_stream)
        new_stream.id = None
        new_stream.pk = None
        new_stream.title = f"{live_stream.title} (Clone)"
        if new_instructor_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                new_stream.instructor = User.objects.get(id=new_instructor_id)
            except User.DoesNotExist:
                return Response({'detail': 'Invalid instructor ID.'}, status=400)
        new_stream.save()
        return Response(LiveStreamSerializer(new_stream).data)

    @action(detail=True, methods=['post'])
    def rate_instructor(self, request, pk=None):
        live_stream = self.get_object()
        user = request.user
        rating = request.data.get('rating')
        comment = request.data.get('comment', '')
        
        if not rating:
            return Response({'detail': 'Rating is required.'}, status=400)
            
        if not LiveStreamEnrollment.objects.filter(student=user, live_stream=live_stream).exists():
            return Response({'detail': 'You must be enrolled to rate the instructor.'}, status=403)
            
        review, created = InstructorReview.objects.update_or_create(
            instructor=live_stream.instructor,
            student=user,
            live_stream=live_stream,
            defaults={'rating': int(rating), 'comment': comment}
        )
        return Response({'detail': 'Rating submitted.'})

class LiveSessionViewSet(viewsets.ModelViewSet):
    queryset = LiveSession.objects.all()
    serializer_class = LiveSessionSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]
