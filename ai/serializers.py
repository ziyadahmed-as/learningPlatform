from rest_framework import serializers
from .models import KnowledgeDocument


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(
        source='uploaded_by.username', read_only=True
    )
    filename = serializers.CharField(read_only=True)
    file_extension = serializers.CharField(read_only=True)

    class Meta:
        model = KnowledgeDocument
        fields = [
            'id', 'title', 'file', 'description', 'is_active',
            'uploaded_by', 'uploaded_by_username',
            'filename', 'file_extension',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'uploaded_by', 'created_at', 'updated_at']
