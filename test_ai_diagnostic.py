import os
import sys
import django
from dotenv import load_dotenv

# Set up Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Learning.settings')
django.setup()

load_dotenv()

from ai.services import AIService

def test_ai():
    print("Testing Platform Chat...")
    try:
        res = AIService.get_platform_chat_response("What is this platform about?")
        print(f"Success: {res}")
    except Exception as e:
        import traceback
        print(f"Error in Platform Chat: {e}")
        traceback.print_exc()

    print("\nTesting Learning Assistant...")
    try:
        res = AIService.get_learning_assistant_response("How do I learn Django?")
        print(f"Success: {res}")
    except Exception as e:
        import traceback
        print(f"Error in Learning Assistant: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_ai()
