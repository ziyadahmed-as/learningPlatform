from rest_framework import serializers
from .models import Wallet, Transaction, WithdrawalRequest, Payment, LiveStreamPayment

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'wallet', 'amount', 'course', 'transaction_type', 'created_at']
        read_only_fields = ('reference_id',)

class WalletSerializer(serializers.ModelSerializer):
    transactions = TransactionSerializer(many=True, read_only=True, source='transaction_flow')

    class Meta:
        model = Wallet
        fields = ['id', 'user', 'balance', 'total_earned', 'transactions', 'updated_at']
        read_only_fields = ('user', 'balance', 'total_earned')

class WithdrawalRequestSerializer(serializers.ModelSerializer):
    instructor_name = serializers.ReadOnlyField(source='instructor.username')

    class Meta:
        model = WithdrawalRequest
        fields = ['id', 'instructor', 'instructor_name', 'amount', 'status', 'account_details', 'created_at', 'updated_at']
        read_only_fields = ('instructor', 'status')

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'enrollment', 'amount', 'is_successful', 'created_at']
        read_only_fields = ('checkout_session_id', 'is_successful')

class LiveStreamPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveStreamPayment
        fields = ['id', 'enrollment', 'amount', 'is_successful', 'created_at']
        read_only_fields = ('checkout_session_id', 'is_successful')
