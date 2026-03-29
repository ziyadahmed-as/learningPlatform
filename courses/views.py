from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from .models import (
    Category, Course, Chapter, Lesson, ContentBlock
)
from finance.models import Wallet, Transaction, Payment, WithdrawalRequest
from interactions.models import Enrollment, LessonProgress, CourseView, Review
from .serializers import (
    CategorySerializer, CourseSerializer, ChapterSerializer,
    LessonSerializer, ContentBlockSerializer, EnrollmentSerializer, 
    ReviewSerializer,
    WalletSerializer, TransactionSerializer, WithdrawalRequestSerializer
)
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
import stripe
import decimal

stripe.api_key = settings.STRIPE_SECRET_KEY


def is_admin(user):
    return user.is_authenticated and (user.role == 'ADMIN' or user.is_superuser)


class IsAdminOnly(permissions.BasePermission):
    """Only admins can write; anyone can read."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_admin(request.user)


class IsAdminOrInstructorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.role in ['ADMIN', 'INSTRUCTOR'] or request.user.is_superuser)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if is_admin(request.user):
            return True
        if hasattr(obj, 'instructor'):
            return obj.instructor == request.user
        if hasattr(obj, 'course'): # Chapters, Enrollments
            return obj.course.instructor == request.user
        if hasattr(obj, 'chapter'): # Lessons
            return obj.chapter.course.instructor == request.user
        if hasattr(obj, 'lesson'): # ContentBlock
            return obj.lesson.chapter.course.instructor == request.user
        return False


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Anyone can list/retrieve categories.
    Only admins can create/update/delete.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOnly]


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        # Admins and instructors can see all courses (including unapproved)
        if user.is_authenticated and (is_admin(user) or user.role == 'INSTRUCTOR'):
            return Course.objects.all().select_related('instructor', 'category').prefetch_related('chapters__lessons')
        # Students and anonymous users only see approved courses
        return Course.objects.filter(is_approved=True).select_related('instructor', 'category').prefetch_related('chapters__lessons')

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def approve(self, request, pk=None):
        """Admin-only action to approve a course for learners."""
        if not is_admin(request.user):
            return Response({'detail': 'Only admins can approve courses.'}, status=status.HTTP_403_FORBIDDEN)
        course = self.get_object()
        course.is_approved = True
        course.save()
        return Response({'detail': f'Course "{course.title}" has been approved.'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unapprove(self, request, pk=None):
        """Admin-only action to revoke a course approval."""
        if not is_admin(request.user):
            return Response({'detail': 'Only admins can unapprove courses.'}, status=status.HTTP_403_FORBIDDEN)
        course = self.get_object()
        course.is_approved = False
        course.save()
        return Response({'detail': f'Course "{course.title}" approval has been revoked.'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def submit_for_approval(self, request, pk=None):
        """Instructor action to submit course for admin review."""
        course = self.get_object()
        if course.instructor != request.user and not is_admin(request.user):
            return Response({'detail': 'You do not have permission to submit this course.'}, status=status.HTTP_403_FORBIDDEN)
        course.is_submitted = True
        course.save()
        return Response({'detail': f'Course "{course.title}" has been submitted for approval.'})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def enroll(self, request, pk=None):
        course = self.get_object()
        user = request.user

        # Check if already enrolled
        if Enrollment.objects.filter(student=user, course=course).exists():
            return Response({'detail': 'Already enrolled'}, status=status.HTTP_400_BAD_REQUEST)

        # Determine payment status
        is_paid = course.price == 0

        enrollment = Enrollment.objects.create(student=user, course=course, is_paid=is_paid)
        return Response({'detail': 'Successfully enrolled', 'is_paid': is_paid}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def record_view(self, request, pk=None):
        """Record a view for this course. Deduplicates by user/IP within 24h."""
        course = self.get_object()
        user = request.user if request.user.is_authenticated else None
        ip = request.META.get('REMOTE_ADDR')
        cutoff = timezone.now() - timedelta(hours=24)

        # Check for recent view by same user or IP
        recent = CourseView.objects.filter(course=course, viewed_at__gte=cutoff)
        if user:
            recent = recent.filter(user=user)
        elif ip:
            recent = recent.filter(ip_address=ip, user__isnull=True)
        else:
            recent = recent.none()

        if not recent.exists():
            CourseView.objects.create(course=course, user=user, ip_address=ip)
            course.views_count += 1
            course.save(update_fields=['views_count'])

        return Response({'views_count': course.views_count})

    @action(detail=False, methods=['post'], url_path='generate-description', permission_classes=[permissions.IsAuthenticated])
    def generate_description(self, request):
        """AI-powered auto-generation of course descriptions based on title."""
        title = request.data.get('title', '')
        if not title:
            return Response({'detail': 'Node title required for AI expansion.'}, status=400)
        
        # Simplified AI Mock: In production, this would call OpenAI/Gemini API
        # but the structure is ready for institutional AI synchronization.
        mock_description = f"This comprehensive curriculum for '{title}' is synchronized with global standards. " \
                          f"Students will master core concepts through peer-validated modules and " \
                          f"institutional skill clusters designed for maximum scholarly yield."
        
        return Response({'description': mock_description})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def instructor_stats(self, request):
        """Return aggregated stats for the logged-in instructor's courses."""
        user = request.user
        if user.role not in ['INSTRUCTOR', 'ADMIN'] and not user.is_superuser:
            return Response({'detail': 'Only instructors can view stats.'}, status=status.HTTP_403_FORBIDDEN)

        if user.role == 'INSTRUCTOR':
            courses = Course.objects.filter(instructor=user)
        else:
            courses = Course.objects.all()

        total = courses.count()
        published = courses.filter(is_published=True).count()
        approved = courses.filter(is_approved=True).count()
        pending = courses.filter(is_published=True, is_approved=False).count()
        drafts = courses.filter(is_published=False).count()

        total_enrollments = Enrollment.objects.filter(course__in=courses).count()
        total_views = courses.aggregate(total=Sum('views_count'))['total'] or 0

        # Per-course breakdown
        course_stats = []
        for c in courses.prefetch_related('enrollments'):
            enrollment_count = c.enrollments.count()
            lesson_count = Lesson.objects.filter(chapter__course=c).count()
            completed_count = LessonProgress.objects.filter(
                lesson__chapter__course=c, is_completed=True
            ).count()
            if lesson_count > 0 and enrollment_count > 0:
                completion_pct = round((completed_count / (enrollment_count * lesson_count)) * 100, 1)
            else:
                completion_pct = 0

            course_stats.append({
                'id': c.id,
                'title': c.title,
                'slug': c.slug,
                'is_published': c.is_published,
                'is_approved': c.is_approved,
                'price': str(c.price),
                'enrollment_count': enrollment_count,
                'views_count': c.views_count,
                'completion_percentage': completion_pct,
                'lesson_count': lesson_count,
            })

        return Response({
            'total_courses': total,
            'published': published,
            'approved': approved,
            'pending': pending,
            'drafts': drafts,
            'total_enrollments': total_enrollments,
            'total_views': total_views,
            'courses': course_stats,
        })


