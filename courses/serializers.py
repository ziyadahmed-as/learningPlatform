from rest_framework import serializers
from .models import Category, Course, Module, Lesson, Enrollment, Payment

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'content', 'video_url', 'order']

class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'lessons']

class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    instructor_name = serializers.ReadOnlyField(source='instructor.username')

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'description', 'price', 
            'instructor', 'instructor_name', 'category', 
            'created_at', 'updated_at', 'is_published', 'modules'
        ]
        read_only_fields = ['instructor']  # Set automatically in the view

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'enrollment', 'amount', 'is_successful', 'created_at']
        read_only_fields = ['is_successful', 'checkout_session_id', 'enrollment']

class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.ReadOnlyField(source='course.title')
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'course_title', 'enrolled_at', 'is_paid', 'payment']
        read_only_fields = ['is_paid', 'student']
