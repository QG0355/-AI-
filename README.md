# 答辩核心功能材料包

这个文件夹用于把“核心功能相关代码/配置”单独抽出来，方便直接发给 Gemini 生成答辩记录表内容；已尽量去掉与功能无关的构建产物、图片、示例数据大段列表等。

## 目录说明（对应系统模块）

- 部署与转发
  - `docker-compose.yml`：数据库 + 后端 + 前端整体编排（已对敏感信息做脱敏）
  - `frontend/nginx.conf`：前端静态资源 + `/api` + `/uploads` 反向代理
- 后端（Flask API）
  - `backend/app/__init__.py`：应用工厂、蓝图注册、上传文件访问、任务缓存初始化、模型预加载
  - `backend/app/api/*.py`：各功能模块 API（登录注册、识别分析、食物库、饮食记录、历史报表、健康评估、用户管理）
  - `backend/app/db/models.py`：核心数据表结构（User/FoodItem/DietRecord/AnalysisRecord/NutritionAssessment 等）
- 前端（Vue3）
  - `frontend/src/router/index.js`：前台/后台路由与鉴权守卫
  - `frontend/src/api/index.js`：API 调用封装（Axios + Token 注入 + 401 处理）与接口映射

## 建议你发给 Gemini 的方式

1. 直接把整个 `答辩核心功能` 文件夹打包（zip）后发给 Gemini。
2. 让 Gemini 重点阅读：
   - 后端各 `api/*.py` 的接口功能
   - 前端 `router/index.js` 的页面结构
   - `analysis.py` 的“图片识别→营养估算→建议→导出 PDF”流水线

