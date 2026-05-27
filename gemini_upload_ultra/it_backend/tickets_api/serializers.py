from rest_framework import serializers
from .models import CustomUser, Ticket, TicketAttachment, ServiceStar


class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    maintenance_info = serializers.SerializerMethodField()
    contact_phone = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'name', 'gender', 'avatar', 'role', 'identity_id', 'is_identity_bound', 'maintenance_info', 'contact_phone']

    def get_avatar(self, obj):
        request = self.context.get('request')
        url = getattr(obj, 'avatar_display', '') or ''
        if request and url and not url.startswith('http'):
            url = request.build_absolute_uri(url)
        return url

    def get_maintenance_info(self, obj):
        if obj.role == 'maintenance' and hasattr(obj, 'maintenance_profile'):
            return {
                'department': obj.maintenance_profile.department,
                'contact_phone': obj.maintenance_profile.contact_phone
            }
        return None

    def get_contact_phone(self, obj):
        if obj.role == 'maintenance' and hasattr(obj, 'maintenance_profile'):
            return obj.maintenance_profile.contact_phone
        if obj.role == 'auditor' and hasattr(obj, 'auditor_profile'):
            return getattr(obj.auditor_profile, 'contact_phone', '')
        return ''


class RegisterSerializer(serializers.ModelSerializer):
    # 1. 删除了所有的 required=True，变成可选

    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'name', 'role', 'identity_id']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            role='student',
            identity_id=None,
            is_identity_bound=False,
            is_staff=False,
            is_superuser=False
        )
        return user


class TicketSerializer(serializers.ModelSerializer):
    submitter_name = serializers.SerializerMethodField()
    submitter_identity_id = serializers.SerializerMethodField()
    assignee_name = serializers.SerializerMethodField()
    assignee_department = serializers.SerializerMethodField()
    assignee_contact = serializers.SerializerMethodField()
    auditor_name = serializers.SerializerMethodField()
    auditor_contact = serializers.SerializerMethodField()
    # 强制只读，防止前端传错报 400
    status = serializers.CharField(read_only=True)
    rejected_reason = serializers.CharField(read_only=True)
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = [
            'submitter',
            'status',
            'submitTime',
            'updateTime',
            'ai_auto_approved',
            'ai_auto_checked_at',
            'ai_suggested_category',
            'ai_auto_reason',
            'reimbursement_no',
            'reimbursement_text',
            'reimbursement_generated_at',
        ]

    def get_attachments(self, obj):
        request = self.context.get('request')
        items = []
        for a in obj.attachments.all().order_by('id'):
            url = a.file.url if a.file else ''
            if request and url and not url.startswith('http'):
                url = request.build_absolute_uri(url)
            items.append({
                'id': a.id,
                'media_type': a.media_type,
                'url': url,
                'original_name': a.original_name,
                'uploaded_at': a.uploaded_at
            })
        return items

    def get_submitter_name(self, obj):
        request = self.context.get('request')
        if not request:
            return getattr(obj.submitter, 'name', '') or getattr(obj.submitter, 'username', '') or ''
        viewer = getattr(request, 'user', None)
        if getattr(obj, 'is_anonymous', False) and getattr(obj, 'status', '') == 'closed':
            if viewer and getattr(viewer, 'role', None) == 'maintenance':
                return '匿名'
        return getattr(obj.submitter, 'name', '') or getattr(obj.submitter, 'username', '') or ''

    def get_submitter_identity_id(self, obj):
        return (getattr(getattr(obj, 'submitter', None), 'identity_id', None) or '').strip()

    def get_assignee_name(self, obj):
        return getattr(obj.assignee, 'name', '') or getattr(obj.assignee, 'username', '') or ''

    def get_assignee_department(self, obj):
        if obj.assignee and hasattr(obj.assignee, 'maintenance_profile'):
            return obj.assignee.maintenance_profile.department
        return ''

    def get_assignee_contact(self, obj):
        if obj.assignee and hasattr(obj.assignee, 'maintenance_profile'):
            return obj.assignee.maintenance_profile.contact_phone
        return ''

    def get_auditor_name(self, obj):
        return getattr(obj.auditor, 'name', '') or getattr(obj.auditor, 'username', '') or ''

    def get_auditor_contact(self, obj):
        if obj.auditor and hasattr(obj.auditor, 'auditor_profile'):
            return getattr(obj.auditor.auditor_profile, 'contact_phone', '') or ''
        return ''


class TicketAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketAttachment
        fields = ['id', 'ticket', 'media_type', 'file', 'original_name', 'uploaded_at']
        read_only_fields = ['id', 'ticket', 'media_type', 'original_name', 'uploaded_at']


class ServiceStarSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceStar
        fields = '__all__'
