from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, CourseViewSet, LessonViewSet, 
    EnrollmentViewSet, LessonImageViewSet, LessonFileViewSet, stripe_webhook
)
router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'courses', CourseViewSet, basename='course')

router.register(r'lessons', LessonViewSet)
router.register(r'lesson-images', LessonImageViewSet)
router.register(r'lesson-files', LessonFileViewSet)
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')

urlpatterns = [
    path('webhook/stripe/', stripe_webhook, name='stripe-webhook'),
    path('', include(router.urls)),
]
