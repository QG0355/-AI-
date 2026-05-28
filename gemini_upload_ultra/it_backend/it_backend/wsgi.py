"""
WSGI 入口（用于传统同步服务器部署）。

用途：
- 将 Django 项目暴露为 WSGI 应用（application）
- runserver 与多数传统部署方式（gunicorn/uwsgi 等）都依赖该入口
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'it_backend.settings')

application = get_wsgi_application()
