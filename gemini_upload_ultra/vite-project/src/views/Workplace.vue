<!--
文件：src/views/Workplace.vue
类型：页面组件
说明：
- 该文件为前端业务模块，实现页面渲染、交互与接口调用
- 主要逻辑在 <script setup> 中（状态、事件、请求、路由跳转等）
涉及接口：maintenance-users/、me/、tickets/
-->

<template>
  <div class="workspace-container">
    <div class="page-header">
      <h2 v-if="isDispatcher">📌 派单工作台</h2>
      <h2 v-else>🛠️ 维修师傅工作台</h2>
      <p>欢迎回来，{{ auth.currentUser?.name || auth.currentUser?.username }}</p>
      <p v-if="!isDispatcher && auth.currentUser?.maintenance_info?.department">部门/工种：{{ auth.currentUser.maintenance_info.department }}</p>
      <div v-if="!isDispatcher" class="profile-row">
        <select v-model="maintenanceForm.department">
          <option value="">请选择工种（必填）</option>
          <option value="水电">水电</option>
          <option value="强电">强电</option>
          <option value="网络">网络</option>
          <option value="其他">其他</option>
        </select>
        <input v-model="maintenanceForm.contact_phone" placeholder="联系电话（必填）" />
        <button class="btn-save" type="button" @click="saveMaintenanceInfo">保存</button>
      </div>
      <div v-if="isDispatcher && auth.currentUser?.role === 'auditor'" class="profile-row">
        <input v-model="auditorForm.contact_phone" placeholder="审核员联系电话（必填）" />
        <button class="btn-save" type="button" @click="saveAuditorInfo">保存</button>
      </div>
    </div>

    <div class="search-box">
      <input 
        v-model="searchText" 
        type="text" 
        placeholder="🔍 搜索工单号、位置、描述..." 
        @keyup.enter="fetchData"
      />
      <button @click="fetchData" class="btn-search">搜索</button>
    </div>

    <div class="section" v-if="isDispatcher">
      <h3 class="section-title">📢 待派单工单</h3>
      <div v-if="pendingTickets.length === 0" class="empty-box">暂无待派单工单</div>
      <div v-else class="task-grid">
        <div v-for="t in pendingTickets" :key="t.id" class="task-card pending">
          <div class="card-top">
            <span class="tag">待派单</span>
            <span class="time">{{ formatDate(t.submitTime) }}</span>
          </div>
          <h4>{{ t.title }}</h4>
          <p class="ai-suggest">AI建议师傅：{{ suggestWorkerLabel(t) }}</p>
          <p v-if="isOverdue(t)" class="overdue">⏰ 已超时，请优先处理</p>
          <p class="desc">{{ t.description }}</p>
          <p class="loc"><i class="fas fa-map-marker-alt"></i> {{ t.location }}</p>

          <div class="dispatch-row">
            <select v-model="dispatchTo[t.id]" class="dispatch-select">
              <option value="">请选择维修人员</option>
              <option v-for="w in maintenanceUsers" :key="w.id" :value="w.id">
                {{ w.name }}{{ w.department ? `（${w.department}）` : '' }}{{ w.identity_id ? ` ${w.identity_id}` : '' }}
              </option>
            </select>
            <button @click="dispatchTicket(t.id)" class="btn-dispatch">派单</button>
            <button @click="rejectTicket(t.id)" class="btn-reject">驳回</button>
          </div>
        </div>
      </div>
    </div>

    <div class="section" v-if="!isDispatcher">
      <h3 class="section-title">📌 待开始维修</h3>
      <div v-if="myAssignedTickets.length === 0" class="empty-box">暂无待开始的任务</div>
      <div class="task-grid">
        <div v-for="t in myAssignedTickets" :key="t.id" class="task-card pending">
          <div class="card-top">
            <span class="tag">已派单</span>
            <span class="assignee">负责人: 我</span>
          </div>
          <h4>{{ t.title }}</h4>
          <p class="student"><i class="fas fa-user"></i> 学号：{{ t.submitter_identity_id || t.submitter_name || '未绑定' }}</p>
          <p class="loc"><i class="fas fa-map-marker-alt"></i> {{ t.location }}</p>
          <p class="contact"><i class="fas fa-phone"></i> {{ t.contact }}</p>
          <p v-if="isOverdue(t)" class="overdue">⏰ 已超时，请尽快开始维修</p>
          <div class="action-row">
            <button @click="startRepair(t.id)" class="btn-start">🛠️ 开始维修</button>
            <button @click="returnTicket(t.id)" class="btn-return">🔙 退回重派</button>
          </div>
        </div>
      </div>
    </div>

    <div class="section" v-if="!isDispatcher">
      <h3 class="section-title">🔧 我的维修任务</h3>
      <div v-if="myRepairingTickets.length === 0" class="empty-box">您当前没有正在进行的维修</div>
      <div class="task-grid">
        <div v-for="t in myRepairingTickets" :key="t.id" class="task-card repairing">
          <div class="card-top">
            <span class="tag blue">维修中</span>
            <span class="assignee">负责人: 我</span>
          </div>
          <h4>{{ t.title }}</h4>
          <p class="student"><i class="fas fa-user"></i> 学号：{{ t.submitter_identity_id || t.submitter_name || '未绑定' }}</p>
          <p class="loc"><i class="fas fa-map-marker-alt"></i> {{ t.location }}</p>
          <p class="contact"><i class="fas fa-phone"></i> {{ t.contact }}</p>
          <p v-if="isOverdue(t)" class="overdue">⏰ 已超时，请尽快完成</p>
          <button @click="openFinishModal(t.id)" class="btn-finish">✅ 维修完成</button>
        </div>
      </div>
    </div>

    <div class="section" v-if="!isDispatcher">
      <h3 class="section-title">🕒 待评价工单（已完成）</h3>
      <div v-if="myFinishedTickets.length === 0" class="empty-box">暂无待评价工单</div>
      <div class="task-grid">
        <div v-for="t in myFinishedTickets" :key="t.id" class="task-card finished">
          <div class="card-top">
            <span class="tag green">待评价</span>
            <span class="assignee">负责人: 我</span>
          </div>
          <h4>{{ t.title }}</h4>
          <p class="loc"><i class="fas fa-map-marker-alt"></i> {{ t.location }}</p>
          <p class="contact"><i class="fas fa-phone"></i> {{ t.contact }}</p>
          <div class="hint">等待学生评价后自动结单</div>
          <button class="btn-sheet" type="button" @click="openSheet(t.id)">生成报修单</button>
        </div>
      </div>
    </div>

    <div class="section" v-if="!isDispatcher">
      <h3 class="section-title">⭐ 已结单工单（含评价）</h3>
      <div v-if="myClosedTickets.length === 0" class="empty-box">暂无已结单工单</div>
      <div class="task-grid">
        <div v-for="t in myClosedTickets" :key="t.id" class="task-card closed">
          <div class="card-top">
            <span class="tag gray">已结单</span>
            <span class="assignee">负责人: 我</span>
          </div>
          <h4>{{ t.title }}</h4>
          <p class="loc"><i class="fas fa-map-marker-alt"></i> {{ t.location }}</p>
          <p class="score" v-if="t.rating !== undefined && t.rating !== null">评分：{{ t.rating }}/5</p>
          <p class="eval" v-if="t.evaluation">{{ t.evaluation }}</p>
          <p class="eval empty" v-else>无评价内容</p>
          <button class="btn-sheet" type="button" @click="openSheet(t.id)">生成报修单</button>
        </div>
      </div>
    </div>
    <div v-if="finishModal.open" class="modal-mask" @click.self="finishModal.open = false">
      <div class="modal">
        <div class="modal-title">填写维修完成信息</div>
        <div class="field">
          <label>维修结果/说明</label>
          <textarea v-model="finishModal.repair_result" rows="3" placeholder="简要说明维修情况..."></textarea>
        </div>
        <div class="field">
          <label>使用耗材明细</label>
          <textarea v-model="finishModal.materials_used" rows="2" placeholder="例如：水管50米、水龙头1个"></textarea>
        </div>
        <div class="field">
          <label>维修完成照片/视频（建议上传）</label>
          <input type="file" multiple accept="image/*,video/*" @change="onFinishFilesChange" />
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="finishModal.open = false">取消</button>
          <button class="btn-confirm" @click="submitFinish">确认完成</button>
        </div>
      </div>
    </div>

    <div v-if="reimburseModal.open" class="modal-mask" @click.self="closeReimburse">
      <div class="modal">
        <div class="modal-title">报修单（已生成）</div>
        <div class="field">
          <label>报修单号</label>
          <input :value="reimburseModal.no" readonly />
        </div>
        <div class="field">
          <label>报修单内容</label>
          <textarea :value="reimburseModal.text" rows="10" readonly></textarea>
        </div>
        <div class="modal-actions">
          <button class="btn-cancel" type="button" @click="copyReimburse">复制内容</button>
          <button class="btn-confirm" type="button" @click="downloadReimburseTxt">生成报修单</button>
          <button class="btn-cancel" type="button" @click="closeReimburse">关闭</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { apiUrl } from '@/config'

