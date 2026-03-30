from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EnrollmentViewSet, LessonProgressViewSet, CourseViewViewSet, 
    ReviewViewSet, LiveStreamEnrollmentViewSet
)

router = DefaultRouter()
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'lesson-progress', LessonProgressViewSet)
router.register(r'course-views', CourseViewViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'livestream-enrollments', LiveStreamEnrollmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
