<!--
文件：src/views/ForgotPassword.vue
类型：页面组件
说明：
- 该文件为前端业务模块，实现页面渲染、交互与接口调用
- 主要逻辑在 <script setup> 中（状态、事件、请求、路由跳转等）
涉及接口：forgot-password/
-->

<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <div class="logo-icon">
          <i class="fas fa-key"></i>
        </div>
        <h2>找回密码</h2>
        <p>手机号 + 学号/工号验证</p>
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="input-group">
          <label>账号</label>
          <div class="input-wrapper">
            <i class="fas fa-user"></i>
            <input type="text" v-model="form.username" placeholder="请输入账号" required>
          </div>
        </div>

        <div class="input-group">
          <label>学号 / 工号</label>
          <div class="input-wrapper">
            <i class="fas fa-id-card"></i>
            <input type="text" v-model="form.identity_id" placeholder="请输入学号/工号" required>
          </div>
        </div>

        <div class="input-group">
          <label>手机号</label>
          <div class="input-wrapper">
            <i class="fas fa-phone"></i>
            <input type="text" v-model="form.phone" placeholder="请输入手机号" required>
          </div>
        </div>

        <div class="input-group">
          <label>新密码</label>
          <div class="input-wrapper">
            <i class="fas fa-lock"></i>
            <input type="password" v-model="form.new_password" placeholder="请输入新密码（至少6位）" required>
          </div>
        </div>

        <div class="input-group">
          <label>确认新密码</label>
          <div class="input-wrapper">
            <i class="fas fa-lock"></i>
            <input type="password" v-model="confirmPassword" placeholder="请再次输入新密码" required>
          </div>
        </div>

        <button type="submit" class="btn-login" :disabled="loading">
          {{ loading ? '提交中...' : '重置密码' }}
        </button>

        <div class="login-footer">
          <div class="login-links">
            <a @click.prevent="$router.push('/login')" class="link-btn">返回登录</a>
          </div>
        </div>
      </form>

      <div v-if="error" class="error-banner">
        <i class="fas fa-exclamation-circle"></i> {{ error }}
      </div>
      <div v-if="success" class="success-banner">
        <i class="fas fa-check-circle"></i> {{ success }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { apiUrl } from '@/config'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const success = ref('')
const confirmPassword = ref('')
const form = ref({ username: '', identity_id: '', phone: '', new_password: '' })

async function handleSubmit() {
  error.value = ''
  success.value = ''
  if (form.value.new_password !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    const res = await axios.post(apiUrl('forgot-password/'), form.value)
    success.value = res.data?.detail || '密码已重置'
    setTimeout(() => router.push('/login'), 600)
  } catch (e) {
    error.value = e.response?.data?.detail || '提交失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
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

.input-group { margin-bottom: 18px; }
.input-group label { display: block; margin-bottom: 8px; color: #475569; font-size: 14px; font-weight: 600; }
.input-wrapper { position: relative; }
.input-wrapper i { position: absolute; left: 16px; top: 50%; transform: translateY(-50%); color: #94a3b8; font-size: 16px; }
.input-wrapper input { width: 100%; padding: 14px 16px 14px 48px; border: 2px solid #e2e8f0; border-radius: 10px; font-size: 15px; color: #334155; background: #f8fafc; transition: all 0.3s; box-sizing: border-box; }
.input-wrapper input:focus { border-color: #3b82f6; background: white; box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1); }

.btn-login { width: 100%; padding: 14px; background: linear-gradient(to right, #3b82f6, #2563eb); color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 700; cursor: pointer; }
.btn-login:disabled { opacity: 0.7; cursor: not-allowed; }

.login-footer { margin-top: 18px; display: flex; justify-content: center; }
.login-links { font-size: 14px; color: #475569; }
.link-btn { cursor: pointer; color: #2563eb; text-decoration: underline; font-weight: 700; }

.error-banner { margin-top: 18px; padding: 12px 14px; background: #fee2e2; color: #991b1b; border-radius: 10px; font-weight: 700; }
.success-banner { margin-top: 18px; padding: 12px 14px; background: #dcfce7; color: #166534; border-radius: 10px; font-weight: 700; }
</style>