const auth = useAuthStore()
const allTickets = ref([])
const searchText = ref('') // 搜索变量
const maintenanceUsers = ref([])
const dispatchTo = ref({})

const finishModal = ref({ open: false, ticketId: null, repair_result: '', materials_used: '', files: [] })
const reimburseModal = ref({ open: false, no: '', text: '' })
const maintenanceForm = ref({ department: '', contact_phone: '' })
const auditorForm = ref({ contact_phone: '' })

let intervalId = null
let lastAssignedCount = 0
let lastPendingCount = 0
let lastOverdueKey = ''

const isDispatcher = computed(() => ['admin', 'auditor'].includes(auth.currentUser?.role))

const pendingTickets = computed(() => allTickets.value.filter(t => t.status === 'pending_dispatch' && !t.assignee))
const myAssignedTickets = computed(() => allTickets.value.filter(t => t.status === 'pending_repair' && t.assignee === auth.currentUser?.id))
const myRepairingTickets = computed(() => allTickets.value.filter(t => t.status === 'repairing' && t.assignee === auth.currentUser?.id))
const myFinishedTickets = computed(() => allTickets.value.filter(t => t.status === 'finished' && t.assignee === auth.currentUser?.id))
const myClosedTickets = computed(() => allTickets.value.filter(t => t.status === 'closed' && t.assignee === auth.currentUser?.id))

