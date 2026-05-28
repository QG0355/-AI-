/**
 * 文件：src/config.js
 * 类型：运行配置
 * 说明：
 * - 该文件为前端业务模块，实现状态/路由/配置/工具函数等
 * - 涉及接口：无
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export function apiUrl(path) {
  const p = String(path || '').replace(/^\/+/, '')
  return `${API_BASE_URL}/api/${p}`
}
