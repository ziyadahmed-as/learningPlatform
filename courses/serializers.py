from rest_framework import serializers
from .models import Category, Course, Chapter, Lesson, ContentBlock, LiveStream, LiveSession
from interactions.models import Enrollment, LessonProgress
from interactions.serializers import ReviewSerializer

class CategorySerializer(serializers.ModelSerializer):
    node_count = serializers.IntegerField(source='nodes.count', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'node_count']

class ContentBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentBlock
        fields = ['id', 'lesson', 'live_session', 'title', 'type', 'text_content', 'file', 'url', 'order']

class LessonSerializer(serializers.ModelSerializer):
    content_blocks = ContentBlockSerializer(many=True, read_only=True)
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'chapter', 'title', 'description', 'order', 
            'content_blocks', 'is_completed', 'duration', 'is_preview',
            'video_file', 'video_url'
        ]

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

class LiveSessionSerializer(serializers.ModelSerializer):
    content_blocks = ContentBlockSerializer(many=True, read_only=True)

    class Meta:
        model = LiveSession
        fields = ['id', 'live_stream', 'title', 'description', 'scheduled_at', 'meeting_link', 'content_blocks']

class LiveStreamSerializer(serializers.ModelSerializer):
    instructor_name = serializers.ReadOnlyField(source='instructor.username')
    course_name = serializers.ReadOnlyField(source='course.title')
    live_sessions = LiveSessionSerializer(many=True, read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    enrollment_count = serializers.SerializerMethodField()

    class Meta:
        model = LiveStream
        fields = [
            'id', 'course', 'course_name', 'instructor', 'instructor_name',
            'title', 'description', 'group_type', 'max_students',
            'scheduled_at', 'meeting_link', 'price', 'is_active', 'created_at',
            'live_sessions', 'is_enrolled', 'enrollment_count'
        ]
        read_only_fields = ['max_students', 'created_at']
        extra_kwargs = {
            'instructor': {'required': False}
        }

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from interactions.models import LiveStreamEnrollment
            return LiveStreamEnrollment.objects.filter(student=request.user, live_stream=obj).exists()
        return False

    def get_enrollment_count(self, obj):
        from interactions.models import LiveStreamEnrollment
        return LiveStreamEnrollment.objects.filter(live_stream=obj).count()

class CourseSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    live_streams = LiveStreamSerializer(many=True, read_only=True)
    instructor_name = serializers.ReadOnlyField(source='instructor.username')
    category_name = serializers.ReadOnlyField(source='category.name')
    category_slug = serializers.ReadOnlyField(source='category.slug')
    is_enrolled = serializers.SerializerMethodField()
    enrollment_count = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    reviews = ReviewSerializer(source='node_reviews', many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'course_type', 'description', 'price', 
            'thumbnail', 'promo_video',
            'instructor', 'instructor_name', 'category', 'category_name', 'category_slug',
            'created_at', 'updated_at', 'is_published', 'is_approved', 'is_submitted',
            'views_count', 'has_certificate', 'chapters', 'live_streams', 'is_enrolled', 'rating',
            'enrollment_count', 'completion_percentage', 'reviews'
        ]
        read_only_fields = ['is_approved', 'views_count', 'slug']
        extra_kwargs = {
            'instructor': {'required': False}
        }

    def get_rating(self, obj):
        reviews = obj.node_reviews.all() # Corrected related name if needed, check model
        if not reviews:
            return 4.9 
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(student=request.user, course=obj).exists()
        return False

    def get_enrollment_count(self, obj):
        return obj.enrollments.count()

    def get_completion_percentage(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
            
        total_lessons = Lesson.objects.filter(chapter__course=obj).count()
        if total_lessons == 0:
            return 0
            
        completed = LessonProgress.objects.filter(
            student=request.user,
            lesson__chapter__course=obj, 
            is_completed=True
        ).count()
        
        return round((completed / total_lessons) * 100, 1)
