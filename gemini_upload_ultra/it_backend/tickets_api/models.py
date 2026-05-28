"""
数据模型定义（Django ORM Models）。

本文件描述系统核心数据结构：
- CustomUser：扩展 Django 用户，增加角色、学号/工号、手机号、头像等字段
- Ticket：报修工单全流程数据（提交/审核/派单/维修/评价/AI 过审标记）
- TicketAttachment：工单附件（图片/视频）
- AiSetting / AiChatLog：AI 配置与聊天记录（用于后台可视化与审计）
- StudentProfile / MaintenanceProfile / AuditorProfile / AdminProfile：按角色拆分的扩展信息
"""

from django.db import models
from django.contrib.auth.models import AbstractUser


def _user_avatar_upload_to(instance, filename):
    import os
    import uuid
    ext = os.path.splitext(filename)[1].lower()
    return f"avatars/{instance.pk}/{uuid.uuid4().hex}{ext}"


class CustomUser(AbstractUser):
    """
    自定义用户模型。

    设计要点：
    - role：决定用户身份（学生/维修/审核/管理员），影响前端跳转与后端权限
    - identity_id：学号/工号，绑定后用于业务侧唯一识别
    - phone：手机号（用于找回密码；管理员账号不走该流程）
    - avatar/avatar_url：头像展示（支持上传文件或外链）
    """
    IDENTITY_CHOICES = (
        ('student', '学生'),
        ('maintenance', '维修人员'),
        ('auditor', '审核员'),
        ('admin', '超级管理员'),
    )

    GENDER_CHOICES = (
        ('unknown', '未知'),
        ('male', '男'),
        ('female', '女'),
    )

    name = models.CharField(max_length=100, blank=True, verbose_name="真实姓名")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='unknown', verbose_name="性别")
    avatar_url = models.URLField(blank=True, default='', verbose_name="头像地址")
    avatar = models.FileField(upload_to=_user_avatar_upload_to, blank=True, null=True, verbose_name="头像文件")
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name="手机号")
    role = models.CharField(max_length=20, choices=IDENTITY_CHOICES, default='student', verbose_name="身份角色")
    identity_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="身份ID")
    is_identity_bound = models.BooleanField(default=False, verbose_name="是否已绑定")

    class Meta:
        verbose_name = "用户信息"
        verbose_name_plural = "用户信息"

    def __str__(self):
        return self.username

    @property
    def avatar_display(self):
        if self.avatar:
            try:
                return self.avatar.url
            except Exception:
                return ''
        return self.avatar_url or ''


