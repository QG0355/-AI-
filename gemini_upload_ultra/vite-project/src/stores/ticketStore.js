/**
 * 文件：src/stores/ticketStore.js
 * 类型：状态管理
 * 说明：
 * - 该文件为前端业务模块，实现状态/路由/配置/工具函数等
 * - 涉及接口：tickets/
 */

// src/stores/ticketStore.js
import { defineStore } from 'pinia'
import axios from 'axios'
import { useAuthStore } from './auth' // 引入 auth 仓库，用来拿 Token
import { apiUrl } from '@/config'

export const useTicketStore = defineStore('ticket', {
  state: () => ({
    tickets: [],
    loading: false
  }),
  
  actions: {
    // 1. 获取报修单列表 (合并为一个 fetchTickets 函数)
    async fetchTickets(search = '') {
      const authStore = useAuthStore()
      
      if (!authStore.token) return 

      this.loading = true
      try {
        const response = await axios.get(apiUrl('tickets/'), {
          headers: { 
            Authorization: `Token ${authStore.token}` 
          },
          params: {
            search: search
          }
        })
        
        this.tickets = response.data
      } catch (error) {
        console.error('获取报修单失败:', error?.message || error)
      } finally {
        this.loading = false
      }
    },
    // 2. 提交新报修单
    async createTicket(ticketData) {
      const authStore = useAuthStore()
      try {
        // 发送 POST 请求
        await axios.post(apiUrl('tickets/'), ticketData, {
          headers: { Authorization: `Token ${authStore.token}` }
        })
        // 提交成功后，重新获取一下最新列表
        this.fetchTickets()
        return true
      } catch (error) {
        console.error('提交失败:', error?.message || error)
        alert("提交失败，请稍后重试")
        return false
      }
    }
  }
})
