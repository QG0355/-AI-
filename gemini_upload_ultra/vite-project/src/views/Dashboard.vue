<!--
文件：src/views/Dashboard.vue
类型：页面组件
说明：
- 该文件为前端业务模块，实现页面渲染、交互与接口调用
- 主要逻辑在 <script setup> 中（状态、事件、请求、路由跳转等）
涉及接口：tickets/
-->

<template>
  <div class="home-page">
    <section class="hero-section">
      <div class="hero-overlay">
        <div class="hero-main">
          <div class="hero-text">
            <h1>校园设备报修系统</h1>
            <p class="hero-en">Campus Facilities Repair Service</p>
            <p class="hero-desc">
              一站式在线报修平台，连接学生、审核员和维修师傅，让报修流程更加高效、透明、可追踪。
            </p>

            <div class="hero-actions">
              <template v-if="!authStore.isLoggedIn">
                <button class="btn-primary" @click="goLogin">
                  立即登录开始报修
                </button>
                <button class="btn-ghost" @click="goRegister">
                  注册新账号
                </button>
              </template>
              <template v-else>
                <button class="btn-primary" @click="handleMainBtnClick">
                  <i :class="mainActionIcon"></i>
                  {{ mainActionLabel }}
                </button>
                <button class="btn-ghost" @click="goTickets" v-if="isStudent">
                  <i class="fas fa-list"></i>
                  我的报修记录
                </button>
                <button class="btn-ghost" @click="$router.push('/approval')" v-if="['admin', 'auditor'].includes(authStore.currentUser?.role)">
                  <i class="fas fa-check-square"></i>
                  审核中心
                </button>
              </template>
            </div>

            <div class="hero-tips">
              <span class="tip-badge">提醒</span>
              <span>请使用真实联系方式和报修地点，便于维修师傅快速联系和上门服务。</span>
            </div>
          </div>

          <div class="hero-side">
            <div v-for="(s, idx) in heroStats" :key="idx" class="stat-card">
              <div class="stat-label">{{ s.label }}</div>
              <div class="stat-value">{{ s.value }}</div>
            </div>
            <p class="stat-note">以上数据为示意展示，可在后续按任务书要求接真实统计。</p>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-header">
        <h2>常用入口</h2>
        <p>根据不同角色，快速进入对应功能页面</p>
      </div>
      <div class="entry-grid">
        <div class="entry-card" @click="goSubmit" v-if="isStudent">
          <div class="entry-icon primary">
            <i class="fas fa-clipboard-list"></i>
          </div>
          <h3>提交报修</h3>
          <p>填写报修信息、上传故障描述，系统自动流转到相关老师和维修师傅。</p>
        </div>

        <div class="entry-card" @click="goTickets" v-if="isStudent">
          <div class="entry-icon">
            <i class="fas fa-history"></i>
          </div>
          <h3>我的报修</h3>
          <p>随时查看每一条报修的受理进度、派单情况和最终处理结果。</p>
        </div>

        <div class="entry-card" @click="goAi" v-if="isStudent">
          <div class="entry-icon warning">
            <i class="fas fa-robot"></i>
          </div>
          <h3>AI 报修助手</h3>
          <p>用自然语言咨询报修流程和注意事项，结果仅供参考，请以实际为准。</p>
        </div>
        
        <div class="entry-card" @click="$router.push('/workplace')" v-if="['maintenance', 'repair_admin', 'admin', 'auditor'].includes(authStore.currentUser?.role)">
          <div class="entry-icon primary">
            <i class="fas fa-briefcase"></i>
          </div>
          <h3>工作台</h3>
          <p>查看待办任务，进行派单、维修处理或任务管理。</p>
        </div>
        
        <div class="entry-card" @click="$router.push('/approval')" v-if="['admin', 'auditor'].includes(authStore.currentUser?.role)">
          <div class="entry-icon warning">
            <i class="fas fa-check-circle"></i>
          </div>
          <h3>审核中心</h3>
          <p>对新提交的报修申请进行审核、驳回或派单操作。</p>
        </div>
      </div>
    </section>

    <section class="section" v-if="showStarCarousel">
      <div class="section-header">
        <h2>优秀维修之星</h2>
        <p>展示优秀维修人员事迹（由管理员维护）</p>
      </div>
      <ServiceStarCarousel />
    </section>

    <section class="section gray">
      <div class="section-header">
        <h2>报修流程示意</h2>
        <p>整体流程清晰可追踪，方便答辩时说明系统设计思路</p>
      </div>
      <div class="flow-steps">
        <div class="flow-item">
          <div class="step-index">1</div>
          <h3>线上提交</h3>
          <p>学生登录系统，选择报修类别，填写详细故障描述和联系方式。</p>
        </div>
        <div class="flow-item">
          <div class="step-index">2</div>
          <h3>审核与派单</h3>
          <p>审核员或管理员在线审核，并将工单分配给对应维修师傅。</p>
        </div>
        <div class="flow-item">
          <div class="step-index">3</div>
          <h3>上门维修与评价</h3>
          <p>维修完成后，学生在系统中进行评价，为“优秀维修之星”提供数据支撑。</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import { computed, ref, onMounted, watch } from 'vue'
