from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_course_creation_email(course_title, instructor_email):
    """
    Simulates sending an email to the instructor after a successful course creation
    """
    subject = f'Your new course: {course_title} was created successfully'
    message = f'Hi, your new course "{course_title}" is now available in Draft mode. Don\'t forget to publish it when you are ready.'
    
    # In a real app this would use send_mail
    print(f'Simulated Email to {instructor_email}: {subject} - {message}')
    return "Email sent successfully"
