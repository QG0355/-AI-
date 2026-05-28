"""
tickets_api 应用配置（AppConfig）。

职责：
- 定义 Django 应用的元信息（应用名、后台展示名等）
- 在开发/演示模式下，可选择性启动“AI 自动审核循环线程”

AI 自动审核线程说明：
- 通过环境变量 AI_AUTO_REVIEW_LOOP 控制是否启用
- 只在 runserver 启动时开启，避免迁移/脚本等场景误启动
- 使用 RUN_MAIN/--noreload 防止 Django 自动重载导致重复启动线程
"""

from django.apps import AppConfig


class TicketsApiConfig(AppConfig):
    """
    tickets_api 应用配置类。

    这里的 ready() 会在 Django 启动并加载应用后执行，可用于注册信号/启动后台线程等。
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tickets_api'
    verbose_name = '报修系统管理'

    def ready(self):
        """
        应用就绪钩子。

        当前实现用途：可选启动 AI 自动审核循环（用于答辩演示“AI 自动过审”效果）。
        """
        import os
        import sys
        import threading
        import time
        from django.core.management import call_command

        if not (os.environ.get('AI_AUTO_REVIEW_LOOP') or '').strip():
            return
        if 'runserver' not in sys.argv:
            return
        if os.environ.get('RUN_MAIN') not in {'true', 'True', '1', 1} and '--noreload' not in sys.argv:
            return

        try:
            interval = int(os.environ.get('AI_AUTO_REVIEW_INTERVAL') or '20')
        except Exception:
            interval = 20
        if interval < 1:
            interval = 1

        mod = sys.modules.get(__name__)
        if getattr(mod, '_ai_auto_review_started', False):
            return
        setattr(mod, '_ai_auto_review_started', True)

        def _loop():
            while True:
                try:
                    call_command('ai_auto_review', limit=200)
                except Exception:
                    pass
                time.sleep(interval)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()
