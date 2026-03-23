# 🐍 LearnPlatform Backend (Django API)

This is the core API for the LearnPlatform educational system, built with **Django REST Framework** and **PostgreSQL**.

## 🚀 Key Features
*   **Course Management:** CRUD for courses, chapters, lessons, and multi-media content blocks.
*   **Role-Based Security:** Custom permissions for `STUDENT`, `INSTRUCTOR`, and `ADMIN`.
*   **Admin Approval Workflow:** Actions for admins to approve/reject course submissions.
*   **Progress Tracking:** Sequential lesson tracking and student progress metrics.
*   **Stripe Integration:** Payment processing for course enrollments.
*   **Media Handling:** Support for image, PDF, and video file storage.

---

## ⚙️ Backend Setup

### 1. Requirements
*   Python 3.10+
*   PostgreSQL 14+
*   Redis (for Celery)

### 2. Environment Configuration
Create a `.env` file in the current folder:
```bash
DEBUG=True
SECRET_KEY='your-secret-key'
DATABASE_URL=postgres://postgres:zed@localhost:5432/fatraa
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
FRONTEND_URL=http://localhost:5173
```

### 3. Installation & Run
```bash
# Activate your virtual environment
# env/Scripts/activate (Windows)

python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

---

## 🛠️ API Documentation
The API documentation is powered by **drf-spectacular**. 
*   Visit `/api/schema/swagger-ui/` for interactive documentation once the server is running.

## 📁 App Structure
*   `Learning/`: Core settings and environment loading.
*   `courses/`: Models and views for the educational content.
*   `users/`: Authentication models and role management.
*   `utils/`: Shared helper functions and permissions.
