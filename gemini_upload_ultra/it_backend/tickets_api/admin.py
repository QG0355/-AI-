from django.contrib import admin
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
from .models import Ticket, ServiceStar, CustomUser, TicketAttachment, AiChatLog, AiSetting
from .simple_sync import sync_user as sync_user_simple, sync_service_star as sync_service_star_simple

# 隐藏不需要的默认模块（认证与授权、Token等）
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(Token)
except admin.sites.NotRegistered:
    pass


@admin.register(AiChatLog)
class AiChatLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'mode', 'ai_enabled', 'created_at')
    list_filter = ('mode', 'ai_enabled', 'created_at')
    search_fields = ('user__username', 'question', 'answer')
    readonly_fields = ('user', 'question', 'answer', 'mode', 'ai_enabled', 'warning', 'created_at')

    def has_module_permission(self, request):
        return getattr(request.user, 'role', None) in {'admin', 'auditor'}

    def has_view_permission(self, request, obj=None):
        return getattr(request.user, 'role', None) in {'admin', 'auditor'}

    def has_add_permission(self, request):
        return False


@admin.register(AiSetting)
class AiSettingAdmin(admin.ModelAdmin):
    list_display = ('enabled', 'llm_enabled', 'api_base_url', 'api_model', 'api_model_deep', 'timeout_seconds', 'updated_at')
    readonly_fields = ('updated_at',)

    def has_module_permission(self, request):
        return getattr(request.user, 'role', None) == 'admin'

    def has_view_permission(self, request, obj=None):
        return getattr(request.user, 'role', None) == 'admin'

    def has_add_permission(self, request):
        return getattr(request.user, 'role', None) == 'admin'

    def has_change_permission(self, request, obj=None):
        return getattr(request.user, 'role', None) == 'admin'

    def has_delete_permission(self, request, obj=None):
        return getattr(request.user, 'role', None) == 'admin'


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'status', 'ai_auto_approved', 'ai_suggested_category', 'submitter', 'assignee', 'auditor', 'submitTime')
    list_filter = ('category', 'status', 'ai_auto_approved')
    search_fields = ('title', 'description', 'location', 'submitter__username', 'auditor__username')


@admin.register(ServiceStar)
class ServiceStarAdmin(admin.ModelAdmin):
    list_display = ('name', 'honor', 'score', 'score_count', 'sort_order', 'is_active')
    list_editable = ('score', 'score_count', 'sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'honor')
    ordering = ('sort_order', '-id')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            sync_service_star_simple(obj)
        except Exception:
            pass


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'name', 'role', 'identity_id', 'is_identity_bound')
    list_filter = ('role', 'is_identity_bound')
    search_fields = ('username', 'name', 'identity_id')
    fieldsets = (
        ('基础信息', {
            'fields': ('username', 'password', 'name', 'gender', 'role')
        }),
        ('身份绑定', {
            'fields': ('identity_id', 'is_identity_bound')
        }),
        ('头像', {
            'fields': ('avatar', 'avatar_url')
        }),
    )

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change, **kwargs)
        avatar_url_field = form.base_fields.get('avatar_url')
        if avatar_url_field:
            avatar_url_field.required = False
        return form

    def save_model(self, request, obj, form, change):
        raw_password = obj.password or ''
        if raw_password and not (
            raw_password.startswith('pbkdf2_')
            or raw_password.startswith('argon2$')
            or raw_password.startswith('bcrypt$')
            or raw_password.startswith('scrypt$')
        ):
            obj.set_password(raw_password)
        
        # 如果角色是管理员或审核员，自动赋予登录后台的权限
        if obj.role in ['admin', 'auditor']:
            obj.is_staff = True
        else:
            obj.is_staff = False
            
        super().save_model(request, obj, form, change)
        try:
            sync_user_simple(obj)
        except Exception:
            pass


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'media_type', 'original_name', 'uploaded_at')
    list_filter = ('media_type',)
    search_fields = ('ticket__title', 'original_name')
