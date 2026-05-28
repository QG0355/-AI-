"""
简化库同步模块（BiShe_simple）。

背景：
- 项目主库：BiShe（Django ORM 正常使用）
- 简化库：BiShe_simple（用于论文/数据展示/ER 图等场景，结构更“教学化”）

本模块职责：
- 将主库中的用户/工单/服务之星同步写入简化库
- 使用原生 SQL + ON DUPLICATE KEY UPDATE，避免复杂的跨库 ORM 逻辑
"""

from django.db import connections
from django.utils import timezone


def _get_cursor():
    """获取简化库（DATABASES['simple']）的 cursor；如未配置则返回 None。"""
    if 'simple' not in connections.databases:
        return None
    try:
        return connections['simple'].cursor()
    except Exception:
        return None


def sync_user(user):
    """
    同步单个用户到简化库。

    同步策略：
    - 以 identity_id（学号/工号）作为简化库主键
    - 按 role 分表写入（student_user / maintenance_user / auditor_user / admin_user）
    """
    identity_id = (getattr(user, 'identity_id', None) or '').strip()
    if not identity_id:
        return

    role = getattr(user, 'role', None)
    name = getattr(user, 'name', '') or getattr(user, 'username', '') or ''
    gender = getattr(user, 'gender', 'unknown') or 'unknown'
    pwd = getattr(user, 'password', '') or ''

    cursor = _get_cursor()
    if cursor is None:
        return

    if role == 'student':
        cursor.execute(
            """
            INSERT INTO student_user (student_id, name, password, gender, submit_ticket_count)
            VALUES (%s, %s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE name=VALUES(name), password=VALUES(password), gender=VALUES(gender)
            """,
            [identity_id, name, pwd, gender],
        )
        return

    if role == 'maintenance':
        cursor.execute(
            """
            INSERT INTO maintenance_user (worker_id, name, password, gender, rating, finished_ticket_count)
            VALUES (%s, %s, %s, %s, 5.00, 0)
            ON DUPLICATE KEY UPDATE name=VALUES(name), password=VALUES(password), gender=VALUES(gender)
            """,
            [identity_id, name, pwd, gender],
        )
        return

    if role == 'auditor':
        cursor.execute(
            """
            INSERT INTO auditor_user (auditor_id, name, password, gender, audit_ticket_count)
            VALUES (%s, %s, %s, %s, 0)
            ON DUPLICATE KEY UPDATE name=VALUES(name), password=VALUES(password), gender=VALUES(gender)
            """,
            [identity_id, name, pwd, gender],
        )
        return

    if role == 'admin':
        cursor.execute(
            """
            INSERT INTO admin_user (admin_id, name, password, gender, permission_level)
            VALUES (%s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE name=VALUES(name), password=VALUES(password), gender=VALUES(gender)
            """,
            [identity_id, name, pwd, gender],
        )


def sync_ticket(ticket):
    """
    同步单个工单到简化库 repair_ticket 表。

    注意：
    - 会先确保 submitter/assignee/auditor 对应的用户已同步
    - 使用 ON DUPLICATE KEY UPDATE 保证重复同步不会报错
    """
    cursor = _get_cursor()
    if cursor is None:
        return

    submitter = getattr(ticket, 'submitter', None)
    assignee = getattr(ticket, 'assignee', None)
    auditor = getattr(ticket, 'auditor', None)

    if submitter:
        sync_user(submitter)
    if assignee:
        sync_user(assignee)
    if auditor:
        sync_user(auditor)

    student_id = (getattr(submitter, 'identity_id', None) or '').strip()
    if not student_id:
        student_id = (getattr(submitter, 'username', None) or '').strip()

    worker_id = (getattr(assignee, 'identity_id', None) or '').strip() if assignee else None
    auditor_id = (getattr(auditor, 'identity_id', None) or '').strip() if auditor else None

    submit_time = getattr(ticket, 'submitTime', None) or timezone.now()
    update_time = getattr(ticket, 'updateTime', None) or timezone.now()

    cursor.execute(
        """
        INSERT INTO repair_ticket (
            ticket_id, title, category, priority, status, description, location, contact,
            submit_time, update_time, student_id, worker_id, auditor_id, evaluation, rating, is_anonymous, rejected_reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title=VALUES(title),
            category=VALUES(category),
            priority=VALUES(priority),
            status=VALUES(status),
            description=VALUES(description),
            location=VALUES(location),
            contact=VALUES(contact),
            submit_time=VALUES(submit_time),
            update_time=VALUES(update_time),
            student_id=VALUES(student_id),
            worker_id=VALUES(worker_id),
            auditor_id=VALUES(auditor_id),
            evaluation=VALUES(evaluation),
            rating=VALUES(rating),
            is_anonymous=VALUES(is_anonymous),
            rejected_reason=VALUES(rejected_reason)
        """,
        [
            int(getattr(ticket, 'id')),
            getattr(ticket, 'title', ''),
            getattr(ticket, 'category', ''),
            getattr(ticket, 'priority', ''),
            getattr(ticket, 'status', ''),
            getattr(ticket, 'description', None),
            getattr(ticket, 'location', None),
            getattr(ticket, 'contact', None),
            submit_time,
            update_time,
            student_id,
            worker_id,
            auditor_id,
            getattr(ticket, 'evaluation', None),
            int(getattr(ticket, 'rating', 5) or 5),
            1 if bool(getattr(ticket, 'is_anonymous', False)) else 0,
            getattr(ticket, 'rejected_reason', None),
        ],
    )


def sync_service_star(star):
    """同步服务之星到简化库 service_star 表（用于首页展示/论文图表）。"""
    cursor = _get_cursor()
    if cursor is None:
        return

    cursor.execute(
        """
        INSERT INTO service_star (star_id, name, honor, description, score, score_count, sort_order, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name=VALUES(name),
            honor=VALUES(honor),
            description=VALUES(description),
            score=VALUES(score),
            score_count=VALUES(score_count),
            sort_order=VALUES(sort_order),
            is_active=VALUES(is_active)
        """,
        [
            int(getattr(star, 'id')),
            getattr(star, 'name', ''),
            getattr(star, 'honor', None),
            getattr(star, 'description', None),
            float(getattr(star, 'score', 5.00) or 5.00),
            int(getattr(star, 'score_count', 0) or 0),
            int(getattr(star, 'sort_order', 0) or 0),
            1 if bool(getattr(star, 'is_active', True)) else 0,
        ],
    )
