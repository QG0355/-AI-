"""
ASGI 入口（用于异步服务器部署）。

用途：
- 将 Django 项目暴露为 ASGI 应用（application）
- 部署到支持 ASGI 的服务器（如 uvicorn / daphne）时使用

说明：
- 本项目主要用于开发/答辩演示，通常 runserver 使用 WSGI 即可
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'it_backend.settings')

application = get_asgi_application()
