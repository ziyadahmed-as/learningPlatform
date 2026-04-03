import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Learning.settings')
django.setup()

def check_sync():
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = set(row[0] for row in cursor.fetchall())
    
    print("Database Tables Found:")
    for t in sorted(tables):
        print(f" - {t}")
        
    expected_models = ['Category', 'Course', 'Chapter', 'Lesson', 'ContentBlock', 'LiveStream', 'LiveSession']
    print("\nModel Table Check:")
    from django.apps import apps
    courses_app = apps.get_app_config('courses')
    for model_name in expected_models:
        try:
            model = courses_app.get_model(model_name)
            table_name = model._meta.db_table
            exists = table_name in tables
            print(f" - {model_name} (table: {table_name}): {'EXISTS' if exists else 'MISSING'}")
        except Exception as e:
            print(f" - {model_name}: Error retrieving model - {str(e)}")

if __name__ == "__main__":
    check_sync()
