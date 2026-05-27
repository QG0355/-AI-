# it_backend/urls.py

from django.contrib import admin
from django.urls import path, include  # 1. 确保导入了 include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # 2. 确保这里写的是 'tickets_api.urls'
    #    千万不要写成 'it_backend.urls'！
    path('api/', include('tickets_api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
