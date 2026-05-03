from django.contrib import admin
from .models import Enrollment, LessonProgress, CourseView, Review, LiveStreamEnrollment, InstructorReview

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'is_paid', 'created_at')
    list_filter = ('is_paid', 'created_at')

@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'lesson', 'is_completed', 'completed_at')
    list_filter = ('is_completed', 'completed_at')

@admin.register(CourseView)
class CourseViewAdmin(admin.ModelAdmin):
    list_display = ('course', 'user', 'ip_address', 'created_at')
    list_filter = ('created_at',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('course', 'student', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

@admin.register(LiveStreamEnrollment)
class LiveStreamEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'live_stream', 'is_paid', 'created_at')
    list_filter = ('is_paid', 'created_at')

@admin.register(InstructorReview)
class InstructorReviewAdmin(admin.ModelAdmin):
    list_display = ('instructor', 'student', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
