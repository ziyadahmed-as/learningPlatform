from django.db import models
from django.conf import settings
from core.models import BaseModel

class Category(BaseModel):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

class Course(BaseModel):
    """
    Primary Knowledge Node in the institutional registry.
    """
    class CourseType(models.TextChoices):
        LIVE_TUTORIAL = 'LIVE_TUTORIAL', 'Live Tutorial Hub'
        HARD_SKILL_RECORDED = 'HARD_SKILL_RECORDED', 'Hard Skill (Pre-recorded Adaptive)'
        SOFT_SKILL = 'SOFT_SKILL', 'Soft Skill Mastery'

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    course_type = models.CharField(max_length=30, choices=CourseType.choices, default=CourseType.HARD_SKILL_RECORDED, db_index=True)
    description = models.TextField()
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='curated_content')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='nodes')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, db_index=True)
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', blank=True, null=True)
    promo_video = models.FileField(upload_to='courses/promo_videos/', blank=True, null=True)
    is_published = models.BooleanField(default=False, db_index=True)
    is_approved = models.BooleanField(default=False, db_index=True)
    is_submitted = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title', 'is_approved']),
            models.Index(fields=['instructor', 'is_published']),
        ]

    def __str__(self):
        return self.title

class Chapter(BaseModel):
    """
    Module Hub within a knowledge node.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.course.title} - {self.title}'

class Lesson(BaseModel):
    """
    Individual knowledge artifact within a module hub.
    Adapts based on parent course behavior (Live vs Recorded).
    """
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Behavioral artifacts
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    live_at = models.DateTimeField(blank=True, null=True, db_index=True)
    
    duration = models.PositiveIntegerField(default=0)  # in seconds
    is_preview = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.chapter.title} - {self.title}'

class ContentBlock(models.Model):
    """
    Specific data artifact in high-fidelity lesson nodes.
    No need for BaseModel here to keep memory footprint low; 
    parent lesson tracks time.
    """
    class BlockType(models.TextChoices):
        TEXT = 'text', 'Text (Word/Tiptap)'
        IMAGE = 'image', 'Identity Image'
        PDF = 'pdf', 'Artifact PDF'
        VIDEO_UPLOAD = 'video_upload', 'Institutional Video'
        VIDEO_LINK = 'video_link', 'External Signal View'
        LINK = 'link', 'Research Link'

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='content_blocks')
    title = models.CharField(max_length=200, blank=True)
    type = models.CharField(max_length=15, choices=BlockType.choices, default=BlockType.TEXT)
    text_content = models.TextField(blank=True)
    file = models.FileField(upload_to='content_blocks/files/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'[{self.type.upper()}] Artifact {self.order} - {self.lesson.title}'

class LiveStream(BaseModel):
    """
    Live Streaming Sessions for Courses.
    """
    class GroupType(models.TextChoices):
        VVIP = 'VVIP', 'VVIP (1 Student)'
        VIP1 = 'VIP1', 'VIP1 (5 Students)'
        VIP2 = 'VIP2', 'VIP2 (10 Students)'
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_streams', null=True, blank=True)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assigned_streams')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    group_type = models.CharField(max_length=10, choices=GroupType.choices, default=GroupType.VIP1)
    scheduled_at = models.DateTimeField()
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    is_active = models.BooleanField(default=True)

    @property
    def max_students(self):
        capacity_map = {
            self.GroupType.VVIP: 1, 
            self.GroupType.VIP1: 5, 
            self.GroupType.VIP2: 10
        }
        return capacity_map.get(self.group_type, 5)

    class Meta:
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.title} ({self.group_type}) - {self.instructor.username}"
