from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WalletViewSet, TransactionViewSet, WithdrawalRequestViewSet, 
    PaymentViewSet, stripe_webhook
)

router = DefaultRouter()
router.register(r'wallet', WalletViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'withdrawals', WithdrawalRequestViewSet)
router.register(r'payments', PaymentViewSet)

urlpatterns = [
    path('webhook/stripe/', stripe_webhook, name='stripe-webhook'),
    path('', include(router.urls)),
]
