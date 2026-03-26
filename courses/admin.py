from django.contrib import admin
from .models import Category, Course, Chapter, Lesson, ContentBlock, Enrollment, Payment, LessonProgress

admin.site.register(Category)
admin.site.register(Course)
admin.site.register(Chapter)
admin.site.register(Lesson)
admin.site.register(ContentBlock)
admin.site.register(Enrollment)
admin.site.register(Payment)
admin.site.register(LessonProgress)
