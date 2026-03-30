from rest_framework import serializers
from .models import Enrollment, LessonProgress, CourseView, Review, LiveStreamEnrollment
from courses.models import Lesson

class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['id', 'student', 'lesson', 'watched_seconds', 'is_completed', 'completed_at']
        read_only_fields = ('student', 'completed_at')

class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.ReadOnlyField(source='course.title')
    course_thumbnail = serializers.ImageField(source='course.thumbnail', read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'course_title', 'course_thumbnail', 'created_at', 'is_paid', 'progress']
        read_only_fields = ['is_paid', 'student']

    def get_progress(self, obj):
        total_lessons = Lesson.objects.filter(chapter__course=obj.course).count()
        if total_lessons == 0:
            return 0
        completed_lessons = LessonProgress.objects.filter(
            student=obj.student, 
            lesson__chapter__course=obj.course, 
            is_completed=True
        ).count()
        return int((completed_lessons / total_lessons) * 100)

class CourseViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseView
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.username')
    
    class Meta:
        model = Review
        fields = ['id', 'course', 'student', 'student_name', 'rating', 'comment', 'created_at']
        read_only_fields = ('student',)

class LiveStreamEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveStreamEnrollment
        fields = '__all__'
        read_only_fields = ('student', 'is_paid')
