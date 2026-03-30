from django.db import models
from django.conf import settings
from core.models import BaseModel
import uuid

class Wallet(BaseModel):
    """
    Identity Equity Hub for instructors and scholarly stakeholders.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet_record')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = 'Equity Hub'
        indexes = [
            models.Index(fields=['user', 'balance']),
        ]

    def __str__(self):
        return f'Node Equity: {self.user.username} - ${self.balance}'

class Transaction(BaseModel):
    """
    Temporal Flow of institutional capital.
    """
    class TransactionType(models.TextChoices):
        SALE = 'SALE', 'Registry Sale'
        WITHDRAWAL = 'WITHDRAWAL', 'System Withdrawal'
    
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transaction_flow')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    reference_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Signal: {self.transaction_type} ({self.amount}) for {self.wallet.user.username}'

class WithdrawalRequest(BaseModel):
    """
    Root Authorization for capital extraction.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'System Approved'
        REJECTED = 'REJECTED', 'Protocol Rejected'
        PAID = 'PAID', 'Signal Paid'

    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default=Status.PENDING, choices=Status.choices)
    account_details = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Withdrawal Hub: {self.amount} for {self.instructor.username}'

# Note: Payment is often tied to a specific provider/gateway, so we'll keep it as a scalable hub
class Payment(BaseModel):
    """
    Stripe Signal Synchronization.
    """
    enrollment = models.OneToOneField('interactions.Enrollment', on_delete=models.CASCADE, related_name='payment_artifact')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    checkout_session_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    is_successful = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f'Payment Artifact: {self.amount} (Success: {self.is_successful})'

class LiveStreamPayment(BaseModel):
    """
    Stripe Signal Synchronization for Live Streams.
    """
    enrollment = models.OneToOneField('interactions.LiveStreamEnrollment', on_delete=models.CASCADE, related_name='payment_artifact')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=5000.00)
    checkout_session_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    is_successful = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f'Live Stream Payment: {self.amount} (Success: {self.is_successful})'
