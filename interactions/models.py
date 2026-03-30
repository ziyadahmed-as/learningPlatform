from django.db import models
from django.conf import settings
from core.models import BaseModel

class Enrollment(BaseModel):
    """
    Registry Authorization between Scholar and Knowledge Node.
    """
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registry_enrollments')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='enrollments')
    is_paid = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ('student', 'course_id')
        verbose_name_plural = 'Scholar Registries'

    def __str__(self):
        return f'{self.student.username} synced to Node {self.course_id}'

class LessonProgress(BaseModel):
    """
    Temporal Mastery of individual knowledge artifacts.
    """
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_mastery')
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE, related_name='progress')
    watched_seconds = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'lesson')
        verbose_name_plural = 'Artifact Mastery Flow'

    def __str__(self):
        return f'{self.student.username} - Lesson {self.lesson_id} [Status: {"Mastered" if self.is_completed else "Clinical"}]'

class CourseView(BaseModel):
    """
    Signal Pulse tracking across knowledge nodes.
    """
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='course_views')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Signal Pulse on Node {self.course_id}'

class Review(BaseModel):
    """
    Peer-Validated Signal Feedback on knowledge artifacts.
    """
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='node_reviews')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='node_reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)], db_index=True)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('course', 'student')
        ordering = ['-created_at']

    def __str__(self):
        return f'Review for Node {self.course_id} by {self.student.username}'
