from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from .models import Wallet, Transaction, WithdrawalRequest, Payment, LiveStreamPayment
from .serializers import (
    WalletSerializer, TransactionSerializer, WithdrawalRequestSerializer, 
    PaymentSerializer, LiveStreamPaymentSerializer
)
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import stripe
import decimal

stripe.api_key = settings.STRIPE_SECRET_KEY

class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(wallet__user=self.request.user)

class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    queryset = WithdrawalRequest.objects.all()
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'ADMIN' or self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(instructor=self.request.user)

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def approve(self, request, pk=None):
        withdrawal = self.get_object()
        if withdrawal.status != 'PENDING':
            return Response({'detail': 'Request already processed.'}, status=status.HTTP_400_BAD_REQUEST)
        
        wallet = Wallet.objects.get(user=withdrawal.instructor)
        if wallet.balance < withdrawal.amount:
            return Response({'detail': 'Insufficient balance.'}, status=status.HTTP_400_BAD_REQUEST)

        withdrawal.status = 'APPROVED'
        withdrawal.save()
        
        wallet.balance -= withdrawal.amount
        wallet.save()

        Transaction.objects.create(
            wallet=wallet,
            amount=-withdrawal.amount,
            transaction_type='WITHDRAWAL'
        )
        return Response({'detail': 'Withdrawal approved.'})

class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(enrollment__student=self.request.user)

    @action(detail=True, methods=['post'])
    def create_checkout_session(self, request, pk=None):
        payment = self.get_object()
        enrollment = payment.enrollment
        if enrollment.is_paid:
            return Response({'detail': 'Already paid'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {'name': enrollment.course.title},
                            'unit_amount': int(payment.amount * 100),
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
    except Exception:
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

                # Commissioning Logic
                instructor = enrollment.course.instructor
                earnings = payment.amount * decimal.Decimal(0.80) # 80% to instructor
                
                wallet, created = Wallet.objects.get_or_create(user=instructor)
                wallet.balance += earnings
                wallet.total_earned += earnings
                wallet.save()

                instructor.points += 50
                instructor.save(update_fields=['points'])

                Transaction.objects.create(
                    wallet=wallet, amount=earnings, 
                    course=enrollment.course, transaction_type='SALE'
                )
            except Payment.DoesNotExist:
                pass

    return Response(status=status.HTTP_200_OK)
