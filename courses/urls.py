from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet, CourseViewSet, ChapterViewSet, 
    ContentBlockViewSet, LessonViewSet, LiveStreamViewSet
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'chapters', ChapterViewSet)
router.register(r'lessons', LessonViewSet)
router.register(r'content-blocks', ContentBlockViewSet)
router.register(r'live-streams', LiveStreamViewSet, basename='live-stream')

urlpatterns = [
    path('', include(router.urls)),
]
