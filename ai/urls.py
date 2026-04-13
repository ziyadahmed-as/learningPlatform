from django.urls import path
from .views import (
    PlatformChatView, AssistantCourseDescriptionView, 
    SummarizeContentView, LearningAssistantView
)

urlpatterns = [
    path('chat/', PlatformChatView.as_view(), name='platform-chat'),
    path('generate-description/', AssistantCourseDescriptionView.as_view(), name='generate-description'),
    path('summarize-content/', SummarizeContentView.as_view(), name='summarize-content'),
    path('learning-assistant/', LearningAssistantView.as_view(), name='learning-assistant'),
]
