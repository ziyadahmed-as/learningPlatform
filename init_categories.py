import os
import django
import sys

# Add project to path
sys.path.append('C:\\Users\\Django\\Desktop\\project\\firstOffer\\Learning')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Learning.settings')
django.setup()

from courses.models import Category

INSTITUTIONAL_CATEGORIES = [
    'Live Tutorial',
    'Hard Skill (Pre-recorded)',
    'Soft Skill'
]

def initialize_categories():
    print("Synchronizing Institutional Categories...")
    for name in INSTITUTIONAL_CATEGORIES:
        slug = name.lower().replace(' ', '-').replace('(', '').replace(')', '')
        cat, created = Category.objects.get_or_create(name=name, defaults={'slug': slug})
        if created:
            print(f" [+] Created: {name}")
        else:
            print(f" [.] Exists: {name}")
    print("Registry Synchronization Complete.")

if __name__ == "__main__":
    initialize_categories()
