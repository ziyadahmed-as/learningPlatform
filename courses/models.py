from django.db import models
from django.conf import settings
from core.models import BaseModel

class Category(BaseModel):
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

class Course(BaseModel):
    """
    Primary Knowledge Node in the institutional registry.
    """
    class CourseType(models.TextChoices):
        VIDEO_BASED = 'VIDEO_BASED', 'Video-Based Course'
        LIVE_STREAM = 'LIVE_STREAM', 'Live Stream Course'

    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    course_type = models.CharField(max_length=30, choices=CourseType.choices, default=CourseType.VIDEO_BASED, db_index=True)
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
    has_certificate = models.BooleanField(default=False)

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

from gdstorage.storage import GoogleDriveStorage

# Initialize Google Drive Storage
gd_storage = GoogleDriveStorage()

class Lesson(BaseModel):
    """
    Individual knowledge artifact within a module hub.
    Adapts based on parent course behavior (Live vs Recorded).
    """
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Video fields
    video_file = models.FileField(upload_to='lessons/videos/', storage=gd_storage, blank=True, null=True)
    video_url = models.URLField(max_length=500, blank=True, null=True, help_text="Fallback or external video link (e.g. YouTube/Vimeo)")
    
    # Video duration
    duration = models.PositiveIntegerField(default=0)  # in seconds
    is_preview = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.chapter.title} - {self.title}'

class LiveSession(BaseModel):
    """
    Daily/scheduled session for Live Stream Courses.
    """
    live_stream = models.ForeignKey('LiveStream', on_delete=models.CASCADE, related_name='live_sessions')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    scheduled_at = models.DateTimeField()
    meeting_link = models.URLField(max_length=500, blank=True, null=True)

    class Meta:
        ordering = ['scheduled_at']

    def __str__(self):
        return f"{self.title} - {self.live_stream.title}"

class ContentBlock(models.Model):
    """
    Specific data artifact in high-fidelity lesson nodes or live sessions.
    """
    class BlockType(models.TextChoices):
        TEXT = 'text', 'Text (Word/Tiptap)'
        IMAGE = 'image', 'Identity Image'
        PDF = 'pdf', 'Artifact PDF'
        VIDEO_UPLOAD = 'video_upload', 'Institutional Video'
        VIDEO_LINK = 'video_link', 'External Signal View'
        LINK = 'link', 'Research Link'

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='content_blocks', null=True, blank=True)
    live_session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name='content_blocks', null=True, blank=True)
    title = models.CharField(max_length=200, blank=True)
    type = models.CharField(max_length=15, choices=BlockType.choices, default=BlockType.TEXT)
    text_content = models.TextField(blank=True)
    file = models.FileField(upload_to='content_blocks/files/', blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        owner = self.lesson.title if self.lesson else (self.live_session.title if self.live_session else "Unassigned")
        return f'[{self.type.upper()}] Artifact {self.order} - {owner}'

class LiveStream(BaseModel):
    """
    Live Streaming Sessions for Courses.
    """
    class GroupType(models.TextChoices):
        VVIP = 'VVIP', 'VVIP (1 Student)'
        VIP1 = 'VIP1', 'VIP1 (5 Students)'
        VIP2 = 'VIP2', 'VIP2 (10 Students)'
        NORMAL = 'NORMAL', 'Normal (100 Students)'
    
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
            self.GroupType.VIP2: 10,
            self.GroupType.NORMAL: 100
        }
        return capacity_map.get(self.group_type, 5)

    class Meta:
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.title} ({self.group_type}) - {self.instructor.username}"
