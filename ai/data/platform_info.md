# Platform Information

## Overview
This platform is a comprehensive learning management system focused on Full-Stack Development, specifically using Django for the backend and React for the frontend. 

## Key Features
- **Structured Learning**: Courses are organized into Chapters, Lessons, and Content Blocks.
- **Hands-on Projects**: Students build real-world applications with APIs, authentication, payments (Stripe), and deployment.
- **Rich Content**: Lessons support text/HTML via Tiptap editor, images, and PDF handouts.
- **Progress Tracking**: Students can track their progress through courses sequentially.
- **Role-Based Access**: Specialized dashboards for Students, Instructors, and Administrators.

## For Students
- Explore a wide range of web development courses.
- Interactive lesson viewer with support for multiple content types.
- Track course completion and enroll in new paths.

## For Instructors
- Create and manage complex course structures.
- Use an AI-powered assistant to generate compelling course descriptions.
- Manage content blocks within lessons easily.
- Toggle course visibility and track approval status.

## For Administrators
- Oversee user management and platform-wide statistics.
- Approve or reject course submissions.
- Manage categories and monitor system health.

## Technology Stack
- **Backend**: Django 5.x, Django REST Framework, Simple JWT for authentication.
- **Frontend**: React 18+, Vite, Vanilla CSS for styling.
- **Database**: PostgreSQL (or SQLite for development).
- **Asynchronous Tasks**: Celery with Redis for background processing.
- **Payments**: Stripe integration for course enrollments.

## AI Features
- **Platform Assistant**: A RAG-powered chatbot on the home page that can answer any questions about our platform's features, pricing, and curriculum.
- **Course Description Helper**: Instructors can use high-end LLMs to generate professional course descriptions from just a title and optional keywords.
- **Smart Content Support**: Deep integration with modern AI tools to ensure instructors can create the best learning experience possible.