class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]


class ContentBlockViewSet(viewsets.ModelViewSet):
    queryset = ContentBlock.objects.all()
    serializer_class = ContentBlockSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]


class LessonViewSet(viewsets.ModelViewSet):
    serializer_class = LessonSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]
    queryset = Lesson.objects.all()

    def get_queryset(self):
        return Lesson.objects.all().select_related('chapter__course').prefetch_related('content_blocks')

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_completed(self, request, pk=None):
        lesson = self.get_object()
        user = request.user

        # Check if student is enrolled
        course = lesson.chapter.course
        if not Enrollment.objects.filter(student=user, course=course).exists():
            return Response({'detail': 'You must be enrolled in this course.'}, status=status.HTTP_403_FORBIDDEN)

        # Sequential progression logic
        all_lessons = Lesson.objects.filter(chapter__course=course).order_by('chapter__order', 'order')
        lesson_ids = list(all_lessons.values_list('id', flat=True))
        try:
            current_index = lesson_ids.index(lesson.id)
        except ValueError:
            return Response({'detail': 'Lesson not found in course.'}, status=status.HTTP_404_NOT_FOUND)

        if current_index > 0:
            prev_lesson_id = lesson_ids[current_index - 1]
            if not LessonProgress.objects.filter(student=user, lesson_id=prev_lesson_id, is_completed=True).exists():
                return Response({'detail': 'Please complete the previous lesson first.'}, status=status.HTTP_400_BAD_REQUEST)

        progress, created = LessonProgress.objects.get_or_create(student=user, lesson=lesson)
        if not progress.is_completed:
            progress.is_completed = True
            progress.save()
            # Add scholarly points for node completion
            user.points += 10
            user.save(update_fields=['points'])

        return Response({'detail': 'Lesson marked as completed.', 'points_earned': 10})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def update_progress(self, request, pk=None):
        lesson = self.get_object()
        user = request.user
        watched_seconds = request.data.get('watched_seconds', 0)

        # Check if student is enrolled
        course = lesson.chapter.course
        if not Enrollment.objects.filter(student=user, course=course).exists():
            return Response({'detail': 'You must be enrolled in this course.'}, status=status.HTTP_403_FORBIDDEN)

        progress, created = LessonProgress.objects.get_or_create(student=user, lesson=lesson)
        
        try:
            new_seconds = int(watched_seconds)
            if new_seconds > progress.watched_seconds:
                progress.watched_seconds = new_seconds
                progress.save()
        except (ValueError, TypeError):
            pass

        return Response({
            'detail': 'Progress updated.', 
            'watched_seconds': progress.watched_seconds,
            'is_completed': progress.is_completed
        })