onMounted(async () => {
  await fetchData()
  
  if (!isDispatcher.value) lastAssignedCount = myAssignedTickets.value.length
  else lastPendingCount = pendingTickets.value.length

  // 定时轮询，每15秒刷新一次，检查是否有新任务
  intervalId = setInterval(async () => {
    await fetchData()
    if (!isDispatcher.value) {
      if (myAssignedTickets.value.length > lastAssignedCount) {
        alert('📢 提醒：您有新的派单任务，请注意查看！')
      }
      lastAssignedCount = myAssignedTickets.value.length
    } else {
      if (pendingTickets.value.length > lastPendingCount) {
        alert('📢 提醒：有新的报修工单等待派单！')
      }
      lastPendingCount = pendingTickets.value.length
    }

    const overdue = getOverdueTickets()
    const key = overdue.map(t => t.id).join(',')
    if (key && key !== lastOverdueKey) {
      alert(`⏰ 超时提醒：有 ${overdue.length} 个工单已超时，请尽快处理`)
    }
    lastOverdueKey = key
  }, 15000)
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
})

watch(
  () => isDispatcher.value,
  async (val) => {
    if (val) {
      await fetchMaintenanceUsers()
    }
  },
  { immediate: true }
)

watch(
  () => auth.currentUser,
  (u) => {
    if (!u || isDispatcher.value) return
    maintenanceForm.value.department = u?.maintenance_info?.department || ''
    maintenanceForm.value.contact_phone = u?.maintenance_info?.contact_phone || ''
  },
  { immediate: true }
)

