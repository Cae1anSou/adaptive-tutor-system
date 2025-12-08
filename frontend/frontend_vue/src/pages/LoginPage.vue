<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { initiateSessionSessionInitiatePost } from '../api/session'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const formState = reactive({
  nickname: '',
  theme: undefined as string | undefined,
})

const loading = ref(false)

const themes = [
  { value: 'pets', label: '🐱 萌宠乐园' },
  { value: 'shopping', label: '🛒 时尚购物' },
  { value: 'music', label: '🎵 影音娱乐' },
]

const handleStart = async () => {
  if (!formState.nickname || formState.nickname.trim().length < 2) {
    message.error('昵称至少需要2个字符')
    return
  }
  if (!formState.theme) {
    message.error('请选择学习主题')
    return
  }

  loading.value = true
  try {
    const cleanNickname = formState.nickname.replace(/[^\w\u4e00-\u9fa5]/g, '').trim()
    const participantId = cleanNickname
    const res = await initiateSessionSessionInitiatePost({
        participant_id: participantId,
        nickname: formState.nickname,
        theme: formState.theme
    } as any)
    // Adjust logic based on actual API response structure
    // Assuming backend returns { code: 200, data: { participant_id: '...' } }
    if (res.data && (res.data.code === 200 || res.data.code === 201)) {
      const pid = res.data.data?.participant_id || res.data.participant_id
      if (pid) {
        userStore.setSession(pid, formState.nickname, formState.theme)
        message.success('启动成功')
        // 跳转到 learning 页面，带上初始 topicId (mocking legacy '1_1')
        router.push('/learning/1_1')
      } else {
        message.error('返回数据异常: 缺少 participant_id')
      }
    } else {
      message.error(res.data?.message || '启动失败')
    }
  } catch (error) {
    console.error(error)
    message.error('网络错误，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-container">
    <!-- Header -->
    <header class="top-header">
      <h1 class="header-title">sync-PBL学习平台</h1>
      <button class="lang-btn">
        <span>🌐</span> EN
      </button>
    </header>

    <div class="content-container">
      <div class="panel">
        <div class="panel-header">
          <span>✨</span>
          <h2>欢迎使用sync-PBL学习平台</h2>
        </div>

        <div class="entry-container">
          <div class="entry-content">
            <!-- Welcome Section -->
            <div class="welcome-section">
              <div class="welcome-icon">🤖</div>
              <h2>和AI一起学HTML</h2>
              <p>选择你喜欢的主题，让sync-PBL带你亲手打造第一个网站 ✨</p>
            </div>

            <!-- Form Section -->
            <div class="form-section">
              <div class="input-row">
                <div class="input-group">
                  <span class="prefix-icon">👤</span>
                  <input 
                    v-model="formState.nickname" 
                    type="text" 
                    placeholder="输入你的昵称" 
                    maxlength="20"
                    @keyup.enter="handleStart"
                  />
                </div>
                <div class="input-group">
                  <span class="prefix-icon">⭐</span>
                  <select v-model="formState.theme">
                    <option :value="undefined" disabled>选择学习主题</option>
                    <option v-for="t in themes" :key="t.value" :value="t.value">
                      {{ t.label }}
                    </option>
                  </select>
                </div>
              </div>

              <button 
                class="start-button" 
                :disabled="loading || !formState.nickname || !formState.theme"
                @click="handleStart"
              >
                <span v-if="loading">⏳ 启动中...</span>
                <span v-else>▶️ 开始学习</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:root {
  --primary-color: #4f46e5;
  --primary-hover: #3730a3;
  --text-color: #1e293b;
  --text-light: #64748b;
  --border-color: #e5e7eb;
}

.login-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  position: relative;
  background: linear-gradient(-45deg, #667eea, #764ba2, #f093fb, #f5576c, #4facfe, #00f2fe);
  background-size: 400% 400%;
  animation: gradientShift 8s ease-in-out infinite;
  font-family: 'Inter', system-ui, sans-serif;
  color: #1e293b;
}

.login-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  z-index: 1;
}

.login-container > * {
  position: relative;
  z-index: 2;
}

.top-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 64px;
  padding: 0 32px;
  background: linear-gradient(90deg, #2563eb, #7c3aed);
  color: white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.lang-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  background-color: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
}
.lang-btn:hover {
  background-color: rgba(255, 255, 255, 0.3);
}

.content-container {
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 1;
  padding: 32px;
}

.panel {
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 900px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  background: linear-gradient(90deg, #2563eb, #7c3aed);
  color: white;
}
.panel-header h2 {
  font-size: 18px;
  margin: 0;
}

.entry-container {
  padding: 60px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.entry-content {
  width: 100%;
  max-width: 500px;
  text-align: center;
}

.welcome-section {
  margin-bottom: 40px;
}
.welcome-icon {
  font-size: 64px;
  margin-bottom: 16px;
}
.welcome-section h2 {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}
.welcome-section p {
  color: #64748b;
}

.form-section {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  border: 1px solid #e5e7eb;
}

.input-row {
  display: flex;
  gap: 16px;
  margin-bottom: 32px;
}
@media (max-width: 640px) {
  .input-row {
    flex-direction: column;
  }
}

.input-group {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
}

.prefix-icon {
  position: absolute;
  left: 12px;
  z-index: 2;
  font-size: 18px;
}

input, select {
  width: 100%;
  padding: 12px 12px 12px 40px;
  font-size: 16px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  outline: none;
  transition: all 0.2s;
  background: white;
}

input:focus, select:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79,70,229,0.1);
}

.start-button {
  width: 100%;
  padding: 16px;
  font-size: 18px;
  font-weight: 600;
  background: #4f46e5;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.start-button:hover:not(:disabled) {
  background: #3730a3;
  transform: translateY(-2px);
}
.start-button:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 100%; }
  100% { background-position: 0% 50%; }
}
</style>
