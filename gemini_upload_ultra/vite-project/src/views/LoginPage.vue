<!--
文件：src/views/LoginPage.vue
类型：页面组件
说明：
- 该文件为前端业务模块，实现页面渲染、交互与接口调用
- 主要逻辑在 <script setup> 中（状态、事件、请求、路由跳转等）
涉及接口：无
-->

<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <div class="logo-icon">
          <i class="fas fa-tools"></i>
        </div>
        <h2>校园报修服务平台</h2>
        <p>请使用账号密码登录</p>
      </div>

      <form @submit.prevent="handleLogin">
        <div class="input-group">
          <label>账号</label>
          <div class="input-wrapper">
            <i class="fas fa-user"></i>
            <input type="text" v-model="username" placeholder="请输入账号" required>
          </div>
        </div>

        <div class="input-group">
          <label>密码</label>
          <div class="input-wrapper">
            <i class="fas fa-lock"></i>
            <input type="password" v-model="password" placeholder="请输入密码" required>
          </div>
        </div>

        <button type="submit" class="btn-login" :disabled="loading">
          {{ loading ? '正在登录...' : '登 录' }}
        </button>

        <div class="login-footer">
          <div class="login-links">
            <span>还没有账号？</span>
            <a @click.prevent="$router.push('/register')" class="link-btn">注册新用户</a>
          </div>
          <div class="login-links">
            <a @click.prevent="$router.push('/forgot-password')" class="link-btn">忘记密码</a>
          </div>
          <div class="login-links">
            <a @click.prevent="$router.push('/')" class="link-btn">返回主页</a>
          </div>
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
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref(null)
const authStore = useAuthStore()
const router = useRouter()

async function handleLogin() {
  loading.value = true
  error.value = null
  
  const result = await authStore.login(username.value, password.value)
  
  loading.value = false
  
  if (result.success) {
    const user = authStore.currentUser
    const role = user?.role

    if (role === 'admin') {
      const backendAdminUrl = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}/admin/`
      window.location.href = backendAdminUrl
      return
    }

    if (!user?.is_identity_bound) {
      router.push('/bind')
      return
    }

    if (role === 'auditor') {
      router.push('/approval')
    } else if (['maintenance', 'repair_admin'].includes(role)) {
      router.push('/workplace')
    } else {
      router.push('/')
    }
  } else {
    error.value = result.message 
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

.login-links {
  margin-top: 10px;
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
  
  .login-header h2 {
    font-size: 22px;
  }
  
  .logo-icon {
    width: 56px;
    height: 56px;
    font-size: 24px;
  }
}
</style>
