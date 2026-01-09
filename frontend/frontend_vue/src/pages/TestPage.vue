<script setup lang="ts">
import {ref, onMounted, onUnmounted, computed, nextTick, watch} from 'vue'
import {useChatContextStore} from '@/stores/chatContext'
import {useRoute, useRouter} from 'vue-router'
import {useActiveHint, type HintEventDetail} from '@/composables/useActiveHint'
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
  submitTest2SubmissionSubmitTest2Post
} from '@/api/submission'
import websocket from '@/api/websocket'

const route = useRoute()
const router = useRouter()
const chatStore = useChatContextStore()



// --- 业务逻辑保持不变 ---
const loading = ref(false)
const submitting = ref(false)
const testTask = ref<API.TestTask | null>(null)
const testResult = ref<API.TestSubmissionResponse | null>(null)
type CodeState = { html: string; css: string; js: string }
const currentCode = ref<CodeState>({html: '', css: '', js: ''})
const activeTab = ref('html')
const showAskAI = ref(false)

// Sync Code
watch(currentCode, (v) => {
  chatStore.updateCodeContext(v.html, v.css, v.js)
}, { deep: true })

// Sync Task Info
watch(testTask, (v) => {
  if (v) {
    chatStore.updateTaskContext({ description: v.description_md })
  }
})

// Sync Result
watch(testResult, (v) => {
  if (v) {
    chatStore.updateTaskContext({
      status: v.passed ? 'success' : 'failed',
      error: v.message
    })
  }
})

// --- 主动提示逻辑 ---
// 为了让 useActiveHint 能监听 specific code changes，我们需要传递 Ref
const htmlCode = computed(() => currentCode.value.html)
const cssCode = computed(() => currentCode.value.css)
const jsCode = computed(() => currentCode.value.js)

const handleHintTriggered = (detail: HintEventDetail) => {
  console.log('[ActiveHint Triggered]', detail)
  
  // 直接通过 ChatStore 添加系统消息
  chatStore.messages.push({
    role: 'system',
    id: Date.now().toString(),
    content: detail.message,
    createdAt: Date.now()
  })
  
  // 如果需要弹窗提醒也可以在这里做 message.info(detail.message)
}

// 初始化主动提示 Hook
// 注意：topicId 是响应式的，但在 hook 内部我们只取了初始值或者需要 watch 它的变化
// 这里简单起见，我们假设 page reload 才会换 topic，或者我们传递一个 getter
const activeHint = useActiveHint(
  { html: htmlCode, css: cssCode, js: jsCode },
  route.params.topicId as string || 'unknown',
  handleHintTriggered
)
const chatMessages = ref<any[]>([])
const participantId = ref('')
const currentTaskId = ref('')
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

// --- Google/Meta 极简蓝色调风格 ---

// 1. 页面容器静态样式
const STATIC_PAGE_STYLE = {
  display: 'grid',
  gridTemplateRows: isMobile.value ? 'auto auto 500px' : '1fr',
  gap: '16px',
  height: '100%',
  padding: '16px',
  width: '100%',
  boxSizing: 'border-box',
  backgroundColor: '#FFFFFF',
  fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
}

// 1. 页面容器
const testPageStyle = computed(() => ({
  ...STATIC_PAGE_STYLE,
  gridTemplateColumns: isMobile.value ? '1fr' : '380px 1fr'
}))

// 2. 左侧侧边栏容器
const sidebarContainerStyle = computed(() => ({
  display: 'flex',
  flexDirection: 'column',
  gap: '16px',
  height: '100%',
  overflow: 'hidden'
}))

// 3. 通用卡片样式
const cardStyle = {
  background: '#FFFFFF',
  borderRadius: '8px',
  boxShadow: '0 1px 3px rgba(60, 64, 67, 0.1)',
  border: '1px solid #E8EAED',
  display: 'flex',
  flexDirection: 'column' as const,
  overflow: 'hidden'
}

// 4. 卡片头部
const cardHeaderStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '0 16px',
  height: '48px',
  borderBottom: '1px solid #E8EAED',
  backgroundColor: '#FFFFFF',
  color: '#202124',
  fontWeight: 500,
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
  borderTop: '1px solid #E8EAED',
  backgroundColor: '#FFFFFF',
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
  height: '100%'
}))

// Markdown 样式
const markdownStyle = {
  lineHeight: 1.7,
  fontSize: '14px',
  color: '#3C4043',
  '& h1, h2, h3': { marginTop: '1em', marginBottom: '0.6em', color: '#202124', fontWeight: 600 },
  '& p': { marginBottom: '1em' },
  '& code': { background: '#E8F0FE', padding: '2px 5px', borderRadius: '4px', color: '#4285F4', fontSize: '12px' },
  '& pre': { background: '#202124', padding: '12px', borderRadius: '6px', overflowX: 'auto', border: 'none' }
}

