"""
后端接口实现（Django REST Framework Views）。

本文件是后端业务逻辑的“总入口”，包含：
- 登录/注册/当前用户信息（/api/login/、/api/register/、/api/me/）
- 身份绑定（/api/bind-identity/）：学号/工号绑定、角色确定、手机号绑定策略等
- 忘记密码（/api/forgot-password/）：通过 学号/工号 + 手机号 校验后重置
- 工单 Ticket 的全流程接口（提交、查询、审核、派单、维修、评价、附件等）
- AI 助手接口与 AI 配置读取

权限总体规则（简化说明）：
- Token 登录后通过 Authorization: Token <token> 访问受保护接口
- admin/auditor 具备更高权限（可看全量工单/配置等）
"""

from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes, action, parser_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Avg, Count
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from .models import ServiceStar, StudentProfile, MaintenanceProfile, AuditorProfile, AdminProfile, AiSetting, AiChatLog
from rest_framework import filters
import os
import json
import re
import logging
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .models import CustomUser, Ticket
from .serializers import UserSerializer, RegisterSerializer, TicketSerializer, ServiceStarSerializer
from .models import TicketAttachment
from .simple_sync import sync_user as sync_user_simple, sync_ticket as sync_ticket_simple


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    """
    获取/更新当前登录用户信息。

    GET：
    - 返回 UserSerializer 序列化后的用户信息（个人主页展示）

    PATCH：
    - 支持更新 name/gender/phone
    - maintenance/auditor 角色会同步更新对应 Profile 的联系电话字段
    - 管理员账号不需要手机号，后端会拒绝更新 phone
    """
    user = request.user
    if request.method == 'PATCH':
        updates = {}
        profile_updates = {}
        if 'name' in request.data:
            name = (request.data.get('name') or '').strip()
            if not name:
                return Response({"detail": "姓名不能为空"}, status=status.HTTP_400_BAD_REQUEST)
            updates['name'] = name
        if 'gender' in request.data:
            gender = (request.data.get('gender') or '').strip()
            if gender not in {'unknown', 'male', 'female'}:
                return Response({"detail": "性别不合法"}, status=status.HTTP_400_BAD_REQUEST)
            updates['gender'] = gender

        if 'phone' in request.data:
            if getattr(user, 'role', None) == 'admin' or getattr(user, 'is_superuser', False):
                return Response({"detail": "管理员账号不需要绑定手机号"}, status=status.HTTP_400_BAD_REQUEST)
            phone = (request.data.get('phone') or '').strip()
            if not phone:
                return Response({"detail": "手机号不能为空"}, status=status.HTTP_400_BAD_REQUEST)
            if not re.fullmatch(r'\d{6,20}', phone):
                return Response({"detail": "手机号格式不正确"}, status=status.HTTP_400_BAD_REQUEST)
            updates['phone'] = phone
            if getattr(user, 'role', None) == 'maintenance':
                profile_updates['contact_phone'] = phone
            if getattr(user, 'role', None) == 'auditor':
                profile_updates['auditor_contact_phone'] = phone

        if getattr(user, 'role', None) == 'maintenance':
            if 'department' in request.data:
                department = (request.data.get('department') or '').strip()
                if len(department) > 100:
                    return Response({"detail": "部门/工种过长"}, status=status.HTTP_400_BAD_REQUEST)
                profile_updates['department'] = department
            if 'contact_phone' in request.data:
                contact_phone = (request.data.get('contact_phone') or '').strip()
                if len(contact_phone) > 20:
                    return Response({"detail": "联系电话过长"}, status=status.HTTP_400_BAD_REQUEST)
                profile_updates['contact_phone'] = contact_phone
        if getattr(user, 'role', None) == 'auditor':
            if 'contact_phone' in request.data:
                contact_phone = (request.data.get('contact_phone') or '').strip()
                if len(contact_phone) > 20:
                    return Response({"detail": "联系电话过长"}, status=status.HTTP_400_BAD_REQUEST)
                profile_updates['auditor_contact_phone'] = contact_phone

        if not updates and not profile_updates:
            return Response({"detail": "没有可更新的字段"}, status=status.HTTP_400_BAD_REQUEST)

        for k, v in updates.items():
            setattr(user, k, v)
        if updates:
            user.save(update_fields=list(updates.keys()))

        if profile_updates:
            if getattr(user, 'role', None) == 'maintenance':
                mp, _ = MaintenanceProfile.objects.get_or_create(
                    user=user,
                    defaults={'worker_id': user.identity_id or str(user.pk)}
                )
                for k, v in profile_updates.items():
                    setattr(mp, k, v)
                mp.save(update_fields=list(profile_updates.keys()))
            if getattr(user, 'role', None) == 'auditor':
                ap, _ = AuditorProfile.objects.get_or_create(
                    user=user,
                    defaults={'auditor_id': user.identity_id or str(user.pk)}
                )
                if 'auditor_contact_phone' in profile_updates:
                    ap.contact_phone = profile_updates['auditor_contact_phone']
                    ap.save(update_fields=['contact_phone'])
    data = UserSerializer(user, context={'request': request}).data
    if getattr(user, 'role', None) == 'maintenance':
        agg = Ticket.objects.filter(assignee=user, status='closed').aggregate(avg=Avg('rating'), cnt=Count('id'))
        avg = agg.get('avg')
        data['maintenance_rating'] = float(avg) if avg is not None else None
        data['maintenance_rating_count'] = int(agg.get('cnt') or 0)
    return Response(data)


# 1. Login View
class CustomAuthToken(ObtainAuthToken):
    """用户名密码登录：返回 Token + 当前用户信息。"""
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user, context={'request': request}).data})


