from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile, InstructorProfile, StudentProfile

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role',)}),
    )

@admin.register(Profile)

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio')

@admin.register(InstructorProfile)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'instructor_type', 'is_approved_instructor')
    list_filter = ('instructor_type', 'is_approved_instructor')

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'points')
