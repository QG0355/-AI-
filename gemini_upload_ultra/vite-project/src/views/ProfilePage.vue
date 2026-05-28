<!--
文件：src/views/ProfilePage.vue
类型：页面组件
说明：
- 该文件为前端业务模块，实现页面渲染、交互与接口调用
- 主要逻辑在 <script setup> 中（状态、事件、请求、路由跳转等）
涉及接口：me/、me/avatar/
-->

<template>
  <div class="profile-page">
    <div class="profile-card">
      <div class="profile-header">
        <div class="avatar" :style="avatarStyle" aria-label="头像"></div>
        <div class="header-text">
          <h2>个人主页</h2>
          <div class="sub">
            <span class="role">{{ roleName }}</span>
            <span class="username">@{{ auth.currentUser?.username }}</span>
          </div>
        </div>
      </div>

      <div class="grid">
        <div class="field">
          <div class="label">姓名</div>
          <input v-model="form.name" type="text" placeholder="请输入姓名" />
        </div>

        <div class="field">
          <div class="label">性别</div>
          <select v-model="form.gender">
            <option value="unknown">未知</option>
            <option value="male">男</option>
            <option value="female">女</option>
          </select>
        </div>

        <div v-if="auth.currentUser?.role !== 'admin'" class="field full">
          <div class="label">手机号</div>
          <input v-model="form.phone" type="text" placeholder="请输入手机号" />
        </div>
      </div>

      <div class="upload">
        <div class="upload-title">本地头像</div>
        <div class="upload-row">
          <input class="file" type="file" accept="image/*" @change="onPickAvatar" />
          <button class="btn" :disabled="uploading || !pickedAvatar" @click="uploadAvatar">
            {{ uploading ? '上传中...' : '上传头像' }}
          </button>
        </div>
        <div class="upload-hint">支持 JPG/PNG/WEBP/GIF，≤5MB</div>
      </div>

      <div class="identity">
        <div class="identity-row">
          <div class="k">身份绑定</div>
          <div class="v">
            <span v-if="auth.currentUser?.is_identity_bound">
              已绑定：{{ auth.currentUser?.identity_id || '-' }}
            </span>
            <span v-else>未绑定</span>
          </div>
          <button v-if="!auth.currentUser?.is_identity_bound" class="btn" @click="goBind">
            去绑定
          </button>
        </div>
      </div>

      <div v-if="auth.currentUser?.role === 'maintenance'" class="rating">
        <div class="rating-title">我的评分</div>
        <div class="rating-value">
          <span class="score">
            {{ formatScore(auth.currentUser?.maintenance_rating) }}
          </span>
          <span class="count">（{{ auth.currentUser?.maintenance_rating_count || 0 }}单）</span>
        </div>
      </div>

      <div class="actions">
        <button class="btn primary" :disabled="saving" @click="save">
          {{ saving ? '保存中...' : '保存资料' }}
        </button>
      </div>

      <div v-if="error" class="error">{{ error }}</div>
      <div v-if="success" class="success">{{ success }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { apiUrl } from '@/config'
import { DEFAULT_USER_AVATAR } from '@/assets/imageSources'

const auth = useAuthStore()
const router = useRouter()

const form = ref({ name: '', gender: 'unknown', phone: '' })
const saving = ref(false)
const uploading = ref(false)
const error = ref('')
const success = ref('')
const pickedAvatar = ref(null)
const pickedAvatarPreview = ref('')

const roleName = computed(() => {
  const map = {
    student: '学生',
    maintenance: '维修师傅',
    auditor: '审核员',
    admin: '管理员',
    repair_admin: '维修主管'
  }
  return map[auth.currentUser?.role] || '用户'
})

const avatarSource = computed(() => {
  return pickedAvatarPreview.value || auth.currentUser?.avatar || DEFAULT_USER_AVATAR
})

const avatarStyle = computed(() => {
  const v = avatarSource.value || DEFAULT_USER_AVATAR
  if (typeof v === 'string' && v.trim().startsWith('#')) {
    return { backgroundColor: v }
  }
  return {
    backgroundImage: `url(${v})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center'
  }
})

function formatScore(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '暂无'
  return n.toFixed(1)
}

function goBind() {
  router.push('/bind')
}

onMounted(async () => {
  if (!auth.isLoggedIn) {
    router.push('/login')
    return
  }
  await auth.fetchUser()
  form.value = {
    name: auth.currentUser?.name || '',
    gender: auth.currentUser?.gender || 'unknown',
    phone: auth.currentUser?.phone || ''
  }
})

onBeforeUnmount(() => {
  if (pickedAvatarPreview.value) {
    URL.revokeObjectURL(pickedAvatarPreview.value)
  }
})

function onPickAvatar(e) {
  success.value = ''
  error.value = ''
  const file = e?.target?.files?.[0]
  if (!file) return
  if (pickedAvatarPreview.value) {
    URL.revokeObjectURL(pickedAvatarPreview.value)
  }
  pickedAvatar.value = file
  pickedAvatarPreview.value = URL.createObjectURL(file)
}

async function uploadAvatar() {
  if (!pickedAvatar.value) return
  if (!auth.isLoggedIn) return
  success.value = ''
  error.value = ''
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', pickedAvatar.value)
    const res = await axios.post(apiUrl('me/avatar/'), fd, {
      headers: { Authorization: `Token ${auth.token}` }
    })
    auth.currentUser = res.data
    success.value = '头像上传成功'
    pickedAvatar.value = null
    if (pickedAvatarPreview.value) {
      URL.revokeObjectURL(pickedAvatarPreview.value)
    }
    pickedAvatarPreview.value = ''
  } catch (e) {
    error.value = e?.response?.data?.detail || '头像上传失败'
  } finally {
    uploading.value = false
  }
}

async function save() {
  if (!auth.isLoggedIn) return
  error.value = ''
  success.value = ''
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      gender: form.value.gender
    }
    const p = (form.value.phone || '').trim()
    if (p) payload.phone = p
    const res = await axios.patch(
      apiUrl('me/'),
      payload,
      { headers: { Authorization: `Token ${auth.token}` } }
    )
    auth.currentUser = res.data
    success.value = '保存成功'
  } catch (e) {
    error.value = e?.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-page {
  padding: 22px 14px;
  display: flex;
  justify-content: center;
}

.profile-card {
  width: 100%;
  max-width: 1000px;
  background: white;
  border-radius: 16px;
  border: 1px solid #f0e6ee;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.06);
  padding: 18px 18px 16px;
}

.profile-header {
  display: flex;
  gap: 14px;
  align-items: center;
  padding-bottom: 14px;
  border-bottom: 1px solid #f4e7ef;
}

.avatar {
  width: 72px;
  height: 72px;
  border-radius: 14px;
  border: 1px solid #f0d6e3;
}

.header-text h2 {
  margin: 0;
  font-size: 20px;
  color: #1f2937;
}

.sub {
  margin-top: 6px;
  display: flex;
  gap: 10px;
  align-items: center;
  color: #6b7280;
  font-size: 13px;
}

.role {
  padding: 2px 8px;
  border-radius: 999px;
  background: #fff3f5;
  border: 1px solid #ffd0dd;
  color: #b0325b;
  font-weight: 700;
}

.grid {
  margin-top: 14px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 12px;
}

.field.full {
  grid-column: 1 / -1;
}

.label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}

input,
select {
  width: 100%;
  padding: 10px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  box-sizing: border-box;
  background: #fff;
}

.identity {
  margin-top: 14px;
  border-top: 1px dashed #f0d6e3;
  padding-top: 12px;
}

.upload {
  margin-top: 14px;
  padding: 12px;
  border-radius: 12px;
  background: #fbfcff;
  border: 1px solid #e5eaf5;
}

.upload-title {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 10px;
}

.upload-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.file {
  max-width: 100%;
}

.upload-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}

.identity-row {
  display: grid;
  grid-template-columns: 86px 1fr auto;
  align-items: center;
  gap: 10px;
}

.k {
  color: #6b7280;
  font-size: 13px;
}

.v {
  color: #111827;
  font-size: 13px;
}

.rating {
  margin-top: 14px;
  padding: 12px;
  border-radius: 12px;
  background: #fff9fb;
  border: 1px solid #f1e2ea;
}

.rating-title {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 6px;
}

.rating-value {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.score {
  font-size: 22px;
  font-weight: 900;
  color: #b0325b;
}

.count {
  font-size: 13px;
  color: #6b7280;
}

.actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

.btn {
  border: 1px solid #e5e7eb;
  background: white;
  padding: 8px 12px;
  border-radius: 10px;
  cursor: pointer;
  color: #374151;
  font-weight: 700;
}

.btn.primary {
  background: #667eea;
  border-color: #667eea;
  color: white;
}

.btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.error {
  margin-top: 10px;
  color: #b91c1c;
  font-size: 13px;
}

.success {
  margin-top: 10px;
  color: #047857;
  font-size: 13px;
}

@media (max-width: 640px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .identity-row {
    grid-template-columns: 86px 1fr;
  }
  .identity-row .btn {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
</style>
