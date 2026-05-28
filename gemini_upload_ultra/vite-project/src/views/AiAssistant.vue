<!--
文件：src/views/AiAssistant.vue
类型：页面组件
说明：
- 该文件为前端业务模块，实现页面渲染、交互与接口调用
- 主要逻辑在 <script setup> 中（状态、事件、请求、路由跳转等）
涉及接口：ai-chat/、ai/generate_ticket/
-->

<template>
  <div class="ai-page">
    <div class="ai-card">
      <div class="ai-header">
        <div class="header-row">
          <h2>AI 报修助手</h2>
          <button class="btn-clear" type="button" @click="clearChat" :disabled="loading">清空对话</button>
        </div>
        <p>用于了解报修流程与注意事项，结果仅供参考</p>
      </div>

      <div class="warning-banner">
        <i class="fas fa-exclamation-triangle"></i>
        <div class="warning-text">
          <p>重要提示：AI 回答可能有误，仅供参考，以实际为准，不能盲目操作。</p>
          <p>涉及宿舍水电、用电安全、维修操作等，请勿自行检修，请通过平台提交报修等待处理。</p>
        </div>
      </div>

      <div class="chat-box">
        <div class="messages" ref="messageList">
          <div
            v-for="(m, index) in messages"
            :key="index"
            class="message-row"
            :class="m.role"
          >
            <div class="avatar" v-if="m.role === 'assistant'">
              <i class="fas fa-robot"></i>
            </div>
            <div class="avatar notice" v-else-if="m.role === 'notice'">
              <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div class="avatar user" v-else>
              <i class="fas fa-user"></i>
            </div>
            <div class="bubble">
              <p>{{ m.content }}</p>
              <button 
                v-if="m.role === 'assistant' && index === lastAssistantIndex && index > 1" 
                @click="generateTicketFromAi" 
                class="btn-ai-ticket"
                :disabled="loading"
              >
                <i class="fas fa-magic"></i> 一键帮我填报修单
              </button>
            </div>
          </div>

          <div v-if="loading" class="message-row assistant">
            <div class="avatar">
              <i class="fas fa-robot"></i>
            </div>
            <div class="bubble typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <div v-if="error" class="error-text">
          <i class="fas fa-info-circle"></i> {{ error }}
        </div>

        <form class="input-area" @submit.prevent="handleSend">
          <textarea
            v-model="input"
            rows="3"
            placeholder="请输入你想咨询的内容，例如：空调不制冷怎么报修？（请勿咨询/尝试任何带电操作）"
          ></textarea>
          <div class="input-actions">
            <button type="submit" :disabled="loading || !input.trim()">
              {{ loading ? '发送中...' : '发送' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, computed, watch } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { apiUrl } from '@/config'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const BASE_MESSAGES = [
  {
    role: 'assistant',
    content:
      '你好，我是 AI 报修助手，可以帮你了解报修流程与注意事项。'
  },
  {
    role: 'notice',
    content:
      '重要提示：AI 回答可能有误，仅供参考，以实际为准，不能盲目操作。涉及宿舍水电、用电安全、维修操作等，请勿自行检修，请通过平台提交报修等待处理。'
  }
]

function getStorageKey() {
  const uid = auth.currentUser?.id
  if (!uid) return ''
  return `ai_chat_messages_user_${uid}`
}

function normalizeMessages(list) {
  const arr = Array.isArray(list) ? list : []
  const cleaned = arr
    .filter(m => m && typeof m === 'object')
    .map(m => ({
      role: String(m.role || ''),
      content: String(m.content || '')
    }))
    .filter(m => m.role && m.content)
  return cleaned.length ? cleaned : BASE_MESSAGES
}

function loadMessages() {
  const key = getStorageKey()
  if (!key) {
    messages.value = [...BASE_MESSAGES]
    return
  }
  try {
    const raw = sessionStorage.getItem(key)
    if (!raw) {
      messages.value = [...BASE_MESSAGES]
      return
    }
    const parsed = JSON.parse(raw)
    messages.value = normalizeMessages(parsed)
  } catch (e) {
    messages.value = [...BASE_MESSAGES]
  }
}

function persistMessages() {
  const key = getStorageKey()
  if (!key) return
  try {
    const clipped = (messages.value || []).slice(-60)
    sessionStorage.setItem(key, JSON.stringify(clipped))
  } catch (e) {}
}

const messages = ref([...BASE_MESSAGES])

const input = ref('')
const loading = ref(false)
const error = ref('')
const messageList = ref(null)

const lastAssistantIndex = computed(() => {
  for (let i = messages.value.length - 1; i >= 0; i--) {
    if (messages.value[i]?.role === 'assistant') return i
  }
  return -1
})

function scrollToBottom() {
  nextTick(() => {
    const el = document.querySelector('.messages')
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  })
}

function clearChat() {
  messages.value = [...BASE_MESSAGES]
  input.value = ''
  error.value = ''
  persistMessages()
  scrollToBottom()
}

watch(
  () => auth.currentUser?.id,
  () => {
    loadMessages()
    scrollToBottom()
  },
  { immediate: true }
)

watch(
  messages,
  () => {
    persistMessages()
  },
  { deep: true }
)

async function handleSend() {
  if (!input.value.trim()) return
  
  if (!auth.isLoggedIn) {
    alert('请先登录系统')
    return
  }
  
  if (auth.currentUser?.role !== 'student') {
    alert('AI 助手目前仅面向学生开放。\n管理人员请使用管理后台功能。')
    return
  }

  const content = input.value
  messages.value.push({ role: 'user', content })
  input.value = ''
  error.value = ''
  scrollToBottom()

  loading.value = true
  
  try {
    const res = await axios.post(apiUrl('ai-chat/'), {
      content: content
    }, {
      headers: { Authorization: `Token ${auth.token}` }
    })

    const answer = res.data.answer
    const warning = res.data.warning
    messages.value.push({ role: 'assistant', content: answer })
    if (warning) {
       messages.value.push({ role: 'notice', content: warning })
    }
  } catch (e) {
    console.error(e)
    const msg = e?.response?.data?.detail || 'AI 暂时无法回应，请稍后再试。'
    error.value = msg
    messages.value.push({ role: 'notice', content: msg })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
async function generateTicketFromAi() {
  try {
    loading.value = true
    const res = await axios.post(apiUrl('ai/generate_ticket/'), {
      chat_history: messages.value
    }, {
      headers: { Authorization: `Token ${auth.token}` }
    })
    
    const { title, category, description, priority } = res.data
    sessionStorage.setItem('ai_ticket_data', JSON.stringify({ title, category, description, priority }))
    router.push('/submit?from_ai=1')
  } catch (e) {
    alert('生成报修单失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ai-page {
  padding: 24px;
  display: flex;
  justify-content: center;
}

.ai-card {
  width: 100%;
  max-width: var(--app-page-max-width);
  background: #ffffff;
  border-radius: 20px;
  padding: 24px 26px 20px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
}

.ai-header h2 {
  margin: 0;
  font-size: 22px;
  color: #b0325b;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.btn-clear {
  border: 1px solid #f1e2ea;
  background: #fff9fb;
  color: #b0325b;
  font-weight: 700;
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
}

.btn-clear:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-header p {
  margin: 6px 0 14px;
  font-size: 13px;
  color: #8c435f;
}

.warning-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: #fff3f5;
  border-radius: 10px;
  padding: 10px 12px;
  border: 1px solid #ffc9d4;
  color: #b0325b;
  font-size: 13px;
}

.warning-banner i {
  margin-top: 2px;
}

.warning-text p {
  margin: 0;
  line-height: 1.6;
}

.warning-text p + p {
  margin-top: 2px;
}

.chat-box {
  margin-top: 16px;
  border-radius: 14px;
  border: 1px solid #f1e2ea;
  background: #fff9fb;
  display: flex;
  flex-direction: column;
  height: 520px;
}

.messages {
  flex: 1;
  padding: 12px 16px;
  overflow-y: auto;
}

.message-row {
  display: flex;
  align-items: flex-start;
  margin-bottom: 10px;
}

.message-row.assistant {
  flex-direction: row;
}

.message-row.user {
  flex-direction: row-reverse;
}

.message-row.notice {
  flex-direction: row;
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 8px;
  background: linear-gradient(135deg, #ff9a9e, #fecfef);
  color: #ffffff;
}

.avatar.user {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.avatar.notice {
  background: linear-gradient(135deg, #ffb74d, #ff8a65);
}

.bubble {
  max-width: 70%;
  padding: 8px 12px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
}

.assistant .bubble {
  background: #ffffff;
  border: 1px solid #f1d1dd;
  color: #60394c;
}

.btn-ai-ticket {
  margin-top: 10px;
  background: linear-gradient(135deg, #ff9a9e, #fecfef);
  border: none;
  border-radius: 8px;
  padding: 6px 12px;
  color: #60394c;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.3s ease;
}

.btn-ai-ticket:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.notice .bubble {
  background: #fff6e6;
  border: 1px solid #ffd08a;
  color: #8a4b00;
  font-weight: 700;
}

.user .bubble {
  background: #667eea;
  color: #ffffff;
}

.bubble.typing {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.bubble.typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #b0325b;
  animation: blink 1.2s infinite ease-in-out;
}

.bubble.typing span:nth-child(2) {
  animation-delay: 0.15s;
}

.bubble.typing span:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes blink {
  0%,
  80%,
  100% {
    opacity: 0.2;
  }
  40% {
    opacity: 1;
  }
}

.error-text {
  padding: 0 16px 4px;
  font-size: 13px;
  color: #d14343;
  display: flex;
  align-items: center;
  gap: 6px;
}

.input-area {
  border-top: 1px solid #f1d1dd;
  padding: 10px 14px;
  background: #ffffff;
  border-radius: 0 0 14px 14px;
}

.input-area textarea {
  width: 100%;
  resize: none;
  border: 1px solid #e4c5d5;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 14px;
  box-sizing: border-box;
  outline: none;
}

.input-area textarea:focus {
  border-color: #b0325b;
  box-shadow: 0 0 0 2px rgba(176, 50, 91, 0.1);
}

.input-actions {
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.hint {
  font-size: 12px;
  color: #a45c7b;
}

.input-actions button {
  padding: 6px 20px;
  border-radius: 18px;
  border: none;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
}

.input-actions button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .ai-page {
    padding: 12px;
  }

  .ai-card {
    padding: 16px 14px 12px;
  }

  .chat-box {
    height: 460px;
  }
}
</style>
