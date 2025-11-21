<script setup lang="ts">
import {ref, onMounted, onUnmounted, computed, nextTick} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {message} from 'ant-design-vue'
import {
  FileTextOutlined,
  CodeOutlined,
  PlayCircleOutlined,
  BulbOutlined,
  RobotOutlined,
  CheckCircleFilled,
  CloseCircleFilled,
  InfoCircleOutlined
} from '@ant-design/icons-vue'
import {marked} from 'marked'
import type * as Monaco from 'monaco-editor'
import loader from '@monaco-editor/loader'
import {getTestTaskTestTasksTopicIdGet} from '@/api/testTasks'
import {
  submitTest2SubmissionSubmitTest2Post,
  getSubmissionResultSubmissionSubmitTest2ResultTaskIdGet
} from '@/api/submission'

const route = useRoute()
const router = useRouter()

// --- 业务逻辑保持不变 ---
const loading = ref(false)
const submitting = ref(false)
const testTask = ref<API.TestTask | null>(null)
const testResult = ref<API.TestSubmissionResponse | null>(null)
type CodeState = { html: string; css: string; js: string }
const currentCode = ref<CodeState>({html: '', css: '', js: ''})
const activeTab = ref('html')
const showAskAI = ref(false)
const chatMessages = ref<any[]>([])
const participantId = ref('')
type StandaloneCodeEditor = Monaco.editor.IStandaloneCodeEditor
const htmlEditor = ref<StandaloneCodeEditor | null>(null)
const cssEditor = ref<StandaloneCodeEditor | null>(null)
const jsEditor = ref<StandaloneCodeEditor | null>(null)
const htmlEditorRef = ref<HTMLElement | null>(null)
const cssEditorRef = ref<HTMLElement | null>(null)
const jsEditorRef = ref<HTMLElement | null>(null)

const hasCodeContent = computed(() => currentCode.value.html || currentCode.value.css || currentCode.value.js)
const parsedDescription = computed(() => testTask.value?.description_md ? marked(testTask.value.description_md) : '')
const isMobile = computed(() => window.innerWidth <= 768)

// --- 现代简洁风格定义 (Modern Clean UI) ---

// 1. 页面容器：使用浅灰背景，营造沉浸式工作台感觉
const testPageStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: isMobile.value ? '1fr' : '380px 1fr', // 左侧定宽或比例，右侧自适应
  gridTemplateRows: isMobile.value ? 'auto auto 500px' : '1fr', // 桌面端单行两列
  gap: '16px',
  height: '100%',
  padding: '16px',
  width: '100%',
  boxSizing: 'border-box',
  backgroundColor: '#f5f7fa', // 极浅的蓝灰色背景
  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
}))

// 2. 左侧侧边栏容器（包含题目和结果）
const sidebarContainerStyle = computed(() => ({
  display: 'flex',
  flexDirection: 'column',
  gap: '16px',
  height: '100%',
  overflow: 'hidden'
}))

// 3. 通用卡片样式：白底，微弱阴影，圆角
const cardStyle = {
  background: '#ffffff',
  borderRadius: '8px',
  boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02)', // 非常细腻的阴影
  border: '1px solid #f0f0f0', // 极淡的边框
  display: 'flex',
  flexDirection: 'column' as const,
  overflow: 'hidden',
  transition: 'all 0.3s ease'
}

// 4. 卡片头部：极简，只有底部细线
const cardHeaderStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 16px',
  height: '48px',
  borderBottom: '1px solid #f0f0f0',
  backgroundColor: '#fff', // 纯白头部
  color: '#1f1f1f',
  fontWeight: 600,
  fontSize: '14px'
}

const cardContentStyle = {
  flex: '1',
  padding: '16px',
  overflowY: 'auto' as const,
  position: 'relative' as const
}

const cardFooterStyle = {
  padding: '12px 16px',
  borderTop: '1px solid #f0f0f0',
  backgroundColor: '#fafafa', // 浅灰底脚
  display: 'flex',
  justifyContent: 'flex-end',
  alignItems: 'center',
  gap: '8px'
}

// 编辑器区域特定样式
const editorContainerStyle = computed(() => ({
  ...cardStyle,
  gridRow: isMobile.value ? 'auto' : '1',
  gridColumn: isMobile.value ? '1' : '2',
  height: '100%' // 撑满高度
}))

// Markdown 样式：模仿 GitHub Readme 的干净风格
const markdownStyle = {
  lineHeight: 1.7,
  fontSize: '14px',
  color: '#374151',
  '& h1, h2, h3': { marginTop: '1em', marginBottom: '0.6em', color: '#111827', fontWeight: 600 },
  '& p': { marginBottom: '1em' },
  '& code': { background: '#f3f4f6', padding: '2px 5px', borderRadius: '4px', color: '#ef4444', fontSize: '12px' },
  '& pre': { background: '#f8fafc', padding: '12px', borderRadius: '6px', overflowX: 'auto', border: '1px solid #e2e8f0' }
}

