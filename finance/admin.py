from django.contrib import admin
from .models import Wallet, Transaction, WithdrawalRequest, Payment, LiveStreamPayment

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'total_earned')
    search_fields = ('user__username', 'user__email')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'transaction_type', 'course', 'created_at')
    list_filter = ('transaction_type', 'created_at')

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('instructor', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'amount', 'is_successful', 'created_at')
    list_filter = ('is_successful', 'created_at')

@admin.register(LiveStreamPayment)
class LiveStreamPaymentAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'amount', 'is_successful', 'created_at')
    list_filter = ('is_successful', 'created_at')
