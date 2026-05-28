"""
自定义命令：sync_simple

用途：
- 将主库（BiShe）现有数据批量同步到简化库（BiShe_simple）
- 主要用于论文撰写、数据展示、ER 图/样例数据导出等场景

用法：
- python manage.py sync_simple
"""

from django.core.management.base import BaseCommand
from tickets_api.models import CustomUser, Ticket, ServiceStar
from tickets_api.simple_sync import sync_user, sync_ticket, sync_service_star


class Command(BaseCommand):
    """命令实现：遍历所有用户/服务之星/工单并写入简化库。"""
    help = "把当前 Django 数据同步写入 BiShe_simple（论文用简化库）"

    def handle(self, *args, **options):
        """命令入口。"""
        for u in CustomUser.objects.all().iterator():
            sync_user(u)
        for s in ServiceStar.objects.all().iterator():
            sync_service_star(s)
        for t in Ticket.objects.all().iterator():
            sync_ticket(t)
        self.stdout.write(self.style.SUCCESS("sync_simple 完成"))
