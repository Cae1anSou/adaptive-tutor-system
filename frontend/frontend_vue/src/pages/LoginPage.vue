<script setup lang="ts">
import {ref, reactive} from 'vue'
import {useRouter} from 'vue-router'
import {message} from 'ant-design-vue'
import {initiateSessionSessionInitiatePost} from '../api/session'
import {useUserStore} from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

const formState = reactive({
  nickname: '',
  theme: undefined as string | undefined,
})

const loading = ref(false)
const isFocused = ref<'nickname' | 'theme' | null>(null)

const themes = [
  {value: 'pets', label: '🐱 萌宠乐园'},
  {value: 'shopping', label: '🛒 时尚购物'},
  {value: 'music', label: '🎵 影音娱乐'},
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
    if (res.data && (res.data.code === 200 || res.data.code === 201)) {
      const pid = res.data.data?.participant_id || res.data.participant_id
      if (pid) {
        userStore.setSession(pid, formState.nickname, formState.theme)
        message.success('启动成功')
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
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="blob blob-1"></div>
      <div class="blob blob-2"></div>
      <div class="blob blob-3"></div>
      <div class="grid-pattern"></div>
    </div>

    <!-- 主要内容区 -->
    <div class="main-content">
      <!-- 欢迎区域 -->
      <div class="welcome-section">
        <div class="logo-wrapper">
          <div class="logo-ring"></div>
          <div class="logo-icon">🤖</div>
        </div>
        <h1 class="title">
          <span class="title-primary">和AI一起学</span>
          <span class="title-highlight">HTML</span>
        </h1>
        <p class="subtitle">选择你喜欢的主题，让学习更有趣 ✨</p>
      </div>

      <!-- 表单区域 -->
      <div class="form-card" :class="{'has-focused': isFocused}">
        <div class="input-wrapper" :class="{focused: isFocused === 'nickname'}">
          <span class="input-icon">👤</span>
          <input
            v-model="formState.nickname"
            type="text"
            placeholder="输入你的昵称"
            maxlength="20"
            @focus="isFocused = 'nickname'"
            @blur="isFocused = null"
            @keyup.enter="handleStart"
          />
          <span v-if="formState.nickname" class="char-count">{{ formState.nickname.length }}/20</span>
        </div>

        <div class="input-wrapper" :class="{focused: isFocused === 'theme'}">
          <span class="input-icon">🎯</span>
          <div class="theme-selector">
            <select
              v-model="formState.theme"
              @focus="isFocused = 'theme'"
              @blur="isFocused = null"
            >
              <option :value="undefined" disabled>选择学习主题</option>
              <option v-for="t in themes" :key="t.value" :value="t.value">
                {{ t.label }}
              </option>
            </select>
            <div class="select-arrow">▼</div>
          </div>
          <div v-if="formState.theme" class="selected-theme-badge">
            {{ themes.find(t => t.value === formState.theme)?.label?.split(' ')[0] }}
          </div>
        </div>

        <button
          class="start-btn"
          :disabled="loading || !formState.nickname || !formState.theme"
          @click="handleStart"
        >
          <span class="btn-bg"></span>
          <span class="btn-content">
            <span v-if="loading" class="loading-spinner"></span>
            <span v-else>🚀</span>
            <span>{{ loading ? '启动中...' : '开始学习' }}</span>
          </span>
        </button>
      </div>

      <!-- 底部提示 -->
      <p class="hint">按 Enter 键快速开始</p>
    </div>
  </div>
</template>

<style scoped>
/* CSS变量 */
:root {
  --primary: #6366f1;
  --primary-dark: #4f46e5;
  --primary-light: #818cf8;
  --accent: #f59e0b;
  --accent-light: #fbbf24;
  --bg-dark: #0f172a;
  --bg-card: rgba(255, 255, 255, 0.95);
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --border: #e2e8f0;
  --shadow-soft: 0 4px 20px rgba(0, 0, 0, 0.08);
  --shadow-hover: 0 8px 30px rgba(99, 102, 241, 0.25);
}

.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  font-family: 'PingFang SC', 'Microsoft YaHei', -apple-system, sans-serif;
}

/* 背景装饰 */
.bg-decoration {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 0;
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
  animation: float 20s ease-in-out infinite;
}

.blob-1 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #818cf8, #c084fc);
  top: -100px;
  right: -100px;
  animation-delay: 0s;
}

.blob-2 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #67e8f9, #6366f1);
  bottom: -50px;
  left: -50px;
  animation-delay: -7s;
}

