#!/usr/bin/env python
"""
后端入口脚本（Django 管理命令）。

用途：
- 统一入口：python manage.py runserver / migrate / createsuperuser 等
- 在启动任何 Django 命令前，负责设置 DJANGO_SETTINGS_MODULE 指向项目 settings

提示：
- 本项目的核心后端应用为 tickets_api
- 如果你在本机使用虚拟环境，先激活 .venv 再运行本文件
"""
import os
import sys


def main():
    """
    运行 Django 管理命令。

    该函数会把命令行参数原样交给 Django 的 execute_from_command_line 处理。
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'it_backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