class Ticket(models.Model):
    """
    报修工单模型（系统核心业务对象）。

    关键字段：
    - status：工单状态机（pending_dorm -> pending_dispatch -> pending_repair -> repairing -> finished -> closed / rejected）
    - submitter/assignee/auditor：工单的提交人/维修人/审核人
    - ai_auto_approved/ai_auto_checked_at/...：AI 自动审核产物（用于“AI 过审标记 + 人工兜底”）
    """
    CATEGORY_CHOICES = [
        ('设备故障', '设备故障'),
        ('水电问题', '水电问题'),
        ('网络连接', '网络连接'),
        ('柜子损坏', '柜子损坏'),
        ('门窗损坏', '门窗损坏'),
        ('其他', '其他')
    ]

    PRIORITY_CHOICES = [('低', '低'), ('中', '中'), ('高', '高'), ('紧急', '紧急')]

    STATUS_CHOICES = [
        ('pending_dorm', '待审核员审核'),
        ('pending_dispatch', '待派单'),
        ('pending_repair', '待维修'),
        ('repairing', '维修中'),
        ('finished', '维修完成(待评价)'),
        ('closed', '已结单'),
        ('rejected', '已驳回')
    ]

    title = models.CharField(max_length=200, verbose_name="报修标题")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name="报修类别")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, verbose_name="优先级")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_dorm', verbose_name="报修状态")
    description = models.TextField(blank=True, null=True, verbose_name="故障描述")

    location = models.CharField(max_length=200, blank=True, null=True, verbose_name="维修地点")
    contact = models.CharField(max_length=100, blank=True, null=True, verbose_name="联系电话")

    submitter = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='submitted_tickets',
        verbose_name="提交人",
    )
    assignee = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name="维修人员",
    )
    auditor = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audited_tickets',
        verbose_name="审核员",
    )

    evaluation = models.TextField(blank=True, null=True, verbose_name="学生评价")
    rating = models.IntegerField(default=5, verbose_name="评分(1-5)")
    is_anonymous = models.BooleanField(default=False, verbose_name="是否匿名评价")
    rejected_reason = models.TextField(blank=True, null=True, verbose_name="驳回理由")
    response_time = models.DateTimeField(blank=True, null=True, verbose_name="响应时间")
    repair_result = models.TextField(blank=True, null=True, verbose_name="维修结果")
    materials_used = models.TextField(blank=True, null=True, verbose_name="耗材使用")
    material_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="耗材费用")
    urge_count = models.IntegerField(default=0, verbose_name="催单次数")
    last_urge_at = models.DateTimeField(blank=True, null=True, verbose_name="上次催单时间")
    expected_finish_days = models.PositiveIntegerField(default=0, verbose_name="特殊处理预计天数")
    special_reason = models.TextField(blank=True, default='', verbose_name="特殊处理说明")
    ai_auto_approved = models.BooleanField(default=False, verbose_name="AI自动过审")
    ai_auto_checked_at = models.DateTimeField(blank=True, null=True, verbose_name="AI过审时间")
    ai_suggested_category = models.CharField(max_length=50, blank=True, default='', verbose_name="AI建议类别")
    ai_auto_reason = models.TextField(blank=True, default='', verbose_name="AI过审说明")

    reimbursement_no = models.CharField(max_length=32, blank=True, default='', verbose_name="报销单号")
    reimbursement_text = models.TextField(blank=True, default='', verbose_name="报销单内容")
    reimbursement_generated_at = models.DateTimeField(blank=True, null=True, verbose_name="报销单生成时间")

    submitTime = models.DateTimeField(auto_now_add=True, verbose_name="提交时间")
    updateTime = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "报修订单"
        verbose_name_plural = "报修订单"

    def __str__(self):
        return self.title


class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments', verbose_name="所属订单")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="评论用户")
    content = models.TextField(verbose_name="评论内容")
    time = models.DateTimeField(auto_now_add=True, verbose_name="评论时间")

    class Meta:
        verbose_name = "订单评论"
        verbose_name_plural = "订单评论"


# class Order(models.Model):
#
#     STATUS_CHOICES = (
#         (0, '待接单'),  # 刚提交也是这个状态
#         (1, '维修中'),  # 维修人员点击“接单”后
#         (2, '已完成'),  # 修好后
#     )
#
#     status = models.IntegerField(verbose_name="当前状态", choices=STATUS_CHOICES, default=0)


class ServiceStar(models.Model):
    name = models.CharField(max_length=50, verbose_name="维修人员姓名")
    honor = models.CharField(max_length=200, blank=True, verbose_name="荣誉称号")
    description = models.TextField(blank=True, verbose_name="服务事迹")
    score = models.DecimalField(max_digits=3, decimal_places=2, default=5.00, verbose_name="服务评分")
    score_count = models.IntegerField(default=0, verbose_name="评价人数")
    worker = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_star_records',
        verbose_name="关联维修人员",
    )
    avatar_url = models.URLField(blank=True, verbose_name="头像地址")
    sort_order = models.IntegerField(default=0, verbose_name="排序值")
    is_active = models.BooleanField(default=True, verbose_name="是否展示")

    class Meta:
        verbose_name = "服务之星"
        verbose_name_plural = "服务之星"

    def __str__(self):
        return self.name


def _ticket_media_upload_to(instance, filename):
    import os
    import uuid
    ext = os.path.splitext(filename)[1].lower()
    return f"tickets/{instance.ticket_id}/{uuid.uuid4().hex}{ext}"


