<!--
文件：src/views/OAApproval.vue
类型：页面组件
说明：
- 该文件为前端业务模块，实现页面渲染、交互与接口调用
- 主要逻辑在 <script setup> 中（状态、事件、请求、路由跳转等）
涉及接口：tickets/
-->

<template>
  <div class="approval-page">
    <section class="hero-section">
      <div class="hero-overlay">
        <div class="hero-main">
          <div class="hero-text">
            <h1>报修审核中心</h1>
            <p class="hero-desc">审核员 / 管理员可以在此对学生提交的报修进行审核、驳回与流转派单。</p>
            <div class="hero-actions">
              <button class="btn-primary" @click="fetchList">刷新列表</button>
              <div class="stat-badge">待审核：{{ list.length }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-header">
        <h2>待审核工单</h2>
        <p>当前状态：待审核员审核</p>
      </div>

      <div v-if="list.length === 0" class="empty">
        当前没有需要审核的报修工单。
      </div>

      <div v-else class="oa-grid">
        <div v-for="item in list" :key="item.id" class="oa-card">
          <div class="card-header">
            <div class="card-title">{{ item.title }}</div>
            <div class="card-id">#{{ item.id }}</div>
          </div>
          <div class="card-meta">
            <span>报修人：{{ item.submitter_name || '学生' }}</span>
            <span v-if="item.location">地点：{{ item.location }}</span>
          </div>
          <div class="card-body">
            <div v-if="isAiFlagged(item)" class="ai-flag">
              <div class="ai-flag-title">AI 标记：疑似不匹配（需人工确认）</div>
              <div class="ai-flag-text" v-if="item.ai_auto_reason">{{ item.ai_auto_reason }}</div>
              <div class="ai-flag-text" v-if="item.ai_suggested_category">AI 建议类别：{{ item.ai_suggested_category }}</div>
            </div>
            <div class="kv">
              <span class="k">类别</span>
              <span class="v">{{ item.category }}</span>
            </div>
            <div class="kv">
              <span class="k">优先级</span>
              <span class="v">{{ item.priority }}</span>
            </div>
            <div v-if="isOverdue(item)" class="overdue">⏰ 已超时（超过24小时未处理）</div>
            <div class="desc">{{ item.description || '未填写详细描述' }}</div>
          </div>
          <div class="card-actions">
            <button @click="review(item.id, 'approve')" class="btn-ok">通过并去派单</button>
            <button @click="openReject(item.id)" class="btn-no">驳回</button>
          </div>
        </div>
      </div>
    </section>

    <div v-if="rejectModal.open" class="modal-mask" @click.self="closeReject">
      <div class="modal">
        <div class="modal-title">填写驳回理由</div>
        <textarea v-model="rejectModal.reason" rows="4" placeholder="请输入驳回原因（学生将看到该内容）"></textarea>
        <div class="modal-actions">
          <button class="btn-cancel" @click="closeReject">取消</button>
          <button class="btn-confirm" @click="confirmReject" :disabled="rejectModal.submitting">
            {{ rejectModal.submitting ? '提交中...' : '确认驳回' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { apiUrl } from '@/config'

const auth = useAuthStore()
const router = useRouter()
const list = ref([])
const rejectModal = ref({ open: false, ticketId: null, reason: '', submitting: false })
let intervalId = null
let lastCount = 0
let lastOverdueKey = ''
let lastAiFlagKey = ''

async function fetchList() {
  const res = await axios.get(apiUrl('tickets/'), {
    headers: { Authorization: `Token ${auth.token}` },
    params: { status: 'pending_dorm' }
  })
  list.value = res.data
}

function isOverdue(t) {
  const now = Date.now()
  const submit = t.submitTime ? new Date(t.submitTime).getTime() : now
  const update = t.updateTime ? new Date(t.updateTime).getTime() : submit
  return (now - update) / 60000 > 24 * 60
}

function isAiFlagged(t) {
  return !!t?.ai_auto_checked_at && t?.ai_auto_approved === false
}

function getAiFlaggedList() {
  return (list.value || []).filter(isAiFlagged)
}

function getOverdueList() {
  return (list.value || []).filter(isOverdue)
}

onMounted(async () => {
  await fetchList()
  lastCount = list.value.length

  intervalId = setInterval(async () => {
    await fetchList()

    if (list.value.length > lastCount) {
      alert('📢 提醒：有新的报修工单等待审核！')
    }
    lastCount = list.value.length

    const overdue = getOverdueList()
    const key = overdue.map(t => t.id).join(',')
    if (key && key !== lastOverdueKey) {
      alert(`⏰ 超时提醒：有 ${overdue.length} 个待审核工单已超时，请尽快处理`)
    }
    lastOverdueKey = key

    const aiFlagged = getAiFlaggedList()
    const aiKey = aiFlagged.map(t => t.id).join(',')
    if (aiKey && aiKey !== lastAiFlagKey) {
      alert(`🤖 AI 审核提醒：有 ${aiFlagged.length} 个工单被 AI 标记为疑似不匹配，请人工确认`)
    }
    lastAiFlagKey = aiKey
  }, 15000)
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})

async function review(id, decision) {
  await axios.post(
    apiUrl(`tickets/${id}/review/`),
    { decision },
    { headers: { Authorization: `Token ${auth.token}` } }
  )
  // alert('操作成功')
  list.value = list.value.filter(i => i.id !== id)
  if (decision === 'approve') {
    router.push('/workplace')
  }
}

function openReject(id) {
  rejectModal.value.open = true
  rejectModal.value.ticketId = id
  rejectModal.value.reason = ''
  rejectModal.value.submitting = false
}

function closeReject() {
  rejectModal.value.open = false
  rejectModal.value.ticketId = null
  rejectModal.value.reason = ''
  rejectModal.value.submitting = false
}

async function confirmReject() {
  if (!rejectModal.value.ticketId) return
  rejectModal.value.submitting = true
  try {
    await axios.post(
      apiUrl(`tickets/${rejectModal.value.ticketId}/review/`),
      { decision: 'reject', reason: rejectModal.value.reason },
      { headers: { Authorization: `Token ${auth.token}` } }
    )
    // alert('操作成功')
    list.value = list.value.filter(i => i.id !== rejectModal.value.ticketId)
    closeReject()
  } catch (e) {
    // alert('驳回失败')
    rejectModal.value.submitting = false
  }
}
</script>

<style scoped>
.approval-page {
  background: #f6f3f7;
  min-height: calc(100vh - 60px);
}

.hero-section {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.hero-overlay {
  padding: 28px 16px;
}

.hero-main {
  max-width: var(--app-page-max-width);
  margin: 0 auto;
}

.hero-text h1 {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.hero-desc {
  margin: 0 0 16px;
  opacity: 0.95;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.btn-primary {
  background: white;
  color: #5a4aa2;
  border: none;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 700;
}

.stat-badge {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.25);
  font-weight: 700;
}

.section {
  max-width: var(--app-page-max-width);
  margin: 0 auto;
  padding: 18px 16px 28px;
}

.section-header h2 {
  margin: 0 0 6px;
  color: #1e293b;
  font-size: 20px;
  font-weight: 800;
}

.section-header p {
  margin: 0 0 16px;
  color: #64748b;
  font-size: 14px;
}

.overdue {
  margin-top: 10px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fff7e6;
  color: #fa8c16;
  font-weight: 700;
  font-size: 13px;
}

.ai-flag {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #ffd1dc;
  background: #fff3f6;
  color: #b42318;
}

.ai-flag-title {
  font-weight: 800;
  font-size: 13px;
  margin-bottom: 6px;
}

.ai-flag-text {
  font-size: 13px;
  line-height: 1.5;
}

.empty {
  padding: 48px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
  background: white;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
}

.oa-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.oa-card {
  background: white;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.06);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.card-title {
  font-weight: 800;
  color: #0f172a;
  line-height: 1.25;
}

.card-id {
  color: #64748b;
  font-weight: 700;
  font-size: 12px;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: #64748b;
  font-size: 13px;
}

.card-body {
  color: #334155;
  font-size: 13px;
  line-height: 1.7;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kv {
  display: flex;
  gap: 8px;
  align-items: center;
}

.k {
  color: #64748b;
  min-width: 48px;
}

.v {
  color: #334155;
  font-weight: 700;
}

.desc {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  color: #334155;
}

.card-actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}

.btn-ok {
  flex: 1;
  background: #16a34a;
  color: white;
  border: none;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 800;
}

.btn-no {
  background: #ef4444;
  color: white;
  border: none;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 800;
}

.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 200;
}

.modal {
  width: 100%;
  max-width: 520px;
  background: white;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 30px 60px rgba(15, 23, 42, 0.25);
  padding: 16px;
}

.modal-title {
  font-size: 16px;
  font-weight: 900;
  color: #0f172a;
  margin-bottom: 10px;
}

.modal textarea {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px;
  box-sizing: border-box;
  font-size: 14px;
  resize: vertical;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}

.btn-cancel {
  background: #e2e8f0;
  border: none;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 800;
  color: #334155;
}

.btn-confirm {
  background: #ef4444;
  border: none;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  font-weight: 900;
  color: white;
}

.btn-confirm:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

@media (max-width: 860px) {
  .oa-grid {
    grid-template-columns: 1fr;
  }
}
</style>
