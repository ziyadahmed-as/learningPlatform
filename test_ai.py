import os
import sys
import django

# Set up Django environment
sys.path.append('c:/Users/Django/Desktop/project/firstOffer/Learning')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Learning.settings')
django.setup()

from ai.services import AIService

def test_ai():
    print("Testing AIService.generate_course_description...")
    try:
        desc = AIService.generate_course_description("Python for Beginners", "Students", "python, coding")
        print(f"Generated Description: {desc[:100]}...")
    except Exception as e:
        print(f"Error generating description: {e}")

    print("\nTesting AIService.get_platform_chat_response...")
    try:
        response = AIService.get_platform_chat_response("What are the key features of this platform?")
        print(f"Platform Response: {response}")
    except Exception as e:
        print(f"Error getting platform response: {e}")

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        print("OPENAI_API_KEY not found in environment!")
    else:
        test_ai()
