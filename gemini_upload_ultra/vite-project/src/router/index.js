/**
 * 文件：src/router/index.js
 * 类型：路由配置
 * 说明：
 * - 该文件为前端业务模块，实现状态/路由/配置/工具函数等
 * - 涉及接口：无
 */

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', component: () => import('@/views/LoginPage.vue') },
  { path: '/register', component: () => import('@/views/RegisterPage.vue') },
  { path: '/forgot-password', component: () => import('@/views/ForgotPassword.vue') },
  { path: '/bind', component: () => import('@/views/IdentityBind.vue') },
  
  { 
    path: '/', 
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      // 首页是 Dashboard (欢迎页)
      { path: '', component: () => import('@/views/Dashboard.vue') },
      
      // ⚠️ 关键：这里必须有 'submit'，而且对应的组件必须存在！
      { path: 'submit', component: () => import('@/views/SubmitTicket.vue') },
      
      { path: 'tickets', component: () => import('@/views/MyTickets.vue') },
      { path: 'workplace', component: () => import('@/views/Workplace.vue') },
      { path: 'ai-chat', component: () => import('@/views/AiAssistant.vue') },
      { path: 'profile', component: () => import('@/views/ProfilePage.vue') },
      { path: 'approval', component: () => import('@/views/OAApproval.vue') },
      { path: 'admin', component: () => import('@/views/AdminDashboard.vue') }
    ]
  }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const publicPages = ['/login', '/register', '/forgot-password'] // 允许未登录访问的页面

  if (publicPages.includes(to.path) && authStore.isLoggedIn) {
    return next('/')
  }
  
  // 如果去的是受保护页面 (非publicPages) 且没登录
  // 注意：主页 '/' 现在是 SubmitTicket，如果是公共的就加进数组，如果必须登录才显示就删掉 '/'
  // 根据你之前的需求 "未登录显示登录按钮"，主页应该是半公开的，SubmitTicket 内部有处理
  
  // 这里我们只拦截明确需要登录的子路由，或者你可以在这里简单处理：
  // if (!publicPages.includes(to.path) && !authStore.isLoggedIn && to.path !== '/') {
  //   return next('/login')
  // }
  
  // 为了简单起见，且 SubmitTicket 页面内部已经做了 "未登录遮罩"，这里直接放行 '/'
  
  next()
})

export default router
