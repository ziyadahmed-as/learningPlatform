import os
import json
from django.conf import settings
from django.apps import apps

class AIService:
    _vectorstore = None
    _course_vectorstores = {}       # Cache for course-specific RAG
    _recommendation_index = None    # Global catalog index for recommendations
    _recommendation_id_map = []     # Maps FAISS doc index → course id

    # ------------------------------------------------------------------
    # Recommendation helpers
    # ------------------------------------------------------------------

    @classmethod
    def initialize_recommendation_index(cls, force_refresh=False):
        """Builds cached FAISS index of all approved courses."""
        return None

    @classmethod
    def get_course_recommendations(cls, user, limit=5, force_refresh=False):
        """Semantic course recommendations based on user enrollments."""
        Course, Enrollment = apps.get_model('courses', 'Course'), apps.get_model('interactions', 'Enrollment')
        enrolled_ids = list(Enrollment.objects.filter(student=user).values_list('course_id', flat=True))
        base_qs = Course.objects.filter(is_approved=True).exclude(id__in=enrolled_ids)
        return list(base_qs.order_by('-created_at')[:limit])

    @classmethod
    def initialize_rag(cls):
        """Initializes the vector store with all platform documents."""
        return None

    @classmethod
    def initialize_course_rag(cls, course_id):
        """Initializes a specific vector store for a course."""
        return None

    @classmethod
    def get_platform_chat_response(cls, query):
        """Answers questions about the platform using RAG."""
        return "AI Services are currently being migrated to a dedicated microservice."

    @classmethod
    def generate_course_description(cls, title, audience=None, keywords=None):
        """Generates a course description for instructors."""
        return "AI generated description is temporarily unavailable."

    @classmethod
    def summarize_content(cls, content):
        """Summarizes educational content for learners."""
        return "AI summary is temporarily unavailable."

    @classmethod
    def get_learning_assistant_response(cls, query, context="", course_id=None):
        """Contextual learning assistant for students enrolled in courses."""
        return "The AI Learning Assistant is currently being migrated to a dedicated microservice. Please try again later."

    @classmethod
    def generate_course_curriculum(cls, title):
        """Generates a suggested chapter and lesson structure for a course."""
        return []