// 结果状态颜色
const statusColors = {
  successBg: '#f6ffed',
  successBorder: '#b7eb8f',
  errorBg: '#fff2f0',
  errorBorder: '#ffccc7'
}

// --- 工具函数 ---
function normalizeCodeContent(raw: unknown): CodeState {
  if (!raw || typeof raw !== 'object') return {html: '', css: '', js: ''}
  const code = raw as any
  return { html: code.html || '', css: code.css || '', js: code.js || '' }
}

// Monaco 初始化 (使用 clean 的默认配置)
async function initializeMonacoEditor() {
  const monacoInstance = await loader.init()
  const options: Monaco.editor.IStandaloneEditorConstructionOptions = {
    theme: 'vs', // 标准白色主题
    minimap: { enabled: false },
    fontSize: 13,
    fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace", // 程序员喜欢的字体
    lineNumbers: 'on',
    automaticLayout: true,
    scrollBeyondLastLine: false,
    renderLineHighlight: 'all', // 淡淡的高亮行
    lineHeight: 1.5,
    padding: { top: 16, bottom: 16 }
  }

  const create = (ref: HTMLElement, val: string, lang: string) => {
    const editor = monacoInstance.editor.create(ref, { ...options, value: val, language: lang })
    editor.onDidChangeModelContent(() => currentCode.value[lang as keyof CodeState] = editor.getValue())
    return editor as any
  }

  if (htmlEditorRef.value) htmlEditor.value = create(htmlEditorRef.value, currentCode.value.html, 'html')
  if (cssEditorRef.value) cssEditor.value = create(cssEditorRef.value, currentCode.value.css, 'css')
  if (jsEditorRef.value) jsEditor.value = create(jsEditorRef.value, currentCode.value.js, 'javascript')
}

// 生命周期
onMounted(async () => {
  await initializePage()
  await nextTick()
  await initializeMonacoEditor()
})
onUnmounted(() => {
  htmlEditor.value?.dispose(); cssEditor.value?.dispose(); jsEditor.value?.dispose()
})

// 业务函数简化 (保持原有核心逻辑)
async function initializePage() {
  let topicId = route.params.topicId as string || route.query.topic as string || '1_1'
  participantId.value = localStorage.getItem('participantId') || 'anonymous'
  await loadTestTask(topicId)
}

async function loadTestTask(topicId: string) {
  loading.value = true
  try {
    const res = await getTestTaskTestTasksTopicIdGet({topic_id: topicId})
    if (res.data?.data) {
      const normalized = normalizeCodeContent(res.data.data.start_code)
      testTask.value = {...res.data.data, start_code: normalized}
      currentCode.value = normalized
      htmlEditor.value?.setValue(normalized.html)
      cssEditor.value?.setValue(normalized.css)
      jsEditor.value?.setValue(normalized.js)
    }
  } finally { loading.value = false }
}

async function submitCode() {
  if (!testTask.value) return
  submitting.value = true
  try {
    const res = await submitTest2SubmissionSubmitTest2Post({
      participant_id: participantId.value, topic_id: testTask.value.topic_id, code: currentCode.value
    })
    if (res.data?.data) pollSubmissionResult(res.data.data.task_id)
  } catch (e) { message.error('提交异常'); submitting.value = false }
}

async function pollSubmissionResult(taskId: string) {
  let attempts = 0
  const poll = async () => {
    try {
      const res = await getSubmissionResultSubmissionSubmitTest2ResultTaskIdGet({task_id: taskId})
      if (res.data?.data) {
        testResult.value = res.data.data
        showAskAI.value = !res.data.data.passed
        submitting.value = false
        if (res.data.data.passed) message.success('测试通过')
      } else if (attempts++ < 30) setTimeout(poll, 1000)
      else { message.error('超时'); submitting.value = false }
    } catch { submitting.value = false }
  }
  poll()
}

function handleTabChange(tab: string) {
  activeTab.value = tab
  setTimeout(() => {
    if(tab==='html') htmlEditor.value?.focus()
    if(tab==='css') cssEditor.value?.focus()
    if(tab==='js') jsEditor.value?.focus()
  }, 50)
}
</script>