.blob-3 {
  width: 250px;
  height: 250px;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation-delay: -14s;
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(99, 102, 241, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99, 102, 241, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(20px, -20px) scale(1.05); }
  50% { transform: translate(-10px, 10px) scale(0.95); }
  75% { transform: translate(15px, 15px) scale(1.02); }
}

/* 主内容区 */
.main-content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 24px;
}

/* 欢迎区域 */
.welcome-section {
  text-align: center;
  margin-bottom: 32px;
}

.logo-wrapper {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
}

.logo-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #6366f1;
  border-right-color: #6366f1;
  animation: rotate 3s linear infinite;
}

.logo-icon {
  position: absolute;
  inset: 8px;
  font-size: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes rotate {
  to { transform: rotate(360deg); }
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.title-primary {
  color: #1e293b;
}

.title-highlight {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  position: relative;
}

.title-highlight::after {
  content: '';
  position: absolute;
  bottom: 2px;
  left: 0;
  right: 0;
  height: 8px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.3), rgba(139, 92, 246, 0.3));
  z-index: -1;
  border-radius: 4px;
}

.subtitle {
  color: #64748b;
  font-size: 15px;
  margin: 0;
}

/* 表单卡片 */
.form-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 28px;
  box-shadow:
    0 4px 20px rgba(0, 0, 0, 0.08),
    0 0 0 1px rgba(255, 255, 255, 0.5);
  transition: all 0.3s ease;
}

.form-card:hover {
  box-shadow:
    0 8px 30px rgba(99, 102, 241, 0.15),
    0 0 0 1px rgba(255, 255, 255, 0.8);
}

.form-card.has-focused {
  box-shadow:
    0 12px 40px rgba(99, 102, 241, 0.2),
    0 0 0 1px rgba(99, 102, 241, 0.1);
}

.input-wrapper {
  position: relative;
  margin-bottom: 16px;
  transition: all 0.3s ease;
}

.input-wrapper.focused {
  transform: translateX(4px);
}

.input-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  z-index: 2;
  transition: all 0.3s ease;
}

.input-wrapper.focused .input-icon {
  transform: translateY(-50%) scale(1.1);
}

.input-wrapper input,
.theme-selector {
  width: 100%;
  padding: 16px 16px 16px 48px;
  font-size: 16px;
  border: 2px solid #e2e8f0;
  border-radius: 14px;
  outline: none;
  background: #f8fafc;
  transition: all 0.3s ease;
  color: #1e293b;
}

.input-wrapper input:hover,
.theme-selector:hover {
  border-color: #cbd5e1;
}

.input-wrapper input:focus,
.theme-selector:focus-within {
  border-color: #6366f1;
  background: white;
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
}

.theme-selector {
  position: relative;
  padding-right: 48px;
  cursor: pointer;
  appearance: none;
}

.select-arrow {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 10px;
  color: #94a3b8;
  transition: transform 0.3s ease;
  pointer-events: none;
}

.theme-selector:focus-within .select-arrow {
  transform: translateY(-50%) rotate(180deg);
  color: #6366f1;
}

.char-count {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 12px;
  color: #94a3b8;
  pointer-events: none;
}

.selected-theme-badge {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  animation: popIn 0.3s ease;
}

@keyframes popIn {
  0% { transform: translateY(-50%) scale(0); }
  50% { transform: translateY(-50%) scale(1.2); }
  100% { transform: translateY(-50%) scale(1); }
}

/* 开始按钮 */
.start-btn {
  width: 100%;
  padding: 4px;
  font-size: 17px;
  font-weight: 600;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  margin-top: 8px;
}

.btn-bg {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.start-btn:hover:not(:disabled) .btn-bg {
  background: linear-gradient(135deg, #4f46e5, #7c3aed);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
}

.start-btn:active:not(:disabled) .btn-bg {
  transform: scale(0.98);
}

.start-btn:disabled .btn-bg {
  background: linear-gradient(135deg, #cbd5e1, #94a3b8);
}

.btn-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px;
  color: white;
}

.loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 底部提示 */
.hint {
  text-align: center;
  font-size: 13px;
  color: #94a3b8;
  margin: 20px 0 0;
}

/* 响应式 */
@media (max-width: 480px) {
  .title {
    font-size: 26px;
  }

  .logo-wrapper {
    width: 70px;
    height: 70px;
  }

  .logo-icon {
    font-size: 42px;
  }

  .form-card {
    padding: 24px;
    border-radius: 20px;
  }

  .main-content {
    padding: 16px;
  }
}
</style>
