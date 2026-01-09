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
      const resData = res.data as any
      const pid = res.data.data?.participant_id || resData.participant_id || ''
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
    <div class="bg-pattern"></div>

    <!-- 主要内容区 -->
    <div class="main-content">
      <!-- Logo区 -->
      <div class="logo-section">
        <div class="logo-icon">🌐</div>
        <h1 class="title">
          <span class="title-primary">和AI一起学</span>
          <span class="title-highlight">HTML</span>
        </h1>
        <p class="subtitle">选择你喜欢的主题，开始学习之旅</p>
      </div>

      <!-- 表单卡片 -->
      <div class="form-card">
        <div class="input-group">
          <label class="input-label">昵称</label>
          <input
            v-model="formState.nickname"
            type="text"
            placeholder="给自己起个名字"
            maxlength="20"
            @focus="isFocused = 'nickname'"
            @blur="isFocused = null"
            @keyup.enter="handleStart"
          />
          <span v-if="formState.nickname" class="char-count">{{ formState.nickname.length }}/20</span>
        </div>

        <div class="input-group">
          <label class="input-label">学习主题</label>
          <div class="select-wrapper">
            <select
              v-model="formState.theme"
              @focus="isFocused = 'theme'"
              @blur="isFocused = null"
            >
              <option :value="undefined" disabled>选择一个感兴趣的主题</option>
              <option v-for="t in themes" :key="t.value" :value="t.value">
                {{ t.label }}
              </option>
            </select>
            <span class="select-arrow">▼</span>
          </div>
        </div>

        <button
          class="start-btn"
          :disabled="loading || !formState.nickname || !formState.theme"
          @click="handleStart"
        >
          <span v-if="loading" class="btn-loading"></span>
          <span>{{ loading ? '启动中...' : '开始学习' }}</span>
        </button>
      </div>

      <!-- 底部提示 -->
      <p class="hint">按 Enter 键快速开始</p>
    </div>
  </div>
</template>

<style scoped>
/* Google Blue 配色 + 视觉层次 */
:root {
  --google-blue: #4285F4;
  --google-blue-hover: #3367D6;
  --google-blue-light: #E8F0FE;
  --text-primary: #202124;
  --text-secondary: #5F6368;
  --border: #DADCE0;
  --border-focus: #4285F4;
  --bg-page: #F8F9FA;
  --shadow-sm: 0 1px 2px rgba(60, 64, 67, 0.1);
  --shadow-md: 0 1px 3px rgba(60, 64, 67, 0.15);
  --shadow-lg: 0 2px 8px rgba(60, 64, 67, 0.2);
}

.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page);
  font-family: 'Google Sans', 'Product Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  position: relative;
}

/* 背景图案 */
.bg-pattern {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 20% 80%, rgba(66, 133, 244, 0.08) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(66, 133, 244, 0.06) 0%, transparent 50%);
  pointer-events: none;
}

/* 主内容区 */
.main-content {
  width: 100%;
  max-width: 420px;
  padding: 40px 24px;
  position: relative;
  z-index: 1;
}

/* Logo区 */
.logo-section {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  font-size: 48px;
  margin-bottom: 16px;
  display: inline-block;
}

.title {
  font-size: 32px;
  font-weight: 400;
  margin: 0 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
  letter-spacing: -0.5px;
}

.title-primary {
  color: var(--text-primary);
}

.title-highlight {
  color: var(--google-blue);
  font-weight: 500;
}

.subtitle {
  color: var(--text-secondary);
  font-size: 15px;
  margin: 0;
  font-weight: 400;
}

/* 表单卡片 */
.form-card {
  background: #FFFFFF;
  border: 1px solid #E8EAED;
  border-radius: 12px;
  padding: 28px;
  box-shadow: 0 1px 3px rgba(60, 64, 67, 0.1);
}

/* 输入组 */
.input-group {
  position: relative;
  margin-bottom: 20px;
}

.input-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.input-group input,
.select-wrapper select {
  width: 100%;
  padding: 12px 14px;
  font-size: 15px;
  border: 1px solid var(--border);
  border-radius: 8px;
  outline: none;
  background: #FFFFFF;
  transition: all 0.2s ease;
  color: var(--text-primary);
  font-family: inherit;
  appearance: none;
  -webkit-appearance: none;
}

.input-group input::placeholder {
  color: #9AA0A6;
}

.input-group input:hover,
.select-wrapper select:hover {
  border-color: #BDC1C6;
}

.input-group input:focus,
.select-wrapper select:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.1);
}

.char-count {
  position: absolute;
  right: 14px;
  top: 42px;
  font-size: 12px;
  color: #9AA0A6;
  pointer-events: none;
}

/* 下拉选择 */
.select-wrapper {
  position: relative;
}

.select-arrow {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 10px;
  color: #9AA0A6;
  pointer-events: none;
}

.select-wrapper select {
  padding-right: 36px;
}

/* 开始按钮 */
.start-btn {
  width: 100%;
  padding: 14px 24px;
  font-size: 15px;
  font-weight: 500;
  color: #222222;
  background: var(--google-blue);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.start-btn:hover:not(:disabled) {
  background: var(--google-blue-hover);
  box-shadow: 0 2px 8px rgba(66, 133, 244, 0.3);
}

.start-btn:active:not(:disabled) {
  background: var(--google-blue-hover);
  transform: scale(0.98);
}

.start-btn:disabled {
  background: #DADCE0;
  color: #9AA0A6;
  cursor: not-allowed;
}

.btn-loading {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #FFFFFF;
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
  color: #9AA0A6;
  margin: 24px 0 0;
}

/* 响应式 */
@media (max-width: 480px) {
  .title {
    font-size: 26px;
  }

  .form-card {
    padding: 24px 20px;
    border-radius: 0;
    border-left: none;
    border-right: none;
    box-shadow: none;
  }

  .main-content {
    padding: 24px 0;
  }
}
</style>
