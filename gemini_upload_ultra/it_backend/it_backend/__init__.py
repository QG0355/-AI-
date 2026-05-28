"""
Django 项目包初始化。

作用：
- 使用 PyMySQL 兼容 MySQLdb（让 Django 的 MySQL backend 可正常工作）
- 避免在 Windows/部分环境下强依赖 mysqlclient 编译安装
"""

import pymysql
pymysql.install_as_MySQLdb()