watch(
  () => auth.currentUser,
  (u) => {
    if (!u || !isDispatcher.value) return
    if (u?.role !== 'auditor') return
    auditorForm.value.contact_phone = u?.contact_phone || ''
  },
  { immediate: true }
)

async function fetchData() {
  try {
    // 搜索参数传给后端
    const res = await axios.get(apiUrl('tickets/'), {
       headers: { Authorization: `Token ${auth.token}` },
       params: { search: searchText.value } 
    })
    allTickets.value = res.data
    if (isDispatcher.value) {
      if (!maintenanceUsers.value.length) {
        await fetchMaintenanceUsers()
      }
      for (const t of pendingTickets.value) {
        if (!dispatchTo.value[t.id]) {
          const wid = pickWorkerId(t)
          if (wid) dispatchTo.value[t.id] = wid
        }
      }
    }
  } catch (e) {
    console.error(e)
  }
}

async function fetchMaintenanceUsers() {
  try {
    const res = await axios.get(apiUrl('maintenance-users/'), {
      headers: { Authorization: `Token ${auth.token}` }
    })
    maintenanceUsers.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    maintenanceUsers.value = []
  }
}

function suggestCategory(t) {
  const text = `${t.title || ''} ${t.description || ''} ${t.location || ''}`.toLowerCase()
  if (['wifi', 'wi-fi', '网络', '上网', '断网', '路由', '宽带'].some(k => text.includes(k))) return '网络连接'
  if (['水', '漏水', '水龙头', '下水', '电', '灯', '跳闸', '插座', '电闸', '开关'].some(k => text.includes(k))) return '水电问题'
  if (['空调', '冰箱', '洗衣机', '热水器', '风扇', '设备', '电器'].some(k => text.includes(k))) return '设备故障'
  if (['柜', '衣柜', '桌', '椅', '床'].some(k => text.includes(k))) return '柜子损坏'
  if (['门', '窗', '锁', '玻璃'].some(k => text.includes(k))) return '门窗损坏'
  return t.category || '其他'
}

function suggestWorkerLabel(t) {
  const id = dispatchTo.value?.[t.id] || pickWorkerId(t)
  if (!id) return '请手动选择'
  const w = (maintenanceUsers.value || []).find(u => u.id === id)
  if (!w) return '请手动选择'
  return `${w.name || '维修人员'}${w.department ? `（${w.department}）` : ''}`
}

function isOverdue(t) {
  const now = Date.now()
  const submit = t.submitTime ? new Date(t.submitTime).getTime() : now
  const update = t.updateTime ? new Date(t.updateTime).getTime() : submit
  const mins = (now - update) / 60000
  if (t.status === 'pending_dispatch') return mins > 24 * 60
  if (t.status === 'pending_repair') return mins > 24 * 60
  if (t.status === 'repairing') {
    return mins > 24 * 60
  }
  return false
}

function getOverdueTickets() {
  const list = isDispatcher.value
    ? [...pendingTickets.value, ...allTickets.value.filter(t => t.status === 'pending_dorm')]
    : [...myAssignedTickets.value, ...myRepairingTickets.value]
  return list.filter(isOverdue)
}

function pickWorkerId(t) {
  const cat = suggestCategory(t)
  const workers = maintenanceUsers.value || []
  const depOf = (w) => String(w.department || '').trim()

  if (cat === '网络连接') {
    const first = workers.find(w => depOf(w) === '网络')
    return first?.id || workers[0]?.id || null
  }

  if (cat === '水电问题') {
    const first = workers.find(w => depOf(w) === '水电') || workers.find(w => depOf(w) === '强电')
    return first?.id || workers[0]?.id || null
  }

  const first = workers.find(w => depOf(w) === '其他')
  return first?.id || workers[0]?.id || null
}

