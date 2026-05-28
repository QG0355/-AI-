"""
后端路由总入口（Django URLConf）。

职责：
- 挂载 Django 自带管理后台：/admin/
- 挂载业务 API：/api/ -> tickets_api.urls
- 开发环境（DEBUG=True）下提供媒体文件访问（头像/附件等）
"""

from django.contrib import admin
from django.urls import path, include  # 1. 确保导入了 include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # 业务 API 统一挂载到 /api/ 前缀下，前端所有请求都走这一套入口
    path('api/', include('tickets_api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
