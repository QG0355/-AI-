/**
 * 文件：src/stores/auth.js
 * 类型：状态管理
 * 说明：
 * - 该文件为前端业务模块，实现状态/路由/配置/工具函数等
 * - 涉及接口：login/、me/
 */

// src/stores/auth.js
import { defineStore } from 'pinia'
import axios from 'axios'
import { apiUrl } from '@/config'

function getStoredToken() {
  const t = localStorage.getItem('token')
  if (!t || t === 'null' || t === 'undefined') {
    localStorage.removeItem('token')
    return null
  }
  return t
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    currentUser: null,
    token: getStoredToken()
  }),

  getters: {
    isLoggedIn: (state) => !!state.token,
    isAdmin: (state) => state.currentUser?.role === 'admin'
  },

  actions: {
    async login(username, password) {
      try {
        const response = await axios.post(apiUrl('login/'), { username, password })
        
        this.token = response.data.token
        this.currentUser = response.data.user
        localStorage.setItem('token', this.token)
        axios.defaults.headers.common['Authorization'] = `Token ${this.token}`
        
        // 登录成功，返回一个带 success 标记的对象
        return { success: true }

      } catch (error) {
        console.error('登录报错详情:', error)
        console.error('Error response:', error.response)
        console.error('Error data:', error.response?.data)
        console.error('Error status:', error.response?.status)
        
        // --- ⭐ 核心修改：提取详细错误信息 ⭐ ---
        let errorMsg = "登录失败，请检查网络"
        
        if (error.response && error.response.data) {
            const data = error.response.data
            
            // 情况 1: Django 自带的错误 (比如 {"non_field_errors": ["无法使用提供的认证信息登录。"]})
            if (data.non_field_errors) {
                errorMsg = data.non_field_errors[0]
            } 
            // 情况 2: 我们自定义的错误 (比如 {"detail": "..."})
            else if (data.detail) {
                errorMsg = data.detail
            }
            // 情况 3: 字段错误 (比如 {"password": ["此字段是必填项。"]})
            else {
                // 把所有错误拼起来显示
                errorMsg = JSON.stringify(data)
            }
        } else if (!error.response) {
            errorMsg = "无法连接到服务器，请检查后端服务是否启动"
        }
        
        // 登录失败，返回 success: false 和具体的错误消息
        return { success: false, message: errorMsg }
      }
    },
    
    logout() {
      this.currentUser = null
      this.token = null
      localStorage.removeItem('token')
      delete axios.defaults.headers.common['Authorization']
      try {
        const keys = []
        for (let i = 0; i < sessionStorage.length; i++) {
          const k = sessionStorage.key(i)
          if (!k) continue
          if (k.startsWith('ai_chat_messages_user_') || k === 'ai_chat_messages_guest') {
            keys.push(k)
          }
        }
        keys.forEach(k => sessionStorage.removeItem(k))
      } catch (e) {}
    },

    // 新增：初始化时获取用户信息
    async fetchUser() {
      if (!this.token) return
      
      try {
        // 确保 header 里有 token
        axios.defaults.headers.common['Authorization'] = `Token ${this.token}`
        const response = await axios.get(apiUrl('me/'))
        this.currentUser = response.data
      } catch (error) {
        console.error('获取用户信息失败:', error)
        if (error?.response?.status === 401) {
          alert('登录已过期，请重新登录')
        }
        // 如果 token 失效，自动登出
        this.logout()
      }
    }
  }
})