// 结果状态颜色 - Google 风格
const statusColors = {
  successBg: '#E6F4EA',
  successBorder: '#34A853',
  errorBg: '#FCE8E6',
  errorBorder: '#EA4335'
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
  
  // Setup WebSocket for real-time results
  websocket.connect()
  websocket.subscribe('submission_result', handleSubmissionResult)
  
  await nextTick()
  await initializeMonacoEditor()
})
onUnmounted(() => {
  websocket.unsubscribe('submission_result', handleSubmissionResult)
  htmlEditor.value?.dispose(); cssEditor.value?.dispose(); jsEditor.value?.dispose()
})

// 业务函数简化 (保持原有核心逻辑)
async function initializePage() {
  let topicId = route.params.topicId as string || route.query.topic as string || '1_1'
  participantId.value = localStorage.getItem('participant_id') || 'anonymous'
  
  // Initialize AI Context
  chatStore.setContext('test', topicId)
  
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
  testResult.value = null // Clear previous result
  try {
    const res = await submitTest2SubmissionSubmitTest2Post({
      participant_id: participantId.value, topic_id: testTask.value.topic_id, code: currentCode.value
    })
    if (res.data?.data) {
      currentTaskId.value = res.data.data.task_id
      message.loading({ content: '正在运行测试用例...', key: 'testing' })
    }
  } catch (e) { 
    message.error('提交异常'); 
    submitting.value = false 
  }
}

function handleSubmissionResult(payload: any) {
  // Payload is SocketResponse2: { type, taskid, message: EvaluationResult, ... }
  // EvaluationResult: { passed, message, details, ... }

  // Verify if this result matches our current task
  // Backend sends 'taskid', distinct from 'task_id' in other places
  const incomingTaskId = payload.taskid || payload.task_id
  if (incomingTaskId && currentTaskId.value && incomingTaskId !== currentTaskId.value) {
    return
  }
  
  message.destroy('testing') // Stop loading message
  
  const result = payload.message || payload // Fallback if structure changes
  
  if (payload.error || result.error) {
     const errMsg = (payload.error?.message || payload.error) ?? result.error
     message.error('测试运行出错: ' + errMsg)
     submitting.value = false
     return
  }

  testResult.value = result
  showAskAI.value = !result.passed
  submitting.value = false
  
  if (result.passed) {
    message.success('测试通过')
  } else {
    message.error('测试未通过')
  }
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
            <FileTextOutlined style="color: #4285F4"/>
            <span>题目描述</span>
          </div>
        </div>
        <div :style="cardContentStyle" class="custom-scrollbar">
          <div v-if="loading" style="padding: 20px; text-align: center; color: #9AA0A6"><a-spin/></div>
          <div v-else-if="testTask" :style="markdownStyle as any" v-html="parsedDescription"></div>
        </div>
        <div :style="cardFooterStyle">
          <a-button type="text" size="small" style="color: #5F6368">
            <template #icon><BulbOutlined /></template>
            提示
          </a-button>
        </div>
      </div>

      <div :style="{ ...cardStyle, flex: testResult ? '1' : '0 0 auto', minHeight: '100px' } as any">
        <div :style="cardHeaderStyle">
          <div style="display:flex; align-items:center; gap:8px">
            <CodeOutlined style="color: #4285F4"/>
            <span>运行结果</span>
          </div>
        </div>
        <div :style="cardContentStyle" class="custom-scrollbar">
          <div v-if="!testResult" style="height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; color:#9AA0A6">
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
              <CheckCircleFilled v-if="testResult.passed" style="color: #34A853; font-size: 18px; margin-top: 2px"/>
              <CloseCircleFilled v-else style="color: #EA4335; font-size: 18px; margin-top: 2px"/>
              <div>
                <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; color: #202124">
                  {{ testResult.passed ? '测试通过' : '测试失败' }}
                </div>
                <div style="font-size: 13px; color: #5F6368; line-height: 1.5">
                  {{ testResult.message }}
                </div>
              </div>
            </div>

            <div v-if="testResult.details?.length" style="margin-top: 12px; padding-left: 4px">
              <div v-for="(d, i) in testResult.details" :key="i" style="font-size: 12px; color: #5F6368; margin-bottom: 4px; display:flex; gap: 6px">
                <span style="color: #EA4335">•</span> {{ d }}
              </div>
            </div>
          </div>
        </div>
        <div v-if="showAskAI" :style="cardFooterStyle">
          <a-button type="primary" ghost size="small" style="border-radius: 4px">
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
                 color: activeTab === tab ? '#4285F4' : '#5F6368',
                 borderBottom: activeTab === tab ? '2px solid #4285F4' : '2px solid transparent',
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
        <span v-if="submitting" style="margin-right: auto; font-size: 12px; color: #9AA0A6">正在运行测试用例...</span>
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
  background: #BDC1C6;
  border-radius: 3px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #9AA0A6;
}

#DefaultPage {
  flex: 1;
  height: 100%;
}
</style>