class TicketAttachment(models.Model):
    MEDIA_CHOICES = (
        ('image', '图片'),
        ('video', '视频'),
    )

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments', verbose_name="所属订单")
    media_type = models.CharField(max_length=10, choices=MEDIA_CHOICES, verbose_name="媒体类型")
    file = models.FileField(upload_to=_ticket_media_upload_to, verbose_name="文件内容")
    original_name = models.CharField(max_length=255, blank=True, default='', verbose_name="原始文件名")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        verbose_name = "订单附件"
        verbose_name_plural = "订单附件"

    def __str__(self):
        return f"{self.ticket_id}-{self.media_type}"


class AiSetting(models.Model):
    enabled = models.BooleanField(default=True, verbose_name="启用 AI 助手")
    llm_enabled = models.BooleanField(default=False, verbose_name="深度思考")
    api_base_url = models.CharField(max_length=255, blank=True, default='https://api.deepseek.com/v1', verbose_name="API Base URL")
    api_model = models.CharField(max_length=100, blank=True, default='deepseek-chat', verbose_name="模型")
    api_model_deep = models.CharField(max_length=100, blank=True, default='', verbose_name="深度思考模型")
    api_key = models.CharField(max_length=255, blank=True, default='', verbose_name="API Key")
    timeout_seconds = models.IntegerField(default=30, verbose_name="超时(秒)")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "AI 配置"
        verbose_name_plural = "AI 配置"


class AiChatLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='ai_chat_logs', verbose_name="用户")
    question = models.TextField(verbose_name="用户问题")
    answer = models.TextField(blank=True, default='', verbose_name="AI 回答")
    mode = models.CharField(max_length=20, blank=True, default='', verbose_name="模式")
    ai_enabled = models.BooleanField(default=True, verbose_name="AI 开关状态")
    warning = models.TextField(blank=True, default='', verbose_name="提示")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="时间")

    class Meta:
        verbose_name = "AI 聊天记录"
        verbose_name_plural = "AI 聊天记录"
        ordering = ['-created_at']


class StudentProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='student_profile', verbose_name="关联用户")
    student_id = models.CharField(max_length=50, unique=True, verbose_name="学号")
    submitted_count = models.IntegerField(default=0, verbose_name="提交报修单数")

    class Meta:
        verbose_name = "学生详情"
        verbose_name_plural = "学生详情"

    def __str__(self):
        return self.student_id


class MaintenanceProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='maintenance_profile', verbose_name="关联用户")
    worker_id = models.CharField(max_length=50, unique=True, verbose_name="维修人员工号")
    finished_count = models.IntegerField(default=0, verbose_name="完成维修订单数")
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00, verbose_name="评分")
    department = models.CharField(max_length=100, blank=True, default='', verbose_name="所属部门/工种")
    contact_phone = models.CharField(max_length=20, blank=True, default='', verbose_name="联系电话")

    class Meta:
        verbose_name = "维修员详情"
        verbose_name_plural = "维修员详情"

    def __str__(self):
        return self.worker_id


class AuditorProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='auditor_profile', verbose_name="关联用户")
    auditor_id = models.CharField(max_length=50, unique=True, verbose_name="审核员工号")
    audited_count = models.IntegerField(default=0, verbose_name="审核保修单数")
    contact_phone = models.CharField(max_length=20, blank=True, default='', verbose_name="联系电话")

    class Meta:
        verbose_name = "审核员详情"
        verbose_name_plural = "审核员详情"

    def __str__(self):
        return self.auditor_id


class AdminProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile', verbose_name="关联用户")
    admin_id = models.CharField(max_length=50, unique=True, verbose_name="管理员编号")
    permission_level = models.IntegerField(default=1, verbose_name="权限级别")

    class Meta:
        verbose_name = "管理员详情"
        verbose_name_plural = "管理员详情"

    def __str__(self):
        return self.admin_id
