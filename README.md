# LearnPlatform — Backend API

A production-ready Django REST Framework backend powering the LearnPlatform learning management system. Features JWT authentication, role-based access control (RBAC), course management, student enrollment, Stripe payment integration, and asynchronous task processing with Celery.

---

## Tech Stack

| Technology | Purpose |
|---|---|
| **Django 5.x** | Web framework |
| **Django REST Framework** | RESTful API development |
| **PostgreSQL 15** | Relational database |
| **Redis 7** | Celery message broker & cache |
| **Celery** | Asynchronous task processing |
| **Stripe** | Payment gateway |
| **SimpleJWT** | JWT authentication |
| **drf-spectacular** | OpenAPI / Swagger docs |
| **Gunicorn** | Production WSGI server |
| **Docker** | Containerization |

---

## Project Structure

```
Learning/
├── Learning/               # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   └── wsgi.py
├── users/                  # User management app
│   ├── models.py           # User model (STUDENT, INSTRUCTOR, ADMIN)
│   ├── views.py            # Registration, Profile, Admin CRUD
│   ├── serializers.py      # User serializers
│   ├── urls.py             # Auth & admin endpoints
│   └── tests.py            # Admin management tests
├── courses/                # Course management app
│   ├── models.py           # Category, Course, Module, Lesson, Enrollment, Payment
│   ├── views.py            # ViewSets, Enrollment, Stripe checkout & webhook
│   ├── serializers.py      # Course, Enrollment, Payment serializers
│   ├── urls.py             # Course API routes
│   ├── tasks.py            # Celery async tasks
│   └── tests.py            # Enrollment & course tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── manage.py
```

---

## API Endpoints

### Authentication (`/api/users/`)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/users/register/` | Create a new user account |
| POST | `/api/users/login/` | Obtain JWT token pair |
| POST | `/api/users/login/refresh/` | Refresh access token |
| GET | `/api/users/me/` | Get current user profile |
| PATCH | `/api/users/me/` | Update current user profile |

### Admin User Management (`/api/users/manage/`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/users/manage/` | List all users (Admin only) |
| GET | `/api/users/manage/{id}/` | Get user detail |
| PATCH | `/api/users/manage/{id}/` | Update user role |
| DELETE | `/api/users/manage/{id}/` | Delete user |

### Courses (`/api/courses/`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/courses/categories/` | List categories |
| GET | `/api/courses/courses/` | List all courses |
| POST | `/api/courses/courses/` | Create course (Instructor/Admin) |
| GET | `/api/courses/courses/{id}/` | Course detail with modules & lessons |
| PATCH | `/api/courses/courses/{id}/` | Update course |
| DELETE | `/api/courses/courses/{id}/` | Delete course |
| POST | `/api/courses/courses/{id}/enroll/` | Enroll in a course |

### Enrollment & Payments (`/api/courses/enrollments/`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/courses/enrollments/` | List my enrollments |
| POST | `/api/courses/enrollments/{id}/create_checkout_session/` | Create Stripe checkout |
| POST | `/api/courses/webhook/stripe/` | Stripe webhook handler |

---

## User Roles & Permissions

| Role | Permissions |
|---|---|
| **STUDENT** | Browse courses, enroll, view enrollments, manage own profile |
| **INSTRUCTOR** | All student permissions + create/edit/delete own courses |
| **ADMIN** | Full access: manage all users, courses, and platform content |

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

### 1. Clone & Install

```bash
cd Learning
python -m venv ../env
../env/Scripts/activate      # Windows
# source ../env/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file or set these in your environment:

```env
POSTGRES_DB=learning_db
POSTGRES_USER=learning_user
POSTGRES_PASSWORD=learning_pass
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
STRIPE_PUBLIC_KEY=pk_test_your_key
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
```

### 3. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```

API is now available at `http://localhost:8000/api/`

### 5. Run Celery Worker (optional)

```bash
celery -A Learning worker -l info
```

---

## Docker Setup

### Build & Run with Docker Compose

```bash
docker-compose up --build
```

This starts all services:

| Service | Port | Description |
|---|---|---|
| `web` | 8000 | Django API server |
| `db` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis broker |
| `celery` | — | Background worker |

### Run Migrations in Docker

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

---

## Running Tests

```bash
python manage.py test
```

Tests cover:
- ✅ Admin user management (RBAC enforcement)
- ✅ Student cannot access admin endpoints
- ✅ Admin can create courses
- ✅ Student enrollment in free courses (`is_paid=True`)
- ✅ Student enrollment in paid courses (`is_paid=False`)
- ✅ Duplicate enrollment prevention

---

## Stripe Integration

1. Create a [Stripe account](https://dashboard.stripe.com)
2. Get your test API keys from the Stripe Dashboard
3. Set `STRIPE_SECRET_KEY` and `STRIPE_WEBHOOK_SECRET` in settings
4. For local webhook testing, use [Stripe CLI](https://stripe.com/docs/stripe-cli):

```bash
stripe listen --forward-to localhost:8000/api/courses/webhook/stripe/
```

---

## License

This project is for educational purposes as part of the LearnPlatform full-stack development course.
