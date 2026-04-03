import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Learning.settings')
django.setup()

from courses.models import Category
from courses.serializers import CategorySerializer

def verify():
    # Fetch first 3 categories
    cats = Category.objects.all()[:3]
    print(f"Total categories: {cats.count()}")
    
    for cat in cats:
        # Check node count
        node_count = cat.nodes.count()
        print(f" - {cat.name} (nodes: {node_count}, description: {cat.description if cat.description else '[EMPTY]'})")
        
    # Test serializer
    if cats.exists():
        serializer = CategorySerializer(cats[0])
        print("\nSerialized example:")
        for k, v in serializer.data.items():
            print(f"  {k}: {v}")

if __name__ == "__main__":
    verify()
