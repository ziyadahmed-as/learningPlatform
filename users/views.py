from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, UserSerializer, AdminUserSerializer, MyTokenObtainPairSerializer

User = get_user_model()


class MyTokenObtainView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


class UserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class InstructorListView(generics.ListAPIView):
    """
    Publicly accessible list of approved faculty nodes.
    Used for the /instructors page.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserSerializer
    queryset = User.objects.filter(role='INSTRUCTOR', instructor_profile__is_approved_instructor=True).order_by('username')


class IsAdminUserRole(permissions.BasePermission):
    """Allows access only to users with the ADMIN or SUPER_ADMIN role."""
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role in ['ADMIN', 'SUPER_ADMIN'] or request.user.is_superuser)
        )


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    CRUD for all users. Accessible only by ADMIN users.
    Adds approve/reject instructor application actions.
    """
    serializer_class = AdminUserSerializer
    queryset = User.objects.all().select_related('profile', 'instructor_profile', 'student_profile').order_by('-date_joined')
    permission_classes = [IsAdminUserRole]

    def get_queryset(self):
        role_filter = self.request.query_params.get('role')
        qs = self.queryset
        if role_filter:
            qs = qs.filter(role=role_filter)
        return qs

    def perform_create(self, serializer):
        # Admin can now create other admins as requested
        serializer.save()

    def perform_update(self, serializer):
        # Admin can now modify any role
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        # Admin can delete any account
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUserRole])
    def approve_instructor(self, request, pk=None):
        """Promote a user to INSTRUCTOR role (approve their application)."""
        user = self.get_object()
        if user.role == 'INSTRUCTOR' and user.instructor_profile.is_approved_instructor:
            return Response(
                {'detail': f'{user.username} is already an approved instructor.'},
                status=status.HTTP_200_OK
            )
        user.role = 'INSTRUCTOR'
        profile = user.instructor_profile
        profile.is_approved_instructor = True
        profile.save()
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
        profile = user.instructor_profile
        profile.expertise = ''
        profile.is_approved_instructor = False
        profile.save()
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
        from django.db.models import Sum, Count, Q
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
        pending_approval_count = Course.objects.filter(is_submitted=True, is_approved=False).count()
        
        # Pending courses list for moderation
        pending_courses_qs = Course.objects.filter(is_submitted=True, is_approved=False).order_by('-updated_at')[:20]
        pending_courses = [
            {
                'id': c.id,
                'title': c.title,
                'instructor': c.instructor.username,
                'category': c.category.name if c.category else 'Uncategorized',
                'price': float(c.price),
                'submitted_at': c.updated_at.strftime('%b %d, %Y')
            }
            for c in pending_courses_qs
        ]

        # ── Enrollment stats ─────────────────────────────────────────────────
        total_enrollments = Enrollment.objects.count()
        paid_enrollments = Enrollment.objects.filter(is_paid=True).count()

        # ── Revenue ──────────────────────────────────────────────────────────
        total_revenue_aggr = Payment.objects.filter(is_successful=True).aggregate(total=Sum('amount'))
        total_revenue = total_revenue_aggr['total'] if total_revenue_aggr['total'] is not None else 0

        revenue_this_month_aggr = Payment.objects.filter(
            is_successful=True, created_at__gte=thirty_days_ago
        ).aggregate(total=Sum('amount'))
        revenue_this_month = revenue_this_month_aggr['total'] if revenue_this_month_aggr['total'] is not None else 0

        # ── Pending instructor applications ──────────────────────────────────
        from .models import InstructorProfile
        pending_apps_qs = InstructorProfile.objects.filter(
            user__role='STUDENT',
            expertise__isnull=False
        ).exclude(expertise='').select_related('user').order_by('-user__date_joined')[:20]

        pending_instructors = [
            {
                'id': p.user.id,
                'username': p.user.username,
                'email': p.user.email,
                'expertise': p.expertise,
                'years_of_experience': p.years_of_experience,
                'education_level': p.education_level,
                'date_joined': p.user.date_joined.strftime('%b %d, %Y') if p.user.date_joined else ''
            }
            for p in pending_apps_qs
        ]

        # ── Recent users ─────────────────────────────────────────────────────
        recent_users_qs = User.objects.all().order_by('-date_joined')[:10]
        recent_users = [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'role': u.role,
                'joined': u.date_joined.strftime('%b %d, %Y') if u.date_joined else '',
            }
            for u in recent_users_qs
        ]

        # ── Monthly growth (last 6 months) ───────────────────────────────────
        monthly_data = []
        for i in range(5, -1, -1):
            target_date = now - timedelta(days=i * 30)
            month_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            _, last_day = calendar.monthrange(month_start.year, month_start.month)
            month_end = month_start.replace(day=last_day, hour=23, minute=59, second=59)

            month_users = User.objects.filter(date_joined__range=(month_start, month_end)).count()
            month_rev_aggr = Payment.objects.filter(
                is_successful=True, created_at__range=(month_start, month_end)
            ).aggregate(total=Sum('amount'))
            month_revenue = month_rev_aggr['total'] if month_rev_aggr['total'] is not None else 0
            
            monthly_data.append({
                'month': month_start.strftime('%b'),
                'users': month_users,
                'revenue': float(month_revenue),
            })

        # ── Category distribution ─────────────────────────────────────────────
        categories = Category.objects.all().annotate(
            course_count=Count('nodes', distinct=True)
        )
        category_data = [
            {
                'category': cat.name,
                'courses': cat.course_count,
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
                'rating': 5.0 # Institutional baseline
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
                'pending_approval': pending_approval_count,
                'pending_list': pending_courses,
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
 