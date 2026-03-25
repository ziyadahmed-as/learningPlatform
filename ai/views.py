from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.conf import settings
import os
from .services import AIService

class PlatformChatView(APIView):
    """
    Publicly accessible endpoint for general information about the platform.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        if not os.getenv('OPENAI_API_KEY'):
            return Response(
                {"error": "AI services are currently unavailable. Missing API Key."}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
            
        query = request.data.get('query')
        if not query:
            return Response({"error": "Query is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            response = AIService.get_platform_chat_response(query)
            return Response({"response": response}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssistantCourseDescriptionView(APIView):
    """
    Endpoint for instructors to generate course descriptions using AI.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Basic check for Instructor role
        if request.user.role != 'INSTRUCTOR' and request.user.role != 'ADMIN':
            return Response({"error": "Only instructors can generate course descriptions"}, status=status.HTTP_403_FORBIDDEN)

        if not os.getenv('OPENAI_API_KEY'):
            return Response(
                {"error": "AI services are currently unavailable. Missing API Key."}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        title = request.data.get('title')
        audience = request.data.get('audience', '')
        keywords = request.data.get('keywords', '')

        if not title:
            return Response({"error": "Course title is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            description = AIService.generate_course_description(title, audience, keywords)
            return Response({"description": description}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
