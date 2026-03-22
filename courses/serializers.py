from rest_framework import serializers
from .models import Category, Course, Lesson, Enrollment, Payment, LessonImage, LessonFile, LessonProgress

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



class CourseSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)
    instructor_name = serializers.ReadOnlyField(source='instructor.username')
    is_enrolled = serializers.SerializerMethodField()
    enrollment_count = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'description', 'price', 
            'instructor', 'instructor_name', 'category', 
            'created_at', 'updated_at', 'is_published', 'is_approved',
            'views_count', 'lessons', 'is_enrolled',
            'enrollment_count', 'completion_percentage',
        ]
        read_only_fields = ['instructor', 'is_approved', 'views_count']

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(student=request.user, course=obj).exists()
        return False

    def get_enrollment_count(self, obj):
        return obj.enrollments.count()

    def get_completion_percentage(self, obj):
        """Average completion % across all enrolled students."""
        total_lessons = Lesson.objects.filter(course=obj).count()
        if total_lessons == 0:
            return 0
        enrollment_count = obj.enrollments.count()
        if enrollment_count == 0:
            return 0
        completed = LessonProgress.objects.filter(
            lesson__course=obj, is_completed=True
        ).count()
        # Average: total completed lessons / (total students × total lessons) × 100
        return round((completed / (enrollment_count * total_lessons)) * 100, 1)

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