async function saveMaintenanceInfo() {
  if (!maintenanceForm.value.department?.trim()) {
    alert('请先填写工种')
    return
  }
  if (!maintenanceForm.value.contact_phone?.trim()) {
    alert('请先填写联系电话')
    return
  }
  try {
    await axios.patch(apiUrl('me/'), {
      department: maintenanceForm.value.department,
      contact_phone: maintenanceForm.value.contact_phone
    }, {
      headers: { Authorization: `Token ${auth.token}` }
    })
    await auth.fetchUser()
    alert('已保存')
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function saveAuditorInfo() {
  if (!auditorForm.value.contact_phone?.trim()) {
    alert('请先填写联系电话')
    return
  }
  try {
    await axios.patch(apiUrl('me/'), {
      contact_phone: auditorForm.value.contact_phone
    }, {
      headers: { Authorization: `Token ${auth.token}` }
    })
    await auth.fetchUser()
    alert('已保存')
  } catch (e) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function dispatchTicket(ticketId) {
  const workerId = dispatchTo.value?.[ticketId]
  if (!workerId) {
    alert('请选择维修人员')
    return
  }
  try {
    await axios.post(apiUrl(`tickets/${ticketId}/handle/`), {
      type: 'assign',
      worker_id: workerId
    }, { headers: { Authorization: `Token ${auth.token}` } })
    await fetchData()
  } catch (e) {
    alert(e.response?.data?.detail || '派单失败')
  }
}

async function returnTicket(ticketId) {
  if(!confirm("确定要退回给审核员重新派单吗？")) return;
  try {
    await axios.post(apiUrl(`tickets/${ticketId}/handle/`), {
      type: 'return'
    }, { headers: { Authorization: `Token ${auth.token}` } })
    fetchData()
  } catch (e) { 
    alert(e.response?.data?.detail || "退回失败") 
  }
}

async function rejectTicket(ticketId) {
  const input = prompt('请输入驳回原因')
  if (input === null) return
  const reason = (input || '').trim()
  try {
    await axios.post(apiUrl(`tickets/${ticketId}/review/`), {
      decision: 'reject',
      reason,
    }, { headers: { Authorization: `Token ${auth.token}` } })
    await fetchData()
    alert('已驳回')
  } catch (e) {
    alert(e.response?.data?.detail || '驳回失败')
  }
}

function openFinishModal(id) {
  finishModal.value = { open: true, ticketId: id, repair_result: '', materials_used: '', files: [] }
}

function onFinishFilesChange(e) {
  const list = Array.from(e.target.files || [])
  e.target.value = ''
  finishModal.value.files = list
}

async function submitFinish() {
  const { ticketId, repair_result, materials_used, files } = finishModal.value
  try {
    const res = await axios.post(apiUrl(`tickets/${ticketId}/handle/`), {
      type: 'finish',
      repair_result,
      materials_used,
    }, { headers: { Authorization: `Token ${auth.token}` } })

    for (const f of (files || [])) {
      const fd = new FormData()
      fd.append('file', f)
      await axios.post(apiUrl(`tickets/${ticketId}/attachments/`), fd, {
        headers: { Authorization: `Token ${auth.token}` }
      })
    }

    finishModal.value.open = false
    reimburseModal.value.open = true
    reimburseModal.value.no = res.data?.reimbursement_no || ''
    reimburseModal.value.text = res.data?.reimbursement_text || ''
    fetchData()
  } catch (e) { 
    alert(e.response?.data?.detail || "操作失败")
  }
}

async function openSheet(ticketId) {
  try {
    const res = await axios.post(apiUrl(`tickets/${ticketId}/handle/`), {
      type: 'sheet',
    }, { headers: { Authorization: `Token ${auth.token}` } })
    reimburseModal.value.open = true
    reimburseModal.value.no = res.data?.reimbursement_no || ''
    reimburseModal.value.text = res.data?.reimbursement_text || ''
  } catch (e) {
    alert(e.response?.data?.detail || '生成失败')
  }
}

function closeReimburse() {
  reimburseModal.value.open = false
  reimburseModal.value.no = ''
  reimburseModal.value.text = ''
}

async function copyReimburse() {
  try {
    await navigator.clipboard.writeText(reimburseModal.value.text || '')
    alert('已复制')
  } catch (e) {
    alert('复制失败，请手动选中复制')
  }
}

function downloadReimburseTxt() {
  const text = reimburseModal.value.text || ''
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const no = (reimburseModal.value.no || 'reimbursement').replace(/[^\w\-]/g, '_')
  a.download = `${no}.txt`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

async function startRepair(ticketId) {
  try {
    await axios.post(apiUrl(`tickets/${ticketId}/handle/`), {
      type: 'start'
    }, { headers: { Authorization: `Token ${auth.token}` } })
    fetchData()
  } catch (e) { /* alert("操作失败") */ }
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('zh-CN', {month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit'})
}
</script>

<style scoped>
.workspace-container { max-width: var(--app-page-max-width); margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.profile-row { margin-top: 10px; display: flex; gap: 10px; flex-wrap: wrap; }
.profile-row input, .profile-row select { flex: 1; min-width: 180px; padding: 8px 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 13px; background: white; }
.btn-save { padding: 8px 14px; background: #111827; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 800; }
.section { margin-bottom: 40px; }
.section-title { font-size: 18px; border-left: 5px solid #667eea; padding-left: 10px; margin-bottom: 20px; color: #333; }
.search-box { display: flex; gap: 10px; margin-bottom: 30px; max-width: 600px; }
.search-box input { flex: 1; padding: 10px 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
.btn-search { padding: 0 25px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
.task-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
.empty-box { background: #f9f9f9; padding: 20px; text-align: center; color: #999; border-radius: 8px; }
.task-card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #eee; display: flex; flex-direction: column; }
.task-card.pending { border-top: 4px solid #f39c12; }
.task-card.repairing { border-top: 4px solid #3498db; }
.task-card.finished { border-top: 4px solid #2ecc71; }
.task-card.closed { border-top: 4px solid #9ca3af; }
.card-top { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 12px; color: #888; }
.tag { background: #f39c12; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
.tag.blue { background: #3498db; }
.tag.green { background: #2ecc71; }
.tag.gray { background: #9ca3af; }
h4 { margin: 0 0 10px 0; font-size: 16px; color: #333; }
.ai-suggest { margin: -6px 0 10px; font-size: 12px; color: #2563eb; font-weight: 800; }
.overdue { margin: -6px 0 10px; font-size: 12px; color: #dc2626; font-weight: 900; }
.desc { color: #666; font-size: 14px; margin-bottom: 10px; flex: 1; }
.loc, .contact { font-size: 13px; color: #555; margin: 5px 0; }
.contact { color: #e74c3c; font-weight: bold; }
.student { font-size: 13px; color: #555; margin: 5px 0; }
.hint { margin-top: 10px; font-size: 12px; color: #6b7280; }
.score { margin: 8px 0 6px; font-size: 13px; color: #374151; font-weight: 700; }
.eval { margin: 0; font-size: 13px; color: #4b5563; line-height: 1.5; }
.eval.empty { color: #9ca3af; }
.btn-take { margin-top: 15px; width: 100%; padding: 10px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; transition: background 0.2s;}
.btn-finish { margin-top: 15px; width: 100%; padding: 10px; background: #2ecc71; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.btn-start { margin-top: 15px; width: 100%; padding: 10px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.btn-return { margin-top: 15px; width: 100%; padding: 10px; background: #e74c3c; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.btn-sheet { margin-top: 12px; width: 100%; padding: 10px; background: #111827; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 800; }
.btn-dispatch { padding: 10px 14px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 900; }
.btn-reject { padding: 10px 14px; background: #b91c1c; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 900; }

.action-row { display: flex; gap: 10px; }

.dispatch-row { display: flex; gap: 10px; margin-top: 12px; }
.dispatch-select { flex: 1; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; background: white; }
.btn-dispatch { width: 92px; padding: 10px; background: #667eea; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; }
/* Modal Styles */
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 20px; }
.modal { background: white; width: 100%; max-width: 400px; border-radius: 12px; padding: 24px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
.modal-title { font-size: 18px; font-weight: bold; margin-bottom: 20px; color: #333; }
.field { margin-bottom: 15px; }
.field label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: bold; color: #555; }
.field textarea, .field input, .field select { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.btn-cancel { padding: 8px 16px; background: #f1f5f9; color: #475569; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
.btn-confirm { padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }

</style>
