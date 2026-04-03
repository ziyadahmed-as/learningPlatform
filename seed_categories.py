import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Learning.settings')
django.setup()

from courses.models import Category

def seed():
    # Category 1: Programing
    c1 = Category.objects.filter(slug='programing').first()
    if c1:
        c1.description = "Master the art of software engineering from Python to TypeScript. Build architectural integrity and industrial-grade protocols."
        c1.save()
        print("Updated Programing")

    # Category 2: AI
    c2 = Category.objects.filter(slug='ai-and-softskills').first()
    if c2:
        c2.description = "Deep dive into machine learning, neural networks and large language models. Architect the future with artificial intelligence."
        c2.save()
        print("Updated AI")
    else:
        # Check by name
        c2 = Category.objects.filter(name__icontains='AI').first()
        if c2:
            c2.description = "Deep dive into machine learning, neural networks and large language models. Architect the future with artificial intelligence."
            c2.save()
            print("Updated AI (by name)")

    # Category 3: Mathematics
    c3 = Category.objects.filter(slug='mathematics').first()
    if not c3:
        c3 = Category.objects.filter(name__icontains='Math').first()
        
    if c3:
        c3.description = "Advanced calculus, algebra and discrete mathematics for scientists. The foundational logic that powers modern innovation."
        c3.save()
        print("Updated Mathematics")

if __name__ == "__main__":
    seed()
