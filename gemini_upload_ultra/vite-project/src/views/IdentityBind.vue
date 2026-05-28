<!--
文件：src/views/IdentityBind.vue
类型：页面组件
说明：
- 该文件为前端业务模块，实现页面渲染、交互与接口调用
- 主要逻辑在 <script setup> 中（状态、事件、请求、路由跳转等）
涉及接口：bind-identity/
-->

<template>
  <div class="bind-wrapper">
    <div class="bind-card">
      <div class="header">
        <h2><i class="fas fa-id-card"></i> 身份认证绑定</h2>
      </div>
      <div class="warning">
        <i class="fas fa-info-circle"></i> 为了确保报修数据的真实性，请绑定您的校园身份信息。
      </div>

      <form @submit.prevent="handleBind">
        <div class="form-group">
          <label>我是：</label>
          <select v-model="form.role" required>
          <option value="student">在校学生</option>
          <option value="maintenance">维修人员</option>
          <option value="auditor">审核员</option>
          </select>
        </div>
        <div class="form-group">
          <label>真实姓名：</label>
          <input type="text" v-model="form.name" required>
        </div>
        <div class="form-group">
          <label>学号/工号：</label>
          <input type="text" v-model="form.identity_id" required>
        </div>
        
        <button class="btn-primary" type="submit" :disabled="loading">确认绑定</button>
      </form>
      <div v-if="error" class="error-banner">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { apiUrl } from '@/config'

const form = ref({ role: 'student', name: '', identity_id: '' })
const authStore = useAuthStore()
const router = useRouter()
const loading = ref(false)
const error = ref('')

async function handleBind() {
  error.value = ''
  loading.value = true
  try {
    const res = await axios.post(apiUrl('bind-identity/'), form.value, {
      headers: { Authorization: `Token ${authStore.token}` }
    })
    // 更新本地状态
    authStore.currentUser = res.data.user
    localStorage.setItem('user', JSON.stringify(res.data.user))
    
    // alert("绑定成功！")
    const role = res.data.user?.role
    const phone = (res.data.user?.phone || '').trim()
    if (!phone) {
      router.push('/profile')
      return
    }
    if (role === 'auditor') router.push('/approval')
    else if (['maintenance', 'repair_admin', 'admin'].includes(role)) router.push('/workplace')
    else router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '绑定失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.bind-wrapper { display: flex; justify-content: center; padding-top: 50px; min-height: 100vh; background: #f0f2f5; }
.bind-card { width: 400px; padding: 30px; background: white; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); height: fit-content;}
.header { text-align: center; margin-bottom: 20px; color: #333; }
.warning { background: #e3f2fd; color: #0d47a1; padding: 10px; margin-bottom: 20px; font-size: 13px; border-radius: 4px; border: 1px solid #bbdefb; }
.form-group { margin-bottom: 15px; }
.form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
.form-group input, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
.btn-primary { width: 100%; padding: 12px; background: #667eea; color: white; border:none; border-radius: 5px; cursor: pointer; margin-top: 10px; font-size: 16px;}
.btn-text { width: 100%; padding: 10px; background: none; border: none; color: #666; cursor: pointer; margin-top: 10px; font-size: 14px; text-decoration: underline; }
.error-banner { margin-top: 14px; padding: 10px 12px; background: #fee2e2; color: #991b1b; border-radius: 8px; font-weight: 700; }
</style>
