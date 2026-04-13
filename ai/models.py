from django.db import models
from django.conf import settings


class KnowledgeDocument(models.Model):
    """
    Documents uploaded by admins that are indexed into the platform
    chatbot's RAG knowledge base.  Supported formats: PDF, TXT, MD.
    """
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='knowledge_documents/')
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(
        default=True,
        help_text='Only active documents are included in the AI knowledge base.'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.file.name})"

    @property
    def filename(self):
        import os
        return os.path.basename(self.file.name) if self.file else ''

    @property
    def file_extension(self):
        return self.filename.rsplit('.', 1)[-1].lower() if '.' in self.filename else ''
