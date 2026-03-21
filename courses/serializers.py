from rest_framework import serializers
from .models import Category, Course, Module, Lesson, Enrollment, Payment, LessonImage, LessonFile, LessonProgress

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class LessonImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonImage
        fields = ['id', 'image', 'caption', 'order']

class LessonFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonFile
        fields = ['id', 'file', 'title', 'order']

class LessonSerializer(serializers.ModelSerializer):
    images = LessonImageSerializer(many=True, read_only=True)
    files = LessonFileSerializer(many=True, read_only=True)
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'content', 'video_url', 'order', 'images', 'files', 'is_completed']

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return LessonProgress.objects.filter(student=request.user, lesson=obj, is_completed=True).exists()
        return False

class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'order', 'lessons']

class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    instructor_name = serializers.ReadOnlyField(source='instructor.username')
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'description', 'price', 
            'instructor', 'instructor_name', 'category', 
            'created_at', 'updated_at', 'is_published', 'is_approved', 'modules', 'is_enrolled'
        ]
        read_only_fields = ['instructor', 'is_approved']  # is_approved is set via the approve action

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(student=request.user, course=obj).exists()
        return False

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
