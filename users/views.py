from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, UserSerializer, AdminUserSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


class UserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class IsAdminUserRole(permissions.BasePermission):
    """Allows access only to users with the ADMIN role."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'ADMIN' or request.user.is_superuser)
        )


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    CRUD for all users. Accessible only by ADMIN users.
    Adds approve/reject instructor application actions.
    """
    serializer_class = AdminUserSerializer
    queryset = User.objects.all().order_by('-date_joined')
    permission_classes = [IsAdminUserRole]

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUserRole])
    def approve_instructor(self, request, pk=None):
        """Promote a user to INSTRUCTOR role (approve their application)."""
        user = self.get_object()
        if user.role == 'INSTRUCTOR':
            return Response(
                {'detail': f'{user.username} is already an instructor.'},
                status=status.HTTP_200_OK
            )
        user.role = 'INSTRUCTOR'
        user.save()
        return Response(
            {'detail': f'{user.username} has been approved as an instructor.'},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUserRole])
    def reject_instructor(self, request, pk=None):
        """Demote a user back to STUDENT (reject their instructor application)."""
        user = self.get_object()
        user.role = 'STUDENT'
        # Clear expertise so they no longer appear as a pending application
        user.expertise = ''
        user.save()
        return Response(
            {'detail': f'{user.username} application has been rejected.'},
            status=status.HTTP_200_OK
        )


from rest_framework.views import APIView

class AdminStatsView(APIView):
    """
    Platform-wide analytics for the admin dashboard.
    Returns users, courses, revenue, growth charts, recent activity.
    """
    permission_classes = [IsAdminUserRole]

    def get(self, request, *args, **kwargs):
        import calendar
        from courses.models import Course, Category
        from interactions.models import Enrollment
        from finance.models import Payment
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # ── User stats ──────────────────────────────────────────────────────
        total_users = User.objects.count()
        students = User.objects.filter(role='STUDENT').count()
        instructors = User.objects.filter(role='INSTRUCTOR').count()
        new_users_this_month = User.objects.filter(date_joined__gte=thirty_days_ago).count()

        # ── Course stats ─────────────────────────────────────────────────────
        total_courses = Course.objects.count()
        approved_courses = Course.objects.filter(is_approved=True).count()
        pending_approval = Course.objects.filter(is_submitted=True, is_approved=False).count()

        # ── Enrollment stats ─────────────────────────────────────────────────
        total_enrollments = Enrollment.objects.count()
        paid_enrollments = Enrollment.objects.filter(is_paid=True).count()

        # ── Revenue ──────────────────────────────────────────────────────────
        total_revenue = Payment.objects.filter(
            is_successful=True
        ).aggregate(total=Sum('amount'))['total'] or 0

        revenue_this_month = Payment.objects.filter(
            is_successful=True, created_at__gte=thirty_days_ago
        ).aggregate(total=Sum('amount'))['total'] or 0

        # ── Pending instructor applications ──────────────────────────────────
        # Users who registered with expertise (applied as instructor) but are still STUDENT
        pending_instructors = list(
            User.objects.filter(
                role='STUDENT',
                expertise__isnull=False
            ).exclude(expertise='').order_by('-date_joined').values(
                'id', 'username', 'email', 'expertise',
                'years_of_experience', 'education_level', 'date_joined'
            )[:20]
        )
        # Stringify dates for JSON
        for u in pending_instructors:
            if u['date_joined']:
                u['date_joined'] = u['date_joined'].strftime('%b %d, %Y')

        # ── Recent users ─────────────────────────────────────────────────────
        recent_users_qs = User.objects.order_by('-date_joined').values(
            'id', 'username', 'email', 'role', 'date_joined'
        )[:10]
        recent_users = []
        for u in recent_users_qs:
            recent_users.append({
                'id': u['id'],
                'username': u['username'],
                'email': u['email'],
                'role': u['role'],
                'joined': u['date_joined'].strftime('%b %d, %Y') if u['date_joined'] else '',
            })

        # ── Monthly growth (last 6 months) ───────────────────────────────────
        monthly_data = []
        for i in range(5, -1, -1):
            # Approximate month boundaries
            month_start = (now - timedelta(days=i * 30)).replace(day=1, hour=0, minute=0, second=0)
            last_day = calendar.monthrange(month_start.year, month_start.month)[1]
            month_end = month_start.replace(day=last_day, hour=23, minute=59, second=59)

            month_users = User.objects.filter(
                date_joined__gte=month_start, date_joined__lte=month_end
            ).count()
            month_revenue = Payment.objects.filter(
                is_successful=True,
                created_at__gte=month_start,
                created_at__lte=month_end
            ).aggregate(total=Sum('amount'))['total'] or 0
            month_courses = Course.objects.filter(
                created_at__gte=month_start, created_at__lte=month_end
            ).count()

            monthly_data.append({
                'month': month_start.strftime('%b'),
                'users': month_users,
                'revenue': float(month_revenue),
                'courses': month_courses,
            })

        # ── Category distribution ─────────────────────────────────────────────
        categories = Category.objects.annotate(
            course_count=Count('courses', distinct=True),
            student_count=Count('courses__enrollments', distinct=True),
        ).values('name', 'course_count', 'student_count')

        category_data = [
            {
                'category': cat['name'],
                'courses': cat['course_count'],
                'students': cat['student_count'],
            }
            for cat in categories
        ]

        # ── Top Performing Courses ───────────────────────────────────────────
        top_courses_qs = Course.objects.filter(is_approved=True).annotate(
            enroll_count=Count('enrollments')
        ).order_by('-enroll_count')[:5]
        
        top_courses = [
            {
                'id': c.id,
                'title': c.title,
                'enrollments': c.enroll_count,
                'revenue': float(c.enrollments.filter(is_paid=True).count() * c.price),
                'rating': 4.9 # Default institutional rating
            }
            for c in top_courses_qs
        ]

        return Response({
            'users': {
                'total': total_users,
                'students': students,
                'instructors': instructors,
                'new_this_month': new_users_this_month,
            },
            'courses': {
                'total': total_courses,
                'approved': approved_courses,
                'pending_approval': pending_approval,
            },
            'enrollments': {
                'total': total_enrollments,
                'paid': paid_enrollments,
            },
            'revenue': {
                'total': float(total_revenue),
                'this_month': float(revenue_this_month),
            },
            'recent_users': recent_users,
            'pending_instructors': pending_instructors,
            'monthly_growth': monthly_data,
            'category_distribution': category_data,
            'top_courses': top_courses,
        })
 