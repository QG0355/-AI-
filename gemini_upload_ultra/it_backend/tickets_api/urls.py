"""
tickets_api 路由入口（/api/ 下的所有业务接口）。

总体约定：
- /api/login/：用户名密码登录，返回 Token
- /api/me/：获取/修改当前用户信息（个人主页用）
- /api/bind-identity/：身份绑定（学号/工号等）
- /api/tickets/...：工单 CRUD、审核、派单、维修、评价等
- /api/ai-chat/：AI 助手对话
"""

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
    path('forgot-password/', views.forgot_password, name='api_forgot_password'),
    path('bind-identity/', bind_identity, name='api_bind_identity'),
    path('', include(router.urls)),
    # path('change_status/<int:order_id>/', views.change_status, name='change_status'),
    path('ai-chat/', ai_chat, name='ai_chat'),
    path('ai/generate_ticket/', views.ai_generate_ticket, name='api_ai_generate_ticket'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
