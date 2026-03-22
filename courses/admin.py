from django.contrib import admin
from .models import Category, Course, Lesson, Enrollment, Payment, LessonImage, LessonFile, LessonProgress

admin.site.register(Category)
admin.site.register(Course)

admin.site.register(Lesson)
admin.site.register(Enrollment)
admin.site.register(Payment)
admin.site.register(LessonImage)
admin.site.register(LessonFile)
admin.site.register(LessonProgress)