<template>
  <div id="DefaultPage" :style="testPageStyle as any">

    <div :style="sidebarContainerStyle as any">

      <div :style="{ ...cardStyle, flex: testResult ? '1' : '2' } as any">
        <div :style="cardHeaderStyle">
          <div style="display:flex; align-items:center; gap:8px">
            <FileTextOutlined style="color: #1890ff"/>
            <span>题目描述</span>
          </div>
        </div>
        <div :style="cardContentStyle" class="custom-scrollbar">
          <div v-if="loading" style="padding: 20px; text-align: center; color: #999"><a-spin/></div>
          <div v-else-if="testTask" :style="markdownStyle as any" v-html="parsedDescription"></div>
        </div>
        <div :style="cardFooterStyle">
          <a-button type="text" size="small" style="color: #666">
            <template #icon><BulbOutlined /></template>
            提示
          </a-button>
        </div>
      </div>

      <div :style="{ ...cardStyle, flex: testResult ? '1' : '0 0 auto', minHeight: '100px' } as any">
        <div :style="cardHeaderStyle">
          <div style="display:flex; align-items:center; gap:8px">
            <CodeOutlined style="color: #722ed1"/>
            <span>运行结果</span>
          </div>
        </div>
        <div :style="cardContentStyle" class="custom-scrollbar">
          <div v-if="!testResult" style="height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; color:#bfbfbf">
            <InfoCircleOutlined style="font-size: 24px; margin-bottom: 8px"/>
            <span style="font-size: 12px">点击运行查看结果</span>
          </div>
          <div v-else>
            <div :style="{
               padding: '12px',
               borderRadius: '6px',
               background: testResult.passed ? statusColors.successBg : statusColors.errorBg,
               border: `1px solid ${testResult.passed ? statusColors.successBorder : statusColors.errorBorder}`,
               display: 'flex', alignItems: 'flex-start', gap: '10px'
             }">
              <CheckCircleFilled v-if="testResult.passed" style="color: #52c41a; font-size: 18px; margin-top: 2px"/>
              <CloseCircleFilled v-else style="color: #ff4d4f; font-size: 18px; margin-top: 2px"/>
              <div>
                <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #333">
                  {{ testResult.passed ? '测试通过' : '测试失败' }}
                </div>
                <div style="font-size: 13px; color: #666; line-height: 1.5">
                  {{ testResult.message }}
                </div>
              </div>
            </div>

            <div v-if="testResult.details?.length" style="margin-top: 12px; padding-left: 4px">
              <div v-for="(d, i) in testResult.details" :key="i" style="font-size: 12px; color: #666; margin-bottom: 4px; display:flex; gap: 6px">
                <span style="color: #ff4d4f">•</span> {{ d }}
              </div>
            </div>
          </div>
        </div>
        <div v-if="showAskAI" :style="cardFooterStyle">
          <a-button type="primary" ghost size="small" style="border-radius: 16px">
            <template #icon><RobotOutlined /></template>
            AI 帮我分析
          </a-button>
        </div>
      </div>
    </div>

    <div :style="editorContainerStyle as any">
      <div :style="{ ...cardHeaderStyle, padding: '0 8px', height: '44px', borderBottom: '1px solid #f0f0f0' }">
        <div style="display: flex; gap: 4px">
          <div v-for="tab in ['html', 'css', 'js']" :key="tab"
               @click="handleTabChange(tab)"
               :style="{
                 padding: '6px 16px',
                 cursor: 'pointer',
                 fontSize: '13px',
                 fontWeight: 500,
                 color: activeTab === tab ? '#1677ff' : '#666',
                 borderBottom: activeTab === tab ? '2px solid #1677ff' : '2px solid transparent',
                 transition: 'all 0.2s'
               }">
            {{ tab.toUpperCase() }}
          </div>
        </div>
        <div style="font-size: 12px; color: #999">自动保存</div>
      </div>

      <div style="flex: 1; position: relative;">
        <div v-show="activeTab === 'html'" style="height:100%"><div ref="htmlEditorRef" style="height:100%"></div></div>
        <div v-show="activeTab === 'css'" style="height:100%"><div ref="cssEditorRef" style="height:100%"></div></div>
        <div v-show="activeTab === 'js'" style="height:100%"><div ref="jsEditorRef" style="height:100%"></div></div>
      </div>

      <div :style="{ ...cardFooterStyle, height: '56px' }">
        <span v-if="submitting" style="margin-right: auto; font-size: 12px; color: #999">正在运行测试用例...</span>
        <a-button @click="() => initializePage()" :disabled="submitting">重置</a-button>
        <a-button type="primary" @click="submitCode" :loading="submitting" :disabled="!hasCodeContent">
          <template #icon><PlayCircleOutlined /></template>
          提交运行
        </a-button>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* 细节优化：滚动条 */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e5e7eb;
  border-radius: 3px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #d1d5db;
}

#DefaultPage {
  flex: 1;
  height: 100%;
}
</style>