class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Enrollment.objects.filter(student=self.request.user)

    @action(detail=True, methods=['post'])
    def create_checkout_session(self, request, pk=None):
        enrollment = self.get_object()
        if enrollment.is_paid:
            return Response({'detail': 'Already paid'}, status=status.HTTP_400_BAD_REQUEST)

        payment, created = Payment.objects.get_or_create(
            enrollment=enrollment,
            defaults={'amount': enrollment.course.price}
        )

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {'name': enrollment.course.title},
                            'unit_amount': int(enrollment.course.price * 100),
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=settings.FRONTEND_URL + '?success=true',
                cancel_url=settings.FRONTEND_URL + '?canceled=true',
                client_reference_id=str(payment.id),
            )
            payment.checkout_session_id = checkout_session.id
            payment.save()
            return Response({'url': checkout_session.url})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        payment_id = session.get('client_reference_id')
        if payment_id:
            try:
                payment = Payment.objects.get(id=payment_id)
                payment.is_successful = True
                payment.save()
                enrollment = payment.enrollment
                enrollment.is_paid = True
                enrollment.save()

                # Handle Instructor Earnings
                course = enrollment.course
                instructor = course.instructor
                amount = payment.amount
                
                # Platform takes 20% commission
                commission_rate = 0.20
                commission = amount * decimal.Decimal(commission_rate)
                earnings = amount - commission

                wallet, created = Wallet.objects.get_or_create(user=instructor)
                wallet.balance += earnings
                wallet.total_earned += earnings
                wallet.save()

                # Add scholarly points to instructor for successful knowledge transfer
                instructor.points += 50
                instructor.save(update_fields=['points'])

                Transaction.objects.create(
                    wallet=wallet,
                    amount=earnings,
                    course=course,
                    transaction_type='SALE'
                )
            except Payment.DoesNotExist:
                pass
            except Exception as e:
                # Log error in production
                print(f"Error processing payment earnings: {e}")

    return Response(status=status.HTTP_200_OK)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Wallet.objects.filter(user=self.request.user)


class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if is_admin(self.request.user):
            return WithdrawalRequest.objects.all()
        return WithdrawalRequest.objects.filter(instructor=self.request.user)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOnly])
    def approve(self, request, pk=None):
        withdrawal = self.get_object()
        if withdrawal.status != 'PENDING':
            return Response({'detail': 'Request already processed.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check wallet balance
        wallet = Wallet.objects.get(user=withdrawal.instructor)
        if wallet.balance < withdrawal.amount:
            return Response({'detail': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)

        withdrawal.status = 'APPROVED'
        withdrawal.save()
        
        # Deduct from wallet
        wallet.balance -= withdrawal.amount
        wallet.save()

        Transaction.objects.create(
            wallet=wallet,
            amount=-withdrawal.amount,
            transaction_type='WITHDRAWAL'
        )
        return Response({'detail': 'Withdrawal approved.'})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOnly])
    def mark_paid(self, request, pk=None):
        withdrawal = self.get_object()
        if withdrawal.status != 'APPROVED':
            return Response({'detail': 'Request must be approved first.'}, status=status.HTTP_400_BAD_REQUEST)
        withdrawal.status = 'PAID'
        withdrawal.save()
        return Response({'detail': 'Withdrawal marked as paid.'})