# 2. Register View
class RegisterView(generics.CreateAPIView):
    """
    注册接口：只创建基础账号。

    设计理由：
    - 注册后账号默认 role=student，但 is_identity_bound=False
    - 用户需要到 /bind 页面完成实名信息（学号/工号、角色、姓名）
    """
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """
    忘记密码（重置密码）。

    校验规则：
    - 仅允许普通账号（学生/维修/审核），管理员/超级管理员不支持找回密码
    - 必须已绑定身份（is_identity_bound=True）
    - 必须同时校验 identity_id（学号/工号）与 phone（手机号）都匹配
    - 重置后删除旧 Token，强制重新登录
    """
    username = (request.data.get('username') or '').strip()
    identity_id = (request.data.get('identity_id') or '').strip()
    phone = (request.data.get('phone') or '').strip()
    new_password = (request.data.get('new_password') or '').strip()

    if not username:
        return Response({'detail': '账号不能为空'}, status=status.HTTP_400_BAD_REQUEST)
    if not identity_id:
        return Response({'detail': '学号/工号不能为空'}, status=status.HTTP_400_BAD_REQUEST)
    if not new_password:
        return Response({'detail': '新密码不能为空'}, status=status.HTTP_400_BAD_REQUEST)
    if len(new_password) < 6:
        return Response({'detail': '新密码长度至少 6 位'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.get(username=username)
    except CustomUser.DoesNotExist:
        return Response({'detail': '账号不存在'}, status=status.HTTP_400_BAD_REQUEST)

    if getattr(user, 'role', None) == 'admin' or getattr(user, 'is_superuser', False):
        return Response({'detail': '管理员账号不支持找回密码'}, status=status.HTTP_400_BAD_REQUEST)

    if not phone:
        return Response({'detail': '手机号不能为空'}, status=status.HTTP_400_BAD_REQUEST)
    if not re.fullmatch(r'\d{6,20}', phone):
        return Response({'detail': '手机号格式不正确'}, status=status.HTTP_400_BAD_REQUEST)

    if not getattr(user, 'is_identity_bound', False):
        return Response({'detail': '该账号尚未绑定学号/工号，无法重置密码'}, status=status.HTTP_400_BAD_REQUEST)
    if (getattr(user, 'identity_id', None) or '').strip() != identity_id:
        return Response({'detail': '学号/工号不匹配'}, status=status.HTTP_400_BAD_REQUEST)
    if not (getattr(user, 'phone', '') or '').strip():
        return Response({'detail': '该账号尚未绑定手机号，无法重置密码'}, status=status.HTTP_400_BAD_REQUEST)
    if (getattr(user, 'phone', '') or '').strip() != phone:
        return Response({'detail': '手机号不匹配'}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save(update_fields=['password'])
    Token.objects.filter(user=user).delete()
    return Response({'detail': '密码已重置，请重新登录'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_maintenance_users(request):
    """
    获取可派单的维修人员列表（给审核员/管理员派单页面用）。

    权限：
    - 仅 admin/auditor 可访问

    返回：
    - 只返回“部门/工种 + 联系电话”都已完善的维修人员
    """
    user = request.user
    if user.role not in ['admin', 'auditor']:
        return Response({'detail': '无权限查看维修人员列表'}, status=status.HTTP_403_FORBIDDEN)
    qs = CustomUser.objects.filter(role='maintenance').select_related('maintenance_profile').order_by('id')
    data = [
        {
            'id': u.id,
            'name': (u.name or u.username),
            'identity_id': u.identity_id,
            'username': u.username,
            'department': getattr(getattr(u, 'maintenance_profile', None), 'department', '') or '',
            'contact_phone': getattr(getattr(u, 'maintenance_profile', None), 'contact_phone', '') or '',
        }
        for u in qs
        if (getattr(getattr(u, 'maintenance_profile', None), 'department', '') or '').strip()
        and (getattr(getattr(u, 'maintenance_profile', None), 'contact_phone', '') or '').strip()
    ]
    return Response(data)


# 3. Identity Bind View (Kept to prevent 404s from frontend, though logic is simplified)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bind_identity(request):
    """
    身份绑定接口（实名信息补全）。

    绑定内容：
    - role：student/maintenance/auditor（不允许通过该接口绑定 admin，防止提权）
    - identity_id：学号/工号（全局唯一）
    - name：真实姓名

    手机号策略（前端统一在个人主页绑定）：
    - 首次绑定身份时 phone 可不填
    - 绑定后如提交 phone，则可用于更新手机号（并同步到维修/审核的 Profile）
    """
    user = request.user
    existed_phone = (getattr(user, 'phone', '') or '').strip()
    phone = (request.data.get('phone') or '').strip()
    if user.is_identity_bound:
        if phone:
            if not re.fullmatch(r'\d{6,20}', phone):
                return Response({"detail": "手机号格式不正确"}, status=status.HTTP_400_BAD_REQUEST)
            if existed_phone != phone:
                user.phone = phone
                user.save(update_fields=['phone'])
                if getattr(user, 'role', None) == 'maintenance':
                    MaintenanceProfile.objects.update_or_create(user=user, defaults={'worker_id': user.identity_id or str(user.pk), 'contact_phone': phone})
                if getattr(user, 'role', None) == 'auditor':
                    AuditorProfile.objects.update_or_create(user=user, defaults={'auditor_id': user.identity_id or str(user.pk), 'contact_phone': phone})
                return Response({"detail": "手机号已更新", "user": UserSerializer(user, context={'request': request}).data}, status=200)
        return Response({"detail": "您已经绑定过身份，无需重复操作", "user": UserSerializer(user, context={'request': request}).data}, status=200)

    role = (request.data.get('role') or '').strip()
    identity_id = (request.data.get('identity_id') or '').strip()
    name = (request.data.get('name') or '').strip()

    if role not in {'student', 'maintenance', 'auditor'}:
        return Response({"detail": "角色不合法"}, status=status.HTTP_400_BAD_REQUEST)
    if not identity_id:
        return Response({"detail": "工号/学号不能为空"}, status=status.HTTP_400_BAD_REQUEST)
    if phone and not re.fullmatch(r'\d{6,20}', phone):
        return Response({"detail": "手机号格式不正确"}, status=status.HTTP_400_BAD_REQUEST)
    if CustomUser.objects.filter(identity_id=identity_id).exclude(pk=user.pk).exists():
        return Response({"detail": "该工号/学号已被绑定，请确认后重试"}, status=status.HTTP_400_BAD_REQUEST)

    user.role = role
    user.identity_id = identity_id
    user.name = name
    user.phone = phone
    user.is_identity_bound = True
    if role in {'auditor'}:
        user.is_staff = True
    else:
        user.is_staff = False
    try:
        user.save()
    except IntegrityError:
        return Response({"detail": "该工号/学号已被绑定，请确认后重试"}, status=status.HTTP_400_BAD_REQUEST)

    if role == 'student':
        StudentProfile.objects.update_or_create(user=user, defaults={'student_id': identity_id})
    elif role == 'maintenance':
        defaults = {'worker_id': identity_id}
        if phone:
            defaults['contact_phone'] = phone
        MaintenanceProfile.objects.update_or_create(user=user, defaults=defaults)
    elif role == 'auditor':
        defaults = {'auditor_id': identity_id}
        if phone:
            defaults['contact_phone'] = phone
        AuditorProfile.objects.update_or_create(user=user, defaults=defaults)

    try:
        sync_user_simple(user)
    except Exception:
        pass

    return Response({"detail": "绑定成功", "user": UserSerializer(user, context={'request': request}).data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_my_avatar(request):
    """
    上传当前用户头像（本地文件上传）。

    约束：
    - 仅允许图片类型（JPG/PNG/WEBP/GIF）
    - 最大 5MB
    """
    user = request.user
    f = request.FILES.get('file') or request.FILES.get('avatar')
    if not f:
        return Response({"detail": "请上传头像文件(file)"}, status=status.HTTP_400_BAD_REQUEST)

    content_type = (getattr(f, 'content_type', '') or '').lower()
    allowed_types = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
    if content_type and content_type not in allowed_types:
        return Response({"detail": "仅支持 JPG/PNG/WEBP/GIF 图片"}, status=status.HTTP_400_BAD_REQUEST)

    if f.size and f.size > 5 * 1024 * 1024:
        return Response({"detail": "图片大小不能超过 5MB"}, status=status.HTTP_400_BAD_REQUEST)

    old_name = getattr(getattr(user, 'avatar', None), 'name', '') or ''
    user.avatar = f
    user.avatar_url = ''
    user.save(update_fields=['avatar', 'avatar_url'])

    if old_name and old_name != getattr(user.avatar, 'name', ''):
        try:
            user.avatar.storage.delete(old_name)
        except Exception:
            pass

    return Response(UserSerializer(user, context={'request': request}).data)


# 4. Ticket ViewSet
class TicketViewSet(viewsets.ModelViewSet):
    """
    工单视图集（Ticket CRUD + 自定义动作）。

    用法：
    - list/retrieve/create/update/destroy：DRF 标准接口
    - 额外 action：审核（review）、派单、接单、维修完成、评价、导出报修单等
    """
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description', 'location', 'id']
    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.all()
        # Admin 和 审核员 作为审核 / 管理角色，看到全部工单
        if user.role in ['admin', 'auditor']:
            pass
        # 维修人员仅看到指派给自己的工单
        elif user.role == 'maintenance':
            qs = qs.filter(assignee=user)
        # 其他角色只看到自己提交的工单
        else:
            qs = qs.filter(submitter=user)

        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        ai_flagged = (self.request.query_params.get('ai_flagged') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
        if ai_flagged:
            qs = qs.filter(status='pending_dorm', ai_auto_checked_at__isnull=False, ai_auto_approved=False)
        return qs

    def perform_create(self, serializer):
        # 新建工单默认进入“待审核员审核”状态
        ticket = serializer.save(submitter=self.request.user, status='pending_dorm')
        try:
            sync_ticket_simple(ticket)
        except Exception:
            pass

    def perform_update(self, serializer):
        ticket = self.get_object()
        user = self.request.user
        if user.role == 'student':
            if ticket.submitter != user:
                raise PermissionDenied('只能修改自己提交的工单')
            if ticket.status != 'rejected':
                raise PermissionDenied('仅可修改被驳回的工单')
            updated = serializer.save(status='pending_dorm', rejected_reason=None)
            try:
                sync_ticket_simple(updated)
            except Exception:
                pass
            return
        updated = serializer.save()
        try:
            sync_ticket_simple(updated)
        except Exception:
            pass

    def destroy(self, request, *args, **kwargs):
        ticket = self.get_object()
        user = request.user

        if user.role == 'student':
            if ticket.submitter != user:
                return Response({'detail': '只能撤销自己提交的工单'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.status not in ['pending_dorm', 'rejected']:
                return Response({'detail': '当前状态不可撤销'}, status=status.HTTP_400_BAD_REQUEST)
        elif user.role in ['admin', 'auditor']:
            pass
        else:
            return Response({'detail': '无权撤销工单'}, status=status.HTTP_403_FORBIDDEN)

        ticket.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Ticket Handling Action (Assign, Finish, Evaluate)
    @action(detail=True, methods=['post'])
    def handle(self, request, pk=None):
        ticket = self.get_object()
        user = request.user
        action_type = request.data.get('type')

        # 权限控制：学生不能接单、派单、或完成维修
        if user.role == 'student':
            # 学生只能做“评价”或“取消工单”（如果允许的话），不能做 assign/finish
            # 这里先全部拦截，只允许后续加 evaluate
            if action_type in ['assign', 'finish', 'dispatch', 'return']:
                return Response({'detail': '学生无权执行此操作'}, status=status.HTTP_403_FORBIDDEN)

        # Dispatch (Assign)
        if action_type == 'assign':
            if user.role not in ['admin', 'auditor']:
                 return Response({'detail': '无权派单'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.status != 'pending_dispatch':
                return Response({'detail': '当前状态不可派单'}, status=status.HTTP_400_BAD_REQUEST)

            if user.role == 'auditor':
                ap = getattr(user, 'auditor_profile', None)
                if not (getattr(ap, 'contact_phone', '') or '').strip():
                    return Response({'detail': '请先在工作台填写并保存审核员联系电话后再派单'}, status=status.HTTP_400_BAD_REQUEST)
            
            worker_id = request.data.get('worker_id')
            if not worker_id:
                return Response({'detail': '请选择维修人员'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                worker = CustomUser.objects.get(pk=worker_id)
                if worker.role != 'maintenance':
                    return Response({'detail': '派单对象必须是维修人员'}, status=status.HTTP_400_BAD_REQUEST)
                mp = getattr(worker, 'maintenance_profile', None)
                if not mp or not (mp.contact_phone or '').strip() or not (mp.department or '').strip():
                    return Response({'detail': '该维修人员未完善“联系电话/工种”，暂不可派单'}, status=status.HTTP_400_BAD_REQUEST)
                ticket.assignee = worker
                ticket.status = 'pending_repair'
                ticket.save()
                try:
                    sync_ticket_simple(ticket)
                except Exception:
                    pass
                return Response({'status': 'Dispatched'})
            except CustomUser.DoesNotExist:
                return Response({'error': 'Worker not found'}, status=400)

        if action_type == 'start':
            if user.role == 'maintenance' and ticket.assignee != user:
                return Response({'detail': '只能处理指派给自己的工单'}, status=status.HTTP_403_FORBIDDEN)
            if user.role not in ['admin', 'maintenance']:
                return Response({'detail': '无权开始维修'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.status != 'pending_repair':
                return Response({'detail': '当前状态不可开始维修'}, status=status.HTTP_400_BAD_REQUEST)
            if user.role == 'maintenance':
                mp = getattr(user, 'maintenance_profile', None)
                if not mp or not (mp.contact_phone or '').strip() or not (mp.department or '').strip():
                    return Response({'detail': '请先在工作台填写并保存“联系电话/工种”后再开始维修'}, status=status.HTTP_400_BAD_REQUEST)

            ticket.status = 'repairing'
            ticket.response_time = timezone.now()
            ticket.save()
            try:
                sync_ticket_simple(ticket)
            except Exception:
                pass
            return Response({'status': 'Repair Started'})

        # Finish Repair
        if action_type == 'finish':
            # 只有维修工（且是当前工单的处理人）或管理员可以点击完成
            if user.role == 'maintenance' and ticket.assignee != user:
                return Response({'detail': '只能完成指派给自己的工单'}, status=status.HTTP_403_FORBIDDEN)
            
            if user.role not in ['admin', 'maintenance']:
                return Response({'detail': '无权完成工单'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.status != 'repairing':
                return Response({'detail': '仅维修中工单可完成'}, status=status.HTTP_400_BAD_REQUEST)
            if user.role == 'maintenance':
                mp = getattr(user, 'maintenance_profile', None)
                if not mp or not (mp.contact_phone or '').strip() or not (mp.department or '').strip():
                    return Response({'detail': '请先在工作台填写并保存“联系电话/工种”后再完成维修'}, status=status.HTTP_400_BAD_REQUEST)

            ticket.status = 'finished'
            ticket.repair_result = (request.data.get('repair_result') or '').strip() or None
            ticket.materials_used = (request.data.get('materials_used') or '').strip() or None
            ticket.material_cost = 0

            def ensure_repair_sheet(t):
                now2 = timezone.now()
                if not (t.reimbursement_no or '').strip():
                    t.reimbursement_no = f"BX{now2.strftime('%Y%m%d')}-{int(t.id):06d}"
                t.reimbursement_generated_at = now2
                submitter_name2 = getattr(getattr(t, 'submitter', None), 'name', '') or getattr(getattr(t, 'submitter', None), 'username', '') or ''
                submitter_identity2 = (getattr(getattr(t, 'submitter', None), 'identity_id', None) or '').strip()
                worker_name2 = getattr(getattr(t, 'assignee', None), 'name', '') or getattr(getattr(t, 'assignee', None), 'username', '') or ''
                dep2 = ''
                try:
                    dep2 = getattr(getattr(t.assignee, 'maintenance_profile', None), 'department', '') or ''
                except Exception:
                    dep2 = ''
                t.reimbursement_text = (
                    "校园维修报修单\n"
                    f"报修单号：{t.reimbursement_no}\n"
                    f"工单编号：{t.id}\n"
                    f"生成时间：{now2.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    "\n"
                    f"报修标题：{t.title}\n"
                    f"报修类别：{t.category}\n"
                    f"维修地点：{t.location or ''}\n"
                    f"学号：{submitter_identity2}\n"
                    f"学生姓名：{submitter_name2}\n"
                    "\n"
                    f"维修人员：{worker_name2}\n"
                    f"工种：{dep2}\n"
                    "\n"
                    f"维修结果：{t.repair_result or ''}\n"
                    f"耗材明细：{t.materials_used or ''}\n"
                    "\n"
                )
                return t

            ensure_repair_sheet(ticket)
            ticket.save()
            try:
                sync_ticket_simple(ticket)
            except Exception:
                pass
            return Response(
                {
                    'status': 'Repair Finished',
                    'reimbursement_no': ticket.reimbursement_no,
                    'reimbursement_text': ticket.reimbursement_text,
                }
            )

        if action_type == 'sheet':
            allowed = False
            if user.role in ['admin', 'auditor']:
                allowed = True
            elif user.role == 'maintenance' and ticket.assignee == user:
                allowed = True
            elif user.role == 'student' and ticket.submitter == user:
                allowed = True
            if not allowed:
                return Response({'detail': '无权生成报修单'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.status not in ['finished', 'closed']:
                return Response({'detail': '仅已完成/已结单工单可生成报修单'}, status=status.HTTP_400_BAD_REQUEST)

            if not (ticket.reimbursement_text or '').strip():
                now = timezone.now()
                if not (ticket.reimbursement_no or '').strip():
                    ticket.reimbursement_no = f"BX{now.strftime('%Y%m%d')}-{int(ticket.id):06d}"
                ticket.reimbursement_generated_at = now
                submitter_name = getattr(getattr(ticket, 'submitter', None), 'name', '') or getattr(getattr(ticket, 'submitter', None), 'username', '') or ''
                submitter_identity = (getattr(getattr(ticket, 'submitter', None), 'identity_id', None) or '').strip()
                worker_name = getattr(getattr(ticket, 'assignee', None), 'name', '') or getattr(getattr(ticket, 'assignee', None), 'username', '') or ''
                dep = ''
                try:
                    dep = getattr(getattr(ticket.assignee, 'maintenance_profile', None), 'department', '') or ''
                except Exception:
                    dep = ''
                ticket.reimbursement_text = (
                    "校园维修报修单\n"
                    f"报修单号：{ticket.reimbursement_no}\n"
                    f"工单编号：{ticket.id}\n"
                    f"生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    "\n"
                    f"报修标题：{ticket.title}\n"
                    f"报修类别：{ticket.category}\n"
                    f"维修地点：{ticket.location or ''}\n"
                    f"学号：{submitter_identity}\n"
                    f"学生姓名：{submitter_name}\n"
                    "\n"
                    f"维修人员：{worker_name}\n"
                    f"工种：{dep}\n"
                    "\n"
                    f"维修结果：{ticket.repair_result or ''}\n"
                    f"耗材明细：{ticket.materials_used or ''}\n"
                    "\n"
                )
                ticket.save(update_fields=['reimbursement_no', 'reimbursement_text', 'reimbursement_generated_at'])

            return Response(
                {
                    'reimbursement_no': ticket.reimbursement_no,
                    'reimbursement_text': ticket.reimbursement_text,
                }
            )

        # Return to Dispatcher
        if action_type == 'return':
            if user.role == 'maintenance' and ticket.assignee != user:
                return Response({'detail': '只能退回指派给自己的工单'}, status=status.HTTP_403_FORBIDDEN)
            if user.role not in ['admin', 'maintenance']:
                return Response({'detail': '无权退回工单'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.status not in ['pending_repair']:
                return Response({'detail': '仅待维修工单可退回重派'}, status=status.HTTP_400_BAD_REQUEST)
            if user.role == 'maintenance':
                mp = getattr(user, 'maintenance_profile', None)
                if not mp or not (mp.contact_phone or '').strip() or not (mp.department or '').strip():
                    return Response({'detail': '请先在工作台填写并保存“联系电话/工种”后再退回重派'}, status=status.HTTP_400_BAD_REQUEST)
            
            ticket.status = 'pending_dispatch'
            ticket.assignee = None
            ticket.save()
            try:
                sync_ticket_simple(ticket)
            except Exception:
                pass
            return Response({'status': 'Returned'})

        if action_type == 'special':
            return Response({'detail': '特殊工单功能已移除'}, status=status.HTTP_400_BAD_REQUEST)

        # Urge
        if action_type == 'urge':
            if user.role == 'student' and ticket.submitter != user:
                return Response({'detail': '只能催办自己的工单'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.status in ['finished', 'closed', 'rejected']:
                return Response({'detail': '当前状态不可催办'}, status=status.HTTP_400_BAD_REQUEST)
            
            cd_seconds = 12 * 60 * 60
            if ticket.last_urge_at:
                delta = timezone.now() - ticket.last_urge_at
                if delta.total_seconds() < cd_seconds:
                    remain = int(cd_seconds - delta.total_seconds())
                    return Response({'detail': f'催办太频繁，请 {remain} 秒后再试'}, status=429)

            ticket.urge_count += 1
            ticket.last_urge_at = timezone.now()
            ticket.save(update_fields=['urge_count', 'last_urge_at'])
            return Response({'status': 'Urged'})

        if action_type == 'evaluate':
            if user.role != 'student':
                return Response({'detail': '无权评价工单'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.submitter != user:
                return Response({'detail': '只能评价自己提交的工单'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.status != 'finished':
                return Response({'detail': '当前状态不可评价'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                rating = int(request.data.get('rating') or 5)
            except Exception:
                return Response({'detail': '评分格式错误'}, status=status.HTTP_400_BAD_REQUEST)
            if rating < 0 or rating > 5:
                return Response({'detail': '评分需为 0-5'}, status=status.HTTP_400_BAD_REQUEST)

            evaluation = (request.data.get('evaluation') or '').strip()
            is_anonymous = bool(request.data.get('is_anonymous') or False)
            ticket.rating = rating
            ticket.evaluation = evaluation
            ticket.is_anonymous = is_anonymous
            ticket.status = 'closed'
            ticket.save()
            try:
                sync_ticket_simple(ticket)
            except Exception:
                pass
            return Response({'status': 'Closed'})

        return Response({'error': 'Unknown action'}, status=400)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        ticket = self.get_object()
        user = request.user
        if user.role not in ['admin', 'auditor']:
            return Response({'detail': '无权限执行审核操作'}, status=status.HTTP_403_FORBIDDEN)
        if user.role == 'auditor':
            ap = getattr(user, 'auditor_profile', None)
            if not (getattr(ap, 'contact_phone', '') or '').strip():
                return Response({'detail': '请先在工作台填写并保存审核员联系电话后再审核'}, status=status.HTTP_400_BAD_REQUEST)

        decision = request.data.get('decision')
        if ticket.status not in ['pending_dorm', 'pending_dispatch']:
            return Response({'detail': '当前状态不可审核/驳回'}, status=status.HTTP_400_BAD_REQUEST)
        if ticket.assignee_id:
            return Response({'detail': '已派单的工单不可驳回，如需处理请走退回/撤销流程'}, status=status.HTTP_400_BAD_REQUEST)
        if decision == 'approve':
            ticket.status = 'pending_dispatch'
            ticket.rejected_reason = None
            ticket.auditor = user  # 记录审核员
            ticket.save()
            try:
                sync_ticket_simple(ticket)
            except Exception:
                pass
            return Response({'status': 'Approved'})
        if decision == 'reject':
            ticket.status = 'rejected'
            ticket.rejected_reason = (request.data.get('reason') or '').strip() or None
            ticket.auditor = user  # 记录审核员
            ticket.save()
            try:
                sync_ticket_simple(ticket)
            except Exception:
                pass
            return Response({'status': 'Rejected'})

        return Response({'detail': '未知操作'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'], url_path='attachments', parser_classes=[MultiPartParser, FormParser])
    def attachments(self, request, pk=None):
        import os
        import imghdr

        ticket = self.get_object()
        user = request.user

        if request.method == 'GET':
            serializer = TicketSerializer(ticket, context={'request': request})
            return Response(serializer.data.get('attachments', []))
        
        # 多文件上传走 multipart/form-data
        # 在 DRF 中 parser 由 ViewSet 的 parser_classes 决定；这里按需懒加载处理

        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': '缺少文件 file'}, status=status.HTTP_400_BAD_REQUEST)

        if user.role == 'student' and ticket.submitter != user:
            return Response({'detail': '无权上传附件'}, status=status.HTTP_403_FORBIDDEN)
        if user.role == 'maintenance':
            if ticket.assignee != user:
                return Response({'detail': '无权上传附件'}, status=status.HTTP_403_FORBIDDEN)
            if ticket.status not in ['repairing', 'finished']:
                return Response({'detail': '当前状态不可上传附件'}, status=status.HTTP_400_BAD_REQUEST)
        elif user.role not in ['student', 'admin', 'auditor']:
            return Response({'detail': '无权上传附件'}, status=status.HTTP_403_FORBIDDEN)
        if user.role == 'student' and ticket.status not in ['pending_dorm', 'rejected']:
            return Response({'detail': '当前状态不可上传附件'}, status=status.HTTP_400_BAD_REQUEST)
        if ticket.attachments.count() >= 6:
            return Response({'detail': '附件数量已达上限'}, status=status.HTTP_400_BAD_REQUEST)

        max_image = 5 * 1024 * 1024
        max_video = 50 * 1024 * 1024
        name = upload.name or ''
        ext = os.path.splitext(name)[1].lower()
        ct = (getattr(upload, 'content_type', '') or '').lower()

        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        video_exts = {'.mp4', '.webm', '.ogg', '.mov'}
        image_cts = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        video_cts = {'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'}

        is_image = ext in image_exts and ct in image_cts
        is_video = ext in video_exts and (ct in video_cts or ct.startswith('video/'))

        if not (is_image or is_video):
            return Response({'detail': '仅支持图片(jpg/jpeg/png/gif/webp)与视频(mp4/webm/ogg/mov)'}, status=status.HTTP_400_BAD_REQUEST)

        if is_image and upload.size > max_image:
            return Response({'detail': '图片大小不能超过 5MB'}, status=status.HTTP_400_BAD_REQUEST)
        if is_video and upload.size > max_video:
            return Response({'detail': '视频大小不能超过 50MB'}, status=status.HTTP_400_BAD_REQUEST)

        if is_image:
            head = upload.read(2048)
            upload.seek(0)
            kind = imghdr.what(None, h=head)
            if kind not in {'jpeg', 'png', 'gif', 'webp'}:
                return Response({'detail': '图片内容校验失败'}, status=status.HTTP_400_BAD_REQUEST)

        media_type = 'image' if is_image else 'video'
        att = TicketAttachment.objects.create(
            ticket=ticket,
            media_type=media_type,
            file=upload,
            original_name=name
        )
        url = att.file.url if att.file else ''
        if url and not url.startswith('http'):
            url = request.build_absolute_uri(url)
        return Response({'id': att.id, 'media_type': att.media_type, 'url': url, 'original_name': att.original_name}, status=201)


class ServiceStarViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceStar.objects.filter(is_active=True).order_by('sort_order', '-id')
    serializer_class = ServiceStarSerializer
    permission_classes = [AllowAny]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_chat(request):
    user = request.user
    if user.role != 'student':
        return Response({"detail": "AI 助手仅面向学生开放"}, status=status.HTTP_403_FORBIDDEN)

    content = (request.data.get('message') or request.data.get('content') or '').strip()
    if not content:
        return Response({"detail": "问题内容不能为空"}, status=status.HTTP_400_BAD_REQUEST)

    def _mask_pii(text: str) -> str:
        text = re.sub(r'\b1\d{10}\b', '[已脱敏手机号]', text)
        text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[已脱敏邮箱]', text)
        text = re.sub(r'\b\d{6,}\b', '[已脱敏数字]', text)
        text = re.sub(r'[A-Za-z0-9_\-]{24,}', '[已脱敏标识]', text)
        return text

    api_key = os.environ.get('AI_API_KEY') or os.environ.get('OPENAI_API_KEY')
    base_url = (os.environ.get('AI_BASE_URL') or 'https://api.siliconflow.cn/v1').rstrip('/')
    model = os.environ.get('AI_MODEL') or 'deepseek-ai/DeepSeek-V3'
    model_deep = os.environ.get('AI_MODEL_DEEP') or ''
    llm_enabled = str(os.environ.get('AI_LLM_ENABLED') or '').strip().lower() in {'1', 'true', 'yes', 'on'}
    try:
        timeout = float(os.environ.get('AI_TIMEOUT') or 20)
    except Exception:
        timeout = 20.0

    s = AiSetting.objects.order_by('-updated_at', '-id').first()
    if s:
        if not s.enabled:
            return Response({"detail": "AI 助手已在后台关闭"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        llm_enabled = bool(getattr(s, 'llm_enabled', False))
        if (s.api_base_url or '').strip():
            base_url = s.api_base_url.strip().rstrip('/')
        if (s.api_model or '').strip():
            model = s.api_model.strip()
        if (getattr(s, 'api_model_deep', '') or '').strip():
            model_deep = getattr(s, 'api_model_deep', '').strip()
        if (s.api_key or '').strip():
            api_key = s.api_key.strip()
        if getattr(s, 'timeout_seconds', None):
            try:
                timeout = float(s.timeout_seconds)
            except Exception:
                pass

    normalized = content.lower()
    category = "其他"
    if any(k in normalized for k in ["wifi", "wi-fi", "网络", "上网", "断网", "路由", "宽带"]):
        category = "网络连接"
    elif any(k in normalized for k in ["水", "漏水", "水龙头", "下水", "电", "灯", "跳闸", "插座", "电闸", "开关"]):
        category = "水电问题"
    elif any(k in normalized for k in ["空调", "冰箱", "洗衣机", "热水器", "风扇", "设备", "电器"]):
        category = "设备故障"
    elif any(k in normalized for k in ["柜", "衣柜", "桌", "椅", "床"]):
        category = "柜子损坏"
    elif any(k in normalized for k in ["门", "窗", "锁", "玻璃"]):
        category = "门窗损坏"

    name = user.name or user.username
    base = (
        f"您好，{name}。\n"
        f"我理解你遇到的问题是：{content}\n\n"
        "如果你希望一键填写报修单：先把地点/现象/是否紧急等信息告诉我，然后点击聊天回复气泡下方的“ 一键帮我填报修单 ”按钮自动填表。\n\n"
        f"建议（参考）：\n"
    )

    steps = []
    questions = []

    if category == "水电问题":
        steps = [
            "1）如有异味/冒烟/漏电/插座或电器发热/频繁跳闸：请立即停止使用，远离危险区域，不要触碰裸露线路或电器内部。",
            "2）不要自行拆插座、开电箱、测电或接线；这些属于高风险操作。",
            "3）请在平台【提交报修】选择“水电问题”，尽量描述现象（例如：哪盏灯、哪个插座、是否全宿舍断电），并上传现场照片。",
            "4）如果是漏水：尽量关闭可见阀门/水源（在确保安全前提下），并在平台备注“是否持续渗漏、是否影响邻室”。",
        ]
        questions = [
            "是否只影响你宿舍，还是同楼层/整层也有类似情况？",
            "是否出现跳闸、异味、火花、发热等明显危险信号？",
            "发生位置在哪里（楼栋-房间-具体点位）？",
        ]
    elif category == "网络连接":
        steps = [
            "1）先判断范围：是仅你设备不能上网，还是同宿舍同学也都不行。",
            "2）可尝试非破坏性操作：重新连接 Wi-Fi、关闭再打开飞行模式、重启设备网络。",
            "3）请在平台【提交报修】选择“网络连接”，补充错误提示/截图、发生时间段、影响范围。",
        ]
        questions = [
            "是连不上 Wi‑Fi，还是能连上但无法上网？",
            "手机/电脑是否都一样，还是某一台设备的问题？",
            "是否有错误提示截图（例如认证失败、无法获取IP等）？",
        ]
    elif category == "设备故障":
        steps = [
            "1）请不要自行拆机、拆插头或对电器内部进行任何检修。",
            "2）若设备显示错误代码/报警灯，请拍照记录；如果有异味/冒烟/异常发热，请立即停止使用。",
            "3）请在平台【提交报修】选择“设备故障”，填写设备名称、故障现象、出现时间与影响程度。",
        ]
        questions = [
            "设备是什么（空调/洗衣机/热水器等），型号或张贴编号有吗？",
            "故障是间歇还是持续，是否可复现？",
            "是否出现异味、冒烟、漏水、异常声音？",
        ]
    elif category == "门窗损坏":
        steps = [
            "1）请不要强行撬/砸/硬拧，以免造成二次损坏或夹伤。",
            "2）如涉及安全（门锁失效、玻璃破裂等），请保持现场安全并避免接触锋利边缘。",
            "3）请在平台【提交报修】选择“门窗损坏”，拍照并说明损坏位置与是否影响出入/通风/安全。",
        ]
        questions = [
            "是门锁问题还是门窗框/合页/玻璃问题？",
            "是否影响正常出入或存在割伤风险？",
        ]
    elif category == "柜子损坏":
        steps = [
            "1）不要强行拉拽/继续使用卡住的抽屉或柜门，以免夹伤或扩大损坏。",
            "2）请在平台【提交报修】选择“柜子损坏”，拍照并描述损坏部位（铰链/滑轨/门板等）。",
        ]
        questions = [
            "是柜门关不上、抽屉卡住，还是结构松动/断裂？",
            "是否影响正常使用或存在夹手风险？",
        ]
    else:
        steps = [
            f"1）你可以在平台【提交报修】选择最接近的类别（建议：{category}），填写地点、联系方式与现象描述。",
            "2）不要自行进行拆装、带电检修或任何高风险操作。",
            "3）建议附上照片/视频与发生时间，便于快速定位。",
        ]
        questions = [
            "问题具体发生在什么位置（楼栋-房间-点位）？",
            "是否影响安全或正常生活（例如漏水、跳闸、异味等）？",
        ]

    answer = base + "\n".join(steps)
    if questions:
        answer += "\n\n为了更准确一些，你可以补充：\n" + "\n".join([f"- {q}" for q in questions])
    answer += f"\n\n建议报修类别：{category}"

    warning = "重要提示：AI 回答可能有误，仅供参考，以实际为准，不能盲目操作。"
    
    # 默认返回数据（fallback 模式）
    res_data = {
        "answer": answer,
        "warning": warning,
        "mode": "fallback",
        "ai_enabled": bool(api_key),
        "thinking": bool(llm_enabled),
        "has_key": bool(api_key),
    }

    if api_key:
        if not base_url.startswith('https://'):
            # 如果配置不安全，直接走 fallback
            pass
        else:
            outbound_content = _mask_pii(content)
            use_model = (model_deep or model) if llm_enabled else model
            system_prompt = (
                "你是校园报修AI助手。请用中文回答，回答要保守、谨慎、以安全为先。"
                "你只能提供报修流程、信息收集建议与风险提示，不能提供任何带电检修、拆装、测电等操作指导。"
                "你必须引导用户使用“本平台”完成报修，不得建议去任何其他APP/公众号/小程序/电话渠道报修，也不要出现“本系统暂不支持”之类的贬低语气。"
                "当用户表达“想一键报修/一键填写”时，请明确告知：先与AI对话补充信息，然后点击聊天回复气泡下方的“ 一键帮我填报修单 ”按钮自动填表，再在提交页面补全联系方式后提交。"
                "遇到宿舍水电、安全风险、冒烟、漏电、跳闸等情况，必须提醒用户停止操作并通过本平台提交报修等待处理。"
                "不要编造事实或承诺。回答末尾不要重复免责声明，免责声明由前端单独展示。"
            )
            payload = {
                "model": use_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": outbound_content},
                ],
                "temperature": 0.2,
            }
            logger = logging.getLogger(__name__)
            try:
                req = Request(
                    f"{base_url}/chat/completions",
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                msg = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
                if msg:
                    res_data = {"answer": msg, "warning": warning, "mode": "llm", "ai_enabled": True, "thinking": bool(llm_enabled), "has_key": True}
            except HTTPError as e:
                logger.warning("ai_chat_http_error", exc_info=True)
                res_data["upstream_status"] = getattr(e, "code", None)
            except URLError:
                logger.warning("ai_chat_url_error", exc_info=True)
            except Exception:
                logger.warning("ai_chat_error", exc_info=True)

    # 在返回之前，先在后台留个痕迹（保存日志）
    try:
        AiChatLog.objects.create(
            user=user,
            question=content,
            answer=res_data.get("answer", ""),
            mode=res_data.get("mode", ""),
            ai_enabled=res_data.get("ai_enabled", True),
            warning=res_data.get("warning", "")
        )
    except Exception as log_err:
        logging.getLogger(__name__).error(f"Failed to save AiChatLog: {log_err}")

    return Response(res_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_generate_ticket(request):
    user = request.user
    if user.role != 'student':
        return Response({"detail": "仅学生可用此功能"}, status=status.HTTP_403_FORBIDDEN)

    chat_history = request.data.get('chat_history', [])
    if not chat_history:
        return Response({"detail": "聊天记录为空"}, status=status.HTTP_400_BAD_REQUEST)

    user_last = ""
    user_messages = []
    for msg in chat_history:
        if msg.get('role') == 'user':
            c = (msg.get('content') or '').strip()
            if c:
                user_messages.append(c)
    for msg in reversed(chat_history):
        if msg.get('role') == 'user':
            user_last = (msg.get('content') or '').strip()
            break

    user_context = "\n".join(user_messages[-6:])
    text = (user_last or user_context or '').strip()

    category = "其他"
    if any(k in user_context.lower() for k in ["wifi", "wi-fi", "网络", "上网", "断网", "路由", "宽带"]):
        category = "网络连接"
    elif any(k in user_context for k in ["跳闸", "断电", "停电", "插座", "电闸", "开关", "漏电", "灯不亮", "灯坏", "电"]):
        category = "水电问题"
    elif any(k in user_context for k in ["空调", "冰箱", "洗衣机", "热水器", "风扇", "设备", "电器"]):
        category = "设备故障"
    elif any(k in user_context for k in ["柜", "衣柜", "桌", "椅", "床", "抽屉", "滑轨", "铰链"]):
        category = "柜子损坏"
    elif any(k in user_context for k in ["门", "窗", "锁", "玻璃", "合页"]):
        category = "门窗损坏"

    def pick_title(question: str, cat: str) -> str:
        q = (question or '').strip()
        normalized = q.replace('？', '?').replace('，', ',').replace('。', '.')
        compact = re.sub(r'\s+', ' ', normalized).strip()

        if '空调' in compact and any(k in compact for k in ['不制冷', '不冷', '不凉', '不制热', '不热', '不暖']):
            return '空调不制冷/制热'
        if '空调' in compact and any(k in compact for k in ['漏水', '滴水', '渗水']):
            return '空调漏水'
        if any(k in compact for k in ['跳闸', '断电', '停电']):
            return '跳闸/断电'
        if any(k in compact for k in ['下水', '堵塞', '堵', '反味']):
            return '下水堵塞'
        if any(k in compact for k in ['灯不亮', '灯坏', '灯泡']):
            return '灯不亮'
        if any(k in compact for k in ['插座', '开关']):
            return '插座/开关故障'
        if any(k in compact.lower() for k in ['断网', '没网', '连不上', 'wifi', 'wi-fi', '网络']):
            return '网络故障'
        if any(k in compact for k in ['漏水', '滴水', '渗水']):
            return '漏水'
        if any(k in compact for k in ['门', '锁']):
            return '门锁故障'
        if any(k in compact for k in ['窗', '玻璃']):
            return '窗户/玻璃损坏'
        if any(k in compact for k in ['柜', '抽屉', '滑轨', '铰链']):
            return '柜子损坏'

        cleaned = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9]+', ' ', compact).strip()
        if cleaned:
            words = cleaned.split()
            clipped = ''.join(words)[:18]
            if clipped:
                return clipped
        return cat or '报修'

    title = pick_title(text, category)
    desc = text

    return Response({
        "title": title,
        "category": category,
        "description": desc or "",
        "priority": "中"
    })

# def change_status(request, order_id):
#     order = get_object_or_404(Order, id=order_id)
#
#     # 简单的状态流转逻辑
#     if order.status == 0:  # 待接单 -> 维修中
#         order.status = 1
#     elif order.status == 1:  # 维修中 -> 已完成
#         order.status = 2
#
#     order.save()
#
#     # 关键修改：返回 JSON 给 Vue，告诉它最新的状态是多少
#     return JsonResponse({
#         'code': 200,
#         'msg': '状态更新成功',
#         'new_status': order.status
#     })
