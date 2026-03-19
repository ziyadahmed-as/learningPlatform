from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from .models import Category, Course, Module, Lesson, Enrollment, Payment
from .serializers import CategorySerializer, CourseSerializer, ModuleSerializer, LessonSerializer, EnrollmentSerializer
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

class IsAdminOrInstructorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.role in ['ADMIN', 'INSTRUCTOR'] or request.user.is_superuser)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.role == 'ADMIN' or request.user.is_superuser:
            return True
        # Ensure only the course instructor can modify it
        if hasattr(obj, 'instructor'):
            return obj.instructor == request.user
        if hasattr(obj, 'course'):
            return obj.course.instructor == request.user
        if hasattr(obj, 'module'):
            return obj.module.course.instructor == request.user
        return False

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().select_related('instructor', 'category').prefetch_related('modules__lessons')
    serializer_class = CourseSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)
        
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

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all().select_related('course')
    serializer_class = ModuleSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all().select_related('module__course')
    serializer_class = LessonSerializer
    permission_classes = [IsAdminOrInstructorOrReadOnly]

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

        # Create Payment record if it doesn't exist
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
                            'product_data': {
                                'name': enrollment.course.title,
                            },
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
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except stripe.error.SignatureVerificationError as e:
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
            except Payment.DoesNotExist:
                pass

    return Response(status=status.HTTP_200_OK)
