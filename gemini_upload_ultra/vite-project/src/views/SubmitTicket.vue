<template>
  <div class="page-content">
    <h2><i class="fas fa-wrench"></i> {{ isEdit ? '修改并重新提交' : '提交报修单' }}</h2>
    
    <div class="form-card">
      <form @submit.prevent="submitTicket">
        <div class="form-row">
          <div class="form-group half">
            <label>标题</label>
            <input v-model="form.title" placeholder="例如：302宿舍空调漏水" required>
          </div>
          <div class="form-group half">
            <label>故障位置</label>
            <input v-model="form.location" placeholder="例如：教学楼A栋 302室" required>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group half">
            <label>故障类型</label>
            <select v-model="form.category" required>
              <option value="">请选择类型</option>
              <option value="水电问题">水电问题</option>
              <option value="网络连接">网络问题</option>
              <option value="其他">其他</option>
            </select>
          </div>
          
          <div class="form-group half">
            <label>优先级</label>
            <select v-model="form.priority" required>
              <option value="低">低 - 不影响使用</option>
              <option value="中">中 - 影响部分功能</option>
              <option value="高">高 - 无法工作</option>
              <option value="紧急">紧急 - 安全隐患</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>联系电话</label>
          <input v-model="form.contact" placeholder="请填写手机号，方便联系" required>
        </div>

        <div class="form-group">
          <label>故障详细描述</label>
          <textarea v-model="form.description" rows="4" placeholder="请详细描述故障现象..."></textarea>
        </div>

        <div class="form-group">
          <label>上传图片</label>
          <input
            type="file"
            multiple
            accept="image/*,video/*"
            @change="onFilesChange"
          >
          <div class="upload-hint">
            仅支持图片(jpg/jpeg/png)。图片≤5MB。
          </div>

          <div v-if="existingAttachments.length" class="existing-list">
            <div class="existing-title">已上传附件</div>
            <div class="preview-grid">
              <div v-for="a in existingAttachments" :key="a.id" class="preview-item">
                <img v-if="a.media_type === 'image'" :src="a.url" alt="图片" />
                <video v-else controls :src="a.url"></video>
                <div class="file-name">{{ a.original_name || a.url }}</div>
              </div>
            </div>
          </div>

          <div v-if="files.length" class="preview-grid">
            <div v-for="(f, idx) in files" :key="idx" class="preview-item">
              <img v-if="f.previewType === 'image'" :src="f.previewUrl" alt="图片预览" />
              <video v-else controls :src="f.previewUrl"></video>
              <div class="file-name">{{ f.file.name }}</div>
              <button type="button" class="btn-remove" @click="removeFile(idx)">移除</button>
            </div>
          </div>
        </div>

        <button class="btn-primary" :disabled="loading">
          {{ loading ? '提交中...' : (isEdit ? '修改并重新提交' : '提交报修单') }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import axios from 'axios'
import { useRouter, useRoute } from 'vue-router'
import { apiUrl } from '@/config'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const loading = ref(false)

const form = ref({
  title: '',
  location: '', 
  category: '',
  priority: '中',
  description: '',
  contact: ''
})

const editId = computed(() => {
  const v = route.query.edit || route.query.id
  if (!v) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
})

const isEdit = computed(() => !!editId.value)

const existingAttachments = ref([])
const files = ref([])

function revokePreviews() {
  files.value.forEach(f => {
    try { URL.revokeObjectURL(f.previewUrl) } catch (_) {}
  })
}

function removeFile(idx) {
  const item = files.value[idx]
  if (item?.previewUrl) {
    try { URL.revokeObjectURL(item.previewUrl) } catch (_) {}
  }
  files.value.splice(idx, 1)
}

function onFilesChange(e) {
  const list = Array.from(e.target.files || [])
  e.target.value = ''

  const imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
  const videoExts = ['.mp4', '.webm', '.ogg', '.mov']
  const maxImage = 5 * 1024 * 1024
  const maxVideo = 50 * 1024 * 1024

  const next = []
  const rejected = []

  for (const f of list) {
    const name = (f.name || '').toLowerCase()
    const ext = name.includes('.') ? name.slice(name.lastIndexOf('.')) : ''
    const type = (f.type || '').toLowerCase()

    const isImage = imageExts.includes(ext) && type.startsWith('image/')
    const isVideo = videoExts.includes(ext) && type.startsWith('video/')

    if (!isImage && !isVideo) {
      rejected.push(`${f.name}（格式不支持）`)
      continue
    }
    if (isImage && f.size > maxImage) {
      rejected.push(`${f.name}（图片超过5MB）`)
      continue
    }
    if (isVideo && f.size > maxVideo) {
      rejected.push(`${f.name}（视频超过50MB）`)
      continue
    }

    next.push({
      file: f,
      previewType: isImage ? 'image' : 'video',
      previewUrl: URL.createObjectURL(f)
    })
  }

  if (rejected.length) {
    alert('以下文件已被忽略：\n' + rejected.join('\n'))
  }

  files.value.push(...next)
}

async function fetchTicketForEdit() {
  if (!editId.value) return
  const res = await axios.get(apiUrl(`tickets/${editId.value}/`), {
    headers: { Authorization: `Token ${auth.token}` }
  })
  const t = res.data
  if (t.status !== 'rejected') {
    alert('仅可修改被驳回的工单')
    router.push('/tickets')
    return
  }
  form.value.title = t.title || ''
  form.value.location = t.location || ''
  form.value.category = t.category || ''
  form.value.priority = t.priority || '中'
  form.value.description = t.description || ''
  form.value.contact = t.contact || ''
  existingAttachments.value = Array.isArray(t.attachments) ? t.attachments : []
}

async function uploadAllAttachments(ticketId) {
  if (!files.value.length) return
  for (const item of files.value) {
    const fd = new FormData()
    fd.append('file', item.file)
    await axios.post(apiUrl(`tickets/${ticketId}/attachments/`), fd, {
      headers: { Authorization: `Token ${auth.token}` }
    })
  }
}

onMounted(async () => {
  if (!auth.isLoggedIn) return
  if (isEdit.value) {
    await fetchTicketForEdit()
  } else if (route.query.from_ai) {
    const aiDataStr = sessionStorage.getItem('ai_ticket_data')
    if (aiDataStr) {
      try {
        const aiData = JSON.parse(aiDataStr)
        form.value.title = aiData.title || ''
        form.value.category = aiData.category || ''
        form.value.description = aiData.description || ''
        form.value.priority = aiData.priority || '中'
        sessionStorage.removeItem('ai_ticket_data')
      } catch (e) {}
    }
  }
})

async function submitTicket() {
  if (!auth.isLoggedIn) {
    if(confirm("请先登录才能提交报修！\n是否去登录？")) {
        router.push('/login')
    }
    return
  }
  if (!auth.currentUser?.is_identity_bound) {
    if(confirm("您是新用户，请先绑定身份信息（学号/工号）才能报修。\n是否现在去绑定？")) {
        router.push('/bind')
    }
    return
  }
  loading.value = true
  try {
    const payload = {
      title: form.value.title,
      category: form.value.category,
      priority: form.value.priority,
      description: form.value.description,
      location: form.value.location,
      contact: form.value.contact
    }

    if (isEdit.value) {
      await axios.patch(apiUrl(`tickets/${editId.value}/`), payload, {
        headers: { Authorization: `Token ${auth.token}` }
      })
      await uploadAllAttachments(editId.value)
      alert("修改成功，已重新提交审核！")
      router.push('/tickets')
      return
    }

    const res = await axios.post(apiUrl('tickets/'), payload, { 
      headers: { Authorization: `Token ${auth.token}` } 
    })
    const createdId = res.data?.id
    if (createdId) {
      await uploadAllAttachments(createdId)
    }
    
    // alert("报修成功！")
    router.push('/tickets')
  } catch (e) {
    console.error(e.response?.data)
    // alert("提交失败：" + JSON.stringify(e.response?.data))
  } finally {
    loading.value = false
    revokePreviews()
    files.value = []
  }
}
</script>

<style scoped>
.page-content { padding: 20px; max-width: var(--app-page-max-width); margin: 0 auto; }
.form-card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
.form-group { margin-bottom: 20px; }
.form-row { display: flex; gap: 20px; }
.half { flex: 1; }
.form-group label { display: block; margin-bottom: 8px; font-weight: bold; color: #333; }
.form-group input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; box-sizing: border-box; }
.upload-hint { margin-top: 8px; font-size: 12px; color: #666; }
.preview-grid { margin-top: 12px; display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.preview-item { border: 1px solid #eee; border-radius: 8px; padding: 10px; background: #fafafa; display: flex; flex-direction: column; gap: 8px; }
.preview-item img, .preview-item video { width: 100%; border-radius: 6px; background: #000; }
.file-name { font-size: 12px; color: #444; word-break: break-all; }
.btn-remove { align-self: flex-end; background: none; border: none; color: #ef4444; cursor: pointer; font-size: 12px; text-decoration: underline; }
.existing-title { font-size: 13px; font-weight: 700; color: #333; margin-top: 6px; }
.btn-primary { width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 10px;}
.btn-primary:disabled { background: #ccc; }
@media (max-width: 480px) {
  .form-card { padding: 20px; }
  .form-row { flex-direction: column; }
}
</style>
