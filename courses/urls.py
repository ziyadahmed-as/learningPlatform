from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, CourseViewSet, ChapterViewSet, ContentBlockViewSet, LessonViewSet, 
    EnrollmentViewSet, LessonImageViewSet, LessonFileViewSet, stripe_webhook,
    ReviewViewSet, WalletViewSet, WithdrawalRequestViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'chapters', ChapterViewSet)
router.register(r'lessons', LessonViewSet)
router.register(r'content-blocks', ContentBlockViewSet)
router.register(r'lesson-images', LessonImageViewSet)
router.register(r'lesson-files', LessonFileViewSet)
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'reviews', ReviewViewSet)
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'withdrawal-requests', WithdrawalRequestViewSet, basename='withdrawal-request')

urlpatterns = [
    path('webhook/stripe/', stripe_webhook, name='stripe-webhook'),
    path('', include(router.urls)),
]
