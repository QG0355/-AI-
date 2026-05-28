/**
 * 文件：src/main.js
 * 类型：应用入口
 * 说明：
 * - 该文件为前端业务模块，实现状态/路由/配置/工具函数等
 * - 涉及接口：无
 */

import { createApp } from 'vue'
import { createPinia } from 'pinia' // 1. 导入 Pinia
import './style.css' 
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth' // 导入 authStore



const app = createApp(App)
const pinia = createPinia() // 2. 创建 Pinia 实例

app.use(router) // 告诉 Vue 使用路由
app.use(pinia) // 3. 告诉 Vue 使用 Pinia

// 4. 初始化时恢复用户信息
const auth = useAuthStore()
if (auth.token) {
  auth.fetchUser()
}

app.mount('#app')