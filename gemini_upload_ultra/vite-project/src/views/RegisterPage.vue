<!--
文件：src/views/RegisterPage.vue
类型：页面组件
说明：
- 该文件为前端业务模块，实现页面渲染、交互与接口调用
- 主要逻辑在 <script setup> 中（状态、事件、请求、路由跳转等）
涉及接口：register/
-->

<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <div class="logo-icon">
          <i class="fas fa-user-plus"></i>
        </div>
        <h2>注册新账号</h2>
      </div>

      <form @submit.prevent="handleRegister">
        <div class="input-group">
          <label>账号 / User ID</label>
          <div class="input-wrapper">
            <i class="fas fa-user"></i>
            <input type="text" v-model="form.username" placeholder="请设置登录账号" required>
          </div>
        </div>

        <div class="input-group">
          <label>密码 / Password</label>
          <div class="input-wrapper">
            <i class="fas fa-lock"></i>
            <input type="password" v-model="form.password" placeholder="请设置密码" required>
          </div>
        </div>

        <div class="input-group">
          <label>确认密码 / Confirm</label>
          <div class="input-wrapper">
            <i class="fas fa-check-circle"></i>
            <input type="password" v-model="form.confirmPassword" placeholder="请再次输入密码" required>
          </div>
        </div>
        
        <button type="submit" class="btn-login" :disabled="loading">
          {{ loading ? '注册中...' : '立即注册' }}
        </button>

        <div class="login-footer">
          <span>已有账号？</span>
          <a @click.prevent="$router.push('/login')" class="link-btn">返回登录</a>
        </div>
      </form>
      
      <div v-if="error" class="error-banner">
        <i class="fas fa-exclamation-circle"></i> {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { apiUrl } from '@/config'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const loading = ref(false)
const error = ref(null)

const form = ref({
  username: '',
  password: '',
  confirmPassword: ''
})

async function handleRegister() {
  if (form.value.password !== form.value.confirmPassword) {
    error.value = "两次输入的密码不一致！"
    return
  }

  loading.value = true
  error.value = null

  try {
    // 1. 发送注册请求
    await axios.post(apiUrl('register/'), {
      username: form.value.username,
      password: form.value.password
    })
    
    // 2. 注册成功后尝试自动登录
    const authStore = useAuthStore()
    const loginResult = await authStore.login(form.value.username, form.value.password)
    
    if (loginResult.success) {
      // 登录成功，跳转到身份绑定
      router.push('/bind')
    } else {
      // 登录失败（虽然注册成功了），跳转到登录页手动登录
      router.push('/login')
    }

  } catch (err) {
    loading.value = false
    const data = err.response?.data || {}
    if (data.username) error.value = "注册失败: 账号已存在"
    else error.value = '注册失败，请检查网络或联系管理员。'
  }
}
</script>

<style scoped>
/* 复用 LoginPage 的样式，保持一致性 */
.login-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-box {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2); 
  animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideUp {
  from { transform: translateY(30px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.login-header {
  text-align: center;
  margin-bottom: 35px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  margin-bottom: 15px;
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.4);
  transform: rotate(-5deg);
}

.login-header h2 {
  color: #1e293b;
  font-size: 26px;
  font-weight: 800;
  margin-bottom: 5px;
  letter-spacing: -0.5px;
}

.login-header p {
  color: #64748b;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
}

.input-group {
  margin-bottom: 24px;
}

.input-group label {
  display: block;
  margin-bottom: 8px;
  color: #475569;
  font-size: 14px;
  font-weight: 600;
}

.input-wrapper {
  position: relative;
}

.input-wrapper i {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
  font-size: 16px;
  transition: color 0.3s;
}

.input-wrapper input {
  width: 100%;
  padding: 14px 16px 14px 48px;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 15px;
  color: #334155;
  background: #f8fafc;
  transition: all 0.3s;
  box-sizing: border-box;
}

.input-wrapper input:focus {
  border-color: #3b82f6;
  background: white;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}

.input-wrapper input:focus + i {
  color: #3b82f6;
}

.btn-login {
  width: 100%;
  padding: 14px;
  background: linear-gradient(to right, #3b82f6, #2563eb);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
}

.btn-login:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.4);
}

.btn-login:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.login-footer {
  margin-top: 25px;
  text-align: center;
  font-size: 14px;
  color: #64748b;
}

.link-btn {
  color: #3b82f6;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: color 0.2s;
}

.link-btn:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.error-banner {
  margin-top: 20px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #ef4444;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  animation: shake 0.4s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

/* Mobile Adaptation */
@media (max-width: 480px) {
  .login-box {
    padding: 30px 20px;
  }
}
</style>
