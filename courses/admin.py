from django.contrib import admin
from .models import Category, Course, Chapter, Lesson, ContentBlock, LiveSession, LiveStream

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'course_type', 'price', 'is_published', 'is_approved')
    list_filter = ('course_type', 'is_published', 'is_approved', 'category')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter', 'order', 'is_preview', 'video_file', 'video_url')
    list_filter = ('chapter__course', 'chapter')

@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'order', 'lesson', 'live_session')
    list_filter = ('type',)

@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'live_stream', 'scheduled_at')
    list_filter = ('live_stream',)

@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display = ('title', 'instructor', 'group_type', 'scheduled_at', 'is_active')
    list_filter = ('group_type', 'is_active')
