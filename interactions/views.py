from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Enrollment, LessonProgress, CourseView, Review, LiveStreamEnrollment
from .serializers import (
    EnrollmentSerializer, LessonProgressSerializer, CourseViewSerializer, 
    ReviewSerializer, LiveStreamEnrollmentSerializer
)
from courses.models import Lesson, Course
from django.utils import timezone
from datetime import timedelta

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return self.queryset
        return self.queryset.filter(student=self.request.user)

    def perform_create(self, serializer):
        course = serializer.validated_data.get('course')
        # Free courses are marked as paid immediately
        is_paid = course.price == 0
        serializer.save(student=self.request.user, is_paid=is_paid)

class LessonProgressViewSet(viewsets.ModelViewSet):
    queryset = LessonProgress.objects.all()
    serializer_class = LessonProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(student=self.request.user)

    @action(detail=False, methods=['post'], url_path='mark-completed/(?P<lesson_id>[^/.]+)')
    def mark_completed(self, request, lesson_id=None):
        user = request.user
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'detail': 'Lesson not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check if student is enrolled
        course = lesson.chapter.course
        if not Enrollment.objects.filter(student=user, course=course).exists():
            return Response({'detail': 'You must be enrolled in this course.'}, status=status.HTTP_403_FORBIDDEN)

        # Sequential progression logic
        all_lessons = Lesson.objects.filter(chapter__course=course).order_by('chapter__order', 'order')
        lesson_ids = list(all_lessons.values_list('id', flat=True))
        try:
            current_index = lesson_ids.index(lesson.id)
        except ValueError:
             return Response({'detail': 'Lesson not found in course.'}, status=status.HTTP_404_NOT_FOUND)

        if current_index > 0:
            prev_lesson_id = lesson_ids[current_index - 1]
            if not LessonProgress.objects.filter(student=user, lesson_id=prev_lesson_id, is_completed=True).exists():
                return Response({'detail': 'Please complete the previous lesson first.'}, status=status.HTTP_400_BAD_REQUEST)

        progress, created = LessonProgress.objects.get_or_create(student=user, lesson=lesson)
        if not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            progress.save()
            # Add scholarly points for node completion
            user.points += 10
            user.save(update_fields=['points'])

        return Response({'detail': 'Lesson marked as completed.', 'points_earned': 10})

    @action(detail=False, methods=['post'], url_path='update-watched/(?P<lesson_id>[^/.]+)')
    def update_watched(self, request, lesson_id=None):
        user = request.user
        watched_seconds = request.data.get('watched_seconds', 0)
        try:
            lesson = Lesson.objects.get(id=lesson_id)
        except Lesson.DoesNotExist:
            return Response({'detail': 'Lesson not found.'}, status=status.HTTP_404_NOT_FOUND)

        progress, created = LessonProgress.objects.get_or_create(student=user, lesson=lesson)
        
        try:
            new_seconds = int(watched_seconds)
            if new_seconds > progress.watched_seconds:
                progress.watched_seconds = new_seconds
                progress.save()
        except (ValueError, TypeError):
            pass

        return Response({
            'detail': 'Progress updated.', 
            'watched_seconds': progress.watched_seconds,
            'is_completed': progress.is_completed
        })

class CourseViewViewSet(viewsets.ModelViewSet):
    queryset = CourseView.objects.all()
    serializer_class = CourseViewSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        course = serializer.validated_data.get('course')
        user = self.request.user if self.request.user.is_authenticated else None
        ip = self.request.META.get('REMOTE_ADDR')
        
        # Deduplication logic
        cutoff = timezone.now() - timedelta(hours=24)
        recent = CourseView.objects.filter(course=course, created_at__gte=cutoff)
        if user:
            recent = recent.filter(user=user)
        elif ip:
            recent = recent.filter(ip_address=ip, user__isnull=True)
        else:
            recent = recent.none()

        if not recent.exists():
            serializer.save(user=user, ip_address=ip)
            # Update views count cache on course model
            course.views_count += 1
            course.save(update_fields=['views_count'])
        else:
            # Still return 201 but don't save new view or increment count
            pass

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

class LiveStreamEnrollmentViewSet(viewsets.ModelViewSet):
    queryset = LiveStreamEnrollment.objects.all()
    serializer_class = LiveStreamEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return self.queryset
        return self.queryset.filter(student=self.request.user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
