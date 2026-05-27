from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomAuthToken, RegisterView, TicketViewSet, bind_identity, ServiceStarViewSet, ai_chat
from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'service-stars', ServiceStarViewSet, basename='service_star')

urlpatterns = [
    path('login/', CustomAuthToken.as_view(), name='api_login'),
    path('me/', views.get_current_user, name='api_me'),
    path('me/avatar/', views.upload_my_avatar, name='api_me_avatar'),
    path('maintenance-users/', views.get_maintenance_users, name='api_maintenance_users'),
    path('register/', RegisterView.as_view(), name='api_register'),
    path('bind-identity/', bind_identity, name='api_bind_identity'),
    path('', include(router.urls)),
    # path('change_status/<int:order_id>/', views.change_status, name='change_status'),
    path('ai-chat/', ai_chat, name='ai_chat'),
    path('ai/generate_ticket/', views.ai_generate_ticket, name='api_ai_generate_ticket'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
