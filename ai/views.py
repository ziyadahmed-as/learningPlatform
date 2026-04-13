from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.conf import settings
import os
from .services import AIService
from courses.serializers import CourseSerializer


class PlatformChatView(APIView):
    """
    Publicly accessible endpoint for general information about the platform.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        query = request.data.get('query')
        if not query:
            return Response({"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            response = AIService.get_platform_chat_response(query)
            return Response({"response": response}, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e), "traceback": traceback.format_exc()}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssistantCourseDescriptionView(APIView):
    """
    Endpoint for instructors to generate course descriptions using AI.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role not in ['INSTRUCTOR', 'ADMIN'] and not request.user.is_superuser:
            return Response({"error": "Only instructors can generate course descriptions"}, status=status.HTTP_403_FORBIDDEN)

        title = request.data.get('title')
        audience = request.data.get('audience', '')
        keywords = request.data.get('keywords', '')

        if not title:
            return Response({"error": "Title required"}, status=400)

        try:
            description = AIService.generate_course_description(title, audience, keywords)
            return Response({"description": description})
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class SummarizeContentView(APIView):
    """
    AI-powered content summarization for learners and administrators.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        content = request.data.get('content')
        if not content:
            return Response({"error": "Content required"}, status=400)

        try:
            summary = AIService.summarize_content(content)
            return Response({"summary": summary})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class LearningAssistantView(APIView):
    """
    Dedicated AI Learning Assistant for students.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        query = request.data.get('query')
        context = request.data.get('context', '') # Manual course or lesson context
        course_id = request.data.get('course_id') # For dynamic RAG indexing

        if not query:
            return Response({"error": "Query required"}, status=400)

        try:
            response = AIService.get_learning_assistant_response(query, context, course_id)
            return Response({"response": response})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
