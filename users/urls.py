from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from users.views import RegisterView, UserDetailView, AdminUserViewSet, AdminStatsView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'manage', AdminUserViewSet, basename='manage-users')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', UserDetailView.as_view(), name='user_detail'),
    path('admin-stats/', AdminStatsView.as_view(), name='admin-stats'),
    path('', include(router.urls)),
]