import ServiceStarCarousel from '@/components/ServiceStarCarousel.vue'
import axios from 'axios'
import { apiUrl, API_BASE_URL } from '@/config'

const authStore = useAuthStore()
const router = useRouter()

const isStudent = computed(() => {
  return authStore.currentUser?.role === 'student'
})

const showStarCarousel = computed(() => {
  // 服务之星对学生、维修员、审核员均可见
  const role = authStore.currentUser?.role
  return ['student', 'maintenance', 'auditor', 'repair_admin'].includes(role)
})

const mainActionLabel = computed(() => {
  const role = authStore.currentUser?.role
  if (role === 'student') return '我要报修'
  if (role === 'auditor') return '进入审核中心'
  if (role === 'admin') return '进入管理后台'
  return '进入工作台'
})

const mainActionIcon = computed(() => {
  const role = authStore.currentUser?.role
  if (role === 'student') return 'fas fa-wrench'
  if (role === 'auditor') return 'fas fa-check-square'
  if (role === 'admin') return 'fas fa-cogs'
  return 'fas fa-briefcase'
})

const statsData = ref({
  studentTotal: 0,
  studentProcessing: 0,
  studentClosed: 0,
  pendingReview: 0,
  pendingDispatch: 0,
  rejected: 0,
  todayClosed: 0,
  good: 0,
  bad: 0
})

const heroStats = computed(() => {
  const role = authStore.currentUser?.role
  if (role === 'maintenance') {
    return [
      { label: '今日已结单', value: statsData.value.todayClosed },
      { label: '好评', value: statsData.value.good },
      { label: '差评', value: statsData.value.bad }
    ]
  }
  if (role === 'auditor' || role === 'admin') {
    return [
      { label: '待审核', value: statsData.value.pendingReview },
      { label: '待派单', value: statsData.value.pendingDispatch },
      { label: '已驳回', value: statsData.value.rejected }
    ]
  }
  return [
    { label: '我的报修', value: statsData.value.studentTotal },
    { label: '处理中', value: statsData.value.studentProcessing },
    { label: '已结单', value: statsData.value.studentClosed }
  ]
})

async function fetchStats() {
  if (!authStore.isLoggedIn || !authStore.token || !authStore.currentUser?.role) return

  const role = authStore.currentUser.role
  const headers = { Authorization: `Token ${authStore.token}` }

  if (role === 'student') {
    const res = await axios.get(apiUrl('tickets/'), { headers })
    const tickets = Array.isArray(res.data) ? res.data : []
    const processingStatuses = ['pending_dorm', 'pending_dispatch', 'pending_repair', 'repairing', 'finished']
    statsData.value.studentTotal = tickets.length
    statsData.value.studentProcessing = tickets.filter(t => processingStatuses.includes(t.status)).length
    statsData.value.studentClosed = tickets.filter(t => t.status === 'closed').length
    return
  }

  if (role === 'maintenance') {
    const res = await axios.get(apiUrl('tickets/'), { headers })
    const tickets = Array.isArray(res.data) ? res.data : []
    const my = tickets.filter(t => t.assignee === authStore.currentUser?.id)
    const today = new Date()
    const isToday = (iso) => {
      if (!iso) return false
      const d = new Date(iso)
      return d.getFullYear() === today.getFullYear() && d.getMonth() === today.getMonth() && d.getDate() === today.getDate()
    }
    const closedToday = my.filter(t => t.status === 'closed' && isToday(t.updateTime))
    statsData.value.todayClosed = closedToday.length
    statsData.value.good = closedToday.filter(t => (t.rating || 0) >= 4).length
    statsData.value.bad = closedToday.filter(t => (t.rating || 0) <= 2).length
    return
  }

  if (role === 'auditor' || role === 'admin') {
    const [pendingRes, allRes] = await Promise.all([
      axios.get(apiUrl('tickets/'), { headers, params: { status: 'pending_dorm' } }),
      axios.get(apiUrl('tickets/'), { headers })
    ])
    const pending = Array.isArray(pendingRes.data) ? pendingRes.data : []
    const all = Array.isArray(allRes.data) ? allRes.data : []
    statsData.value.pendingReview = pending.length
    statsData.value.pendingDispatch = all.filter(t => ['pending_dispatch', 'pending_repair'].includes(t.status)).length
    statsData.value.rejected = all.filter(t => t.status === 'rejected').length
  }
}

onMounted(() => {
  fetchStats()
})

watch(
  () => authStore.currentUser?.role,
  () => {
    fetchStats()
  }
)

