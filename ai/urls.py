from django.urls import path
from .views import PlatformChatView, AssistantCourseDescriptionView

urlpatterns = [
    path('chat/', PlatformChatView.as_view(), name='platform-chat'),
    path('generate-description/', AssistantCourseDescriptionView.as_view(), name='generate-description'),
]
