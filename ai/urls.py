from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PlatformChatView, AssistantCourseDescriptionView, 
    SummarizeContentView, LearningAssistantView,
    CourseRecommendationView, KnowledgeDocumentViewSet
)

router = DefaultRouter()
router.register('documents', KnowledgeDocumentViewSet, basename='knowledge-documents')

urlpatterns = [
    path('chat/', PlatformChatView.as_view(), name='platform-chat'),
    path('generate-description/', AssistantCourseDescriptionView.as_view(), name='generate-description'),
    path('summarize-content/', SummarizeContentView.as_view(), name='summarize-content'),
    path('learning-assistant/', LearningAssistantView.as_view(), name='learning-assistant'),
    path('recommendations/', CourseRecommendationView.as_view(), name='course-recommendations'),
    path('', include(router.urls)),
]