function handleMainBtnClick() {
  const role = authStore.currentUser?.role
  if (role === 'student') {
    if (!authStore.currentUser?.is_identity_bound) {
      if (confirm('您尚未绑定身份信息，绑定后即可报修。\n是否现在去绑定？')) {
        router.push('/bind')
      }
    } else {
      router.push('/submit')
    }
    return
  }
  if (role === 'auditor') {
    router.push('/approval')
    return
  }
  if (role === 'admin') {
    window.open(`${API_BASE_URL}/admin/`, '_blank')
    return
  }
  router.push('/workplace')
}

function goSubmit() {
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  if (authStore.currentUser?.role === 'student') {
     router.push('/submit')
  } else {
    const role = authStore.currentUser?.role
    if (role === 'auditor') {
      if (confirm('当前角色为审核员，无法提交报修。\n是否进入审核中心？')) {
        router.push('/approval')
      }
      return
    }
    if (role === 'admin') {
      if (confirm('当前角色为管理员，无法提交报修。\n是否进入管理后台？')) {
        window.open(`${API_BASE_URL}/admin/`, '_blank')
      }
      return
    }
    if (confirm('当前角色为工作人员，无法提交报修。\n是否进入工作台处理工单？')) {
      router.push('/workplace')
    }
  }
}

function goLogin() {
  router.push('/login')
}

function goRegister() {
  router.push('/register')
}

function goTickets() {
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  router.push('/tickets')
}

function goAi() {
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  router.push('/ai-chat')
}
</script>

<style scoped>
.home-page {
  background: #f6f3f7;
}

.hero-section {
  background-image:
    linear-gradient(120deg, rgba(176, 50, 91, 0.82), rgba(255, 188, 188, 0.75)),
    var(--dashboard-hero-bg);
  background-size: cover;
  background-position: center;
  color: #fff;
}

.hero-overlay {
  backdrop-filter: blur(2px);
  padding: 48px 32px 40px;
}

.hero-main {
  max-width: var(--app-page-max-width);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 40px;
  align-items: center;
}

.hero-text h1 {
  font-size: 32px;
  letter-spacing: 1px;
  margin: 0 0 8px;
}

.hero-en {
  font-size: 13px;
  opacity: 0.9;
  margin-bottom: 18px;
  text-transform: uppercase;
}

.hero-desc {
  font-size: 15px;
  line-height: 1.8;
  max-width: 520px;
  margin-bottom: 24px;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
}

.btn-primary {
  padding: 10px 26px;
  border-radius: 999px;
  border: none;
  background: #ffe5f0;
  color: #b0325b;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-ghost {
  padding: 10px 22px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  background: transparent;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.hero-tips {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.12);
  padding: 8px 10px;
  border-radius: 999px;
  max-width: 520px;
}

.tip-badge {
  background: rgba(255, 255, 255, 0.26);
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
}

.hero-side {
  background: rgba(255, 255, 255, 0.14);
  border-radius: 16px;
  padding: 18px 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  padding: 10px 12px;
  color: #80304e;
}

.stat-label {
  font-size: 12px;
  opacity: 0.8;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
}

.stat-note {
  margin: 4px 2px 0;
  font-size: 11px;
  color: #fdf3f6;
}

.section {
  max-width: var(--app-page-max-width);
  margin: 0 auto;
  padding: 28px 20px 32px;
}

.section.gray {
  margin-top: 4px;
}

.section-header h2 {
  margin: 0;
  font-size: 20px;
  color: #333;
}

.section-header p {
  margin: 6px 0 18px;
  font-size: 13px;
  color: #888;
}

.entry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
}

.entry-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.entry-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 26px rgba(0, 0, 0, 0.06);
}

.entry-icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f2ecff;
  color: #5b4bd4;
  margin-bottom: 10px;
}

.entry-icon.primary {
  background: #ffe5f0;
  color: #b0325b;
}

.entry-icon.warning {
  background: #fff4e5;
  color: #d97706;
}

.entry-card h3 {
  margin: 0 0 6px;
  font-size: 16px;
  color: #333;
}

.entry-card p {
  margin: 0;
  font-size: 13px;
  color: #666;
  line-height: 1.7;
}

.flow-steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 18px;
}

.flow-item {
  background: #fff;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 5px 16px rgba(0, 0, 0, 0.04);
}

.step-index {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #ffe5f0;
  color: #b0325b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 8px;
}

.flow-item h3 {
  margin: 0 0 6px;
  font-size: 15px;
  color: #333;
}

.flow-item p {
  margin: 0;
  font-size: 13px;
  color: #666;
  line-height: 1.7;
}

@media (max-width: 768px) {
  .hero-overlay {
    padding: 32px 18px 24px;
  }

  .hero-main {
    grid-template-columns: 1fr;
    gap: 22px;
  }

  .hero-text h1 {
    font-size: 24px;
  }

  .hero-desc {
    font-size: 14px;
  }
}
</style>
