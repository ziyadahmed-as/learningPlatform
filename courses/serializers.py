from rest_framework import serializers
from .models import (
    Category, Course, Chapter, Lesson, ContentBlock, 
    Enrollment, Payment, LessonImage, LessonFile, LessonLink,
    LessonProgress, Review, Wallet, Transaction, WithdrawalRequest
)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

class ContentBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentBlock
        fields = ['id', 'lesson', 'title', 'content', 'image', 'pdf_file', 'video_url', 'video_file', 'order']

class LessonImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonImage
        fields = ['id', 'lesson', 'image', 'caption', 'order']

class LessonFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonFile
        fields = ['id', 'lesson', 'file', 'title', 'order']

class LessonLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonLink
        fields = ['id', 'lesson', 'url', 'title', 'order']

class LessonSerializer(serializers.ModelSerializer):
    images = LessonImageSerializer(many=True, read_only=True)
    files = LessonFileSerializer(many=True, read_only=True)
    links = LessonLinkSerializer(many=True, read_only=True)
    content_blocks = ContentBlockSerializer(many=True, read_only=True)
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ['id', 'chapter', 'title', 'content', 'video_url', 'order', 'images', 'files', 'content_blocks', 'is_completed']

    def get_is_completed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return LessonProgress.objects.filter(student=request.user, lesson=obj, is_completed=True).exists()
        return False



class ChapterSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'course', 'title', 'order', 'lessons']


class CourseSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    instructor_name = serializers.ReadOnlyField(source='instructor.username')
    is_enrolled = serializers.SerializerMethodField()
    enrollment_count = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'description', 'price', 
            'thumbnail', 'promo_video',
            'instructor', 'instructor_name', 'category', 
            'created_at', 'updated_at', 'is_published', 'is_approved', 'is_submitted',
            'views_count', 'chapters', 'is_enrolled',
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
        total_lessons = Lesson.objects.filter(chapter__course=obj).count()
        if total_lessons == 0:
            return 0
        enrollment_count = obj.enrollments.count()
        if enrollment_count == 0:
            return 0
        completed = LessonProgress.objects.filter(
            lesson__chapter__course=obj, is_completed=True
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

class ReviewSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.username')

    class Meta:
        model = Review
        fields = ['id', 'course', 'student', 'student_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['student']

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'wallet', 'amount', 'course', 'transaction_type', 'created_at']

class WalletSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True)

    class Meta:
        model = Wallet
        fields = ['id', 'user', 'balance', 'total_earned', 'transactions', 'updated_at']

class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ['id', 'instructor', 'amount', 'status', 'account_details', 'created_at', 'updated_at']
        read_only_fields = ['status', 'instructor']

