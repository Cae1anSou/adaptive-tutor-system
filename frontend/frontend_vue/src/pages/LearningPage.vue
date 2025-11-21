<script setup lang="ts">
import {computed, onMounted, onUnmounted, ref, watch} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {message} from 'ant-design-vue'
import {marked} from 'marked'
import {getLearningContentLearningContentTopicIdGet} from '@/api/learningContent'
import {
  GlobalOutlined,
  CodeOutlined,
  SelectOutlined,
  PauseCircleOutlined,
  CloseCircleOutlined,
  BulbOutlined,
  PlayCircleOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined
} from '@ant-design/icons-vue'

type LevelCard = {
  level: number
  html: string
  summary: string
}

type AllowedElements = {
  current: string[]
  cumulative: string[]
}

type ElementSelectionPayload = {
  tagName: string
  id: string
  className: string
  classList: string[]
  textContent: string
  outerHTML: string
  selector: string
  bounds: { x: number; y: number; width: number; height: number }
  styles: {
    backgroundColor: string
    color: string
    fontSize: string
  }
  pageURL: string
}

type SelectorBridge = {
  start: (isCumulative: boolean, elements: AllowedElements) => void
  stop: () => void
  updateMode: (isCumulative: boolean, elements: AllowedElements) => void
  destroy: () => void
}

const MESSAGE_TYPES = {
  START: 'SW_SELECT_START',
  STOP: 'SW_SELECT_STOP',
  CHOSEN: 'SW_SELECT_CHOSEN',
  UPDATE_MODE: 'SW_UPDATE_CUMULATIVE_MODE'
} as const

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const errorMessage = ref('')
const learningContent = ref<API.LearningContent | null>(null)
const currentTopicId = ref('')

const isClient = typeof window !== 'undefined'
const isMobile = ref(isClient ? window.innerWidth <= 768 : false)

const defaultCodeMessage = '在示例页面中选取元素后，会在此显示对应的HTML代码。'
const selectedElementCode = ref(defaultCodeMessage)
const selectedElementMeta = ref<ElementSelectionPayload | null>(null)
const isSelecting = ref(false)
const includeCumulative = ref(false)
const selectorBridge = ref<SelectorBridge | null>(null)
const exampleIframeRef = ref<HTMLIFrameElement | null>(null)

const allTopics = [
  '1_1', '1_2', '1_3',
  '2_1', '2_2', '2_3',
  '3_1', '3_2', '3_3',
  '4_1', '4_2', '4_3',
  '5_1', '5_2', '5_3',
  '6_1', '6_2', '6_3'
]


const parsedLevels = computed<LevelCard[]>(() => {
  if (!learningContent.value) return []
  return learningContent.value.levels.map(level => {
    const plain = level.description.replace(/\s+/g, ' ').trim()
    const summary = plain.length > 64 ? `${plain.slice(0, 64)}…` : plain
    return {
      level: level.level,
      html: marked.parse(level.description),
      summary
    }
  })
})

const expandedLevels = ref<number[]>([])
const activeLevelCard = computed<LevelCard | null>(() => {
  const activeLevel = expandedLevels.value[0]
  if (!activeLevel) return null
  return parsedLevels.value.find(level => level.level === activeLevel) ?? null
})

const allowedElements = computed<AllowedElements>(() => {
  if (!learningContent.value || !currentTopicId.value) {
    return {current: [], cumulative: []}
  }
  return computeAllowedElements(learningContent.value.sc_all ?? [], currentTopicId.value)
})


const showError = computed(() => Boolean(errorMessage.value))
const hasSelection = computed(() => Boolean(selectedElementMeta.value))

const topicTitle = computed(() => learningContent.value?.title ?? '未加载知识点')

function resolveTopicFromRoute(): string {
  const paramTopic = route.params.topicId
  if (typeof paramTopic === 'string' && paramTopic.trim()) {
    return paramTopic
  }
  const queryTopic = route.query.topic
  if (typeof queryTopic === 'string' && queryTopic.trim()) {
    return queryTopic
  }
  return ''
}

function getDefaultTopicId(): string {
  try {
    const stored = localStorage.getItem('learnedNodes')
    if (stored) {
      const learnedNodes: string[] = JSON.parse(stored)
      for (const topic of allTopics) {
        if (!learnedNodes.includes(topic)) {
          return topic
        }
      }
    }
  } catch (error) {
    console.warn('[LearningPage] 无法解析本地学习记录:', error)
  }
  return allTopics[0]
}

async function syncTopicFromRoute(force = false) {
  let topicId = resolveTopicFromRoute()
  if (!topicId) {
    topicId = getDefaultTopicId()
    message.info(`未指定知识点，已为你加载 ${topicId}`)
    try {
      await router.replace({name: 'learning', params: {topicId}})
    } catch (error) {
      console.warn('[LearningPage] 跳转默认知识点失败:', error)
    }
    return
  }
  if (!force && topicId === currentTopicId.value && learningContent.value) {
    return
  }
  currentTopicId.value = topicId
  await loadLearningContent(topicId)
}

async function loadLearningContent(topicId: string) {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await getLearningContentLearningContentTopicIdGet({topic_id: topicId})
    const body = response.data
    if (body?.code === 200 && body.data) {
      learningContent.value = body.data
    } else {
      learningContent.value = null
      errorMessage.value = body?.message || '加载学习内容失败'
      message.error(errorMessage.value)
    }
  } catch (error) {
    learningContent.value = null
    errorMessage.value = (error as Error).message || '加载学习内容失败'
    message.error(`加载学习内容失败: ${errorMessage.value}`)
    console.error('[LearningPage] 加载学习内容失败:', error)
  } finally {
    loading.value = false
  }
}


function normalizeElementName(element: string | null | undefined): string | null {
  if (!element) return null
  const trimmed = element.trim()
  if (!trimmed) return null
  if (/^<!/i.test(trimmed)) {
    return null
  }
  return trimmed.toLowerCase()
}

function deduplicate(elements: string[]): string[] {
  const seen = new Set<string>()
  const result: string[] = []
  for (const item of elements) {
    const normalized = normalizeElementName(item)
    if (normalized && !seen.has(normalized)) {
      seen.add(normalized)
      result.push(normalized)
    }
  }
  return result
}

function computeAllowedElements(scAll: API.SelectElementInfo[], topicId: string): AllowedElements {
  const cumulativeSet = new Set<string>()
  let currentElements: string[] = []

  for (const entry of scAll) {
    const normalizedList = deduplicate(entry.select_element ?? [])
    normalizedList.forEach(value => cumulativeSet.add(value))
    if (entry.topic_id === topicId) {
      currentElements = normalizedList
      break
    }
  }

  return {
    current: currentElements,
    cumulative: Array.from(cumulativeSet)
  }
}

function prepareAllowedElements(elements: AllowedElements): AllowedElements {
  return {
    current: Array.from(new Set(elements.current)),
    cumulative: Array.from(new Set(elements.cumulative))
  }
}

function createSelectorBridgeInstance(
  iframe: HTMLIFrameElement,
  onChosen: (payload: ElementSelectionPayload) => void,
  onError?: (error: Error) => void
): SelectorBridge {
  const iframeWindow = iframe.contentWindow
  if (!iframeWindow) {
    throw new Error('示例页面尚未加载，请稍后重试。')
  }

  const targetOrigin = '*'

  const handleMessage = (event: MessageEvent) => {
    if (event.source !== iframeWindow) return

    let data: unknown = event.data
    if (typeof data === 'string') {
      try {
        data = JSON.parse(data)
      } catch {
        return
      }
    }

    if (!data || typeof data !== 'object') return
    const message = data as {type?: string; payload?: ElementSelectionPayload}

    if (message.type === MESSAGE_TYPES.CHOSEN && message.payload) {
      onChosen(message.payload)
    }
  }

  window.addEventListener('message', handleMessage)

  const postMessage = (message: Record<string, unknown>) => {
    try {
      iframeWindow.postMessage(message, targetOrigin)
    } catch (error) {
      if (onError) {
        onError(error instanceof Error ? error : new Error(String(error)))
      }
    }
  }

  return {
    start(isCumulative, elements) {
      const payload = prepareAllowedElements(elements)
      postMessage({
        type: MESSAGE_TYPES.START,
        ignore: ['.sw-selector', '.sw-highlight'],
        allowedElements: payload,
        isCumulative
      })
    },
    stop() {
      postMessage({type: MESSAGE_TYPES.STOP})
    },
    updateMode(isCumulative, elements) {
      const payload = prepareAllowedElements(elements)
      postMessage({
        type: MESSAGE_TYPES.UPDATE_MODE,
        isCumulative,
        allowedElements: payload
      })
    },
    destroy() {
      window.removeEventListener('message', handleMessage)
    }
  }
}

function ensureSelectorBridge(): SelectorBridge | null {
  if (!exampleIframeRef.value) {
    message.error('示例页面尚未加载，请稍后重试。')
    return null
  }

  if (!selectorBridge.value) {
    try {
      selectorBridge.value = createSelectorBridgeInstance(
        exampleIframeRef.value,
        handleSelectorChosen,
        handleSelectorError
      )
    } catch (error) {
      selectorBridge.value = null
      handleSelectorError(error instanceof Error ? error : new Error(String(error)))
      return null
    }
  }

  return selectorBridge.value
}

function handleSelectorChosen(payload: ElementSelectionPayload) {
  selectedElementMeta.value = payload
  const outerHTML = payload.outerHTML?.trim()
  selectedElementCode.value = outerHTML && outerHTML.length ? outerHTML : `<${payload.tagName}>`
  isSelecting.value = false
  message.success(`已选中元素 <${payload.tagName}>`)
}

function handleSelectorError(error: Error | unknown) {
  const detail = error instanceof Error ? error.message : String(error)
  message.error(detail ? `元素选择器出错：${detail}` : '元素选择器出错')
  isSelecting.value = false
}

function handleIframeLoad(event: Event) {
  const iframe = event.target as HTMLIFrameElement | null
  if (!iframe) return

  if (selectorBridge.value) {
    selectorBridge.value.destroy()
    selectorBridge.value = null
  }

  exampleIframeRef.value = iframe
  isSelecting.value = false
}

function handleNavigateToTest() {
  if (!currentTopicId.value) return
  router.push({name: 'test', params: {topicId: currentTopicId.value}})
}

function handleStartSelector() {
  if (isSelecting.value) return

  if (!learningContent.value) {
    message.warning('请先加载学习内容后再试。')
    return
  }

  const elements = allowedElements.value
  if (!elements.current.length && !elements.cumulative.length) {
    message.warning('当前知识点暂无可选元素。')
    return
  }

  const bridge = ensureSelectorBridge()
  if (!bridge) return

  isSelecting.value = true
  try {
    bridge.start(includeCumulative.value, elements)
    const modeText = includeCumulative.value ? '累积模式，包含之前章节元素' : '当前章节模式'
    message.info(`已开启选择器（${modeText}），请在右侧示例页面中点击目标元素。`)
  } catch (error) {
    isSelecting.value = false
    handleSelectorError(error instanceof Error ? error : new Error(String(error)))
  }
}

function handleStopSelector() {
  if (!isSelecting.value && !selectorBridge.value) return
  selectorBridge.value?.stop()
  isSelecting.value = false
  message.success('已停止元素选择。')
}

function handleClearSelection() {
  if (!hasSelection.value) return
  selectedElementMeta.value = null
  selectedElementCode.value = defaultCodeMessage
  message.success('已清除已选元素。')
}

function handleResize() {
  if (!isClient) return
  isMobile.value = window.innerWidth <= 768
}

function clearError() {
  errorMessage.value = ''
}

function toggleLevel(level: number) {
  expandedLevels.value = expandedLevels.value[0] === level ? [] : [level]
}

function collapseLevels() {
  expandedLevels.value = []
}

onMounted(() => {
  if (isClient) {
    window.addEventListener('resize', handleResize)
  }
  syncTopicFromRoute(true).catch(error => {
    console.error('[LearningPage] 初始化失败:', error)
  })
})

onUnmounted(() => {
  if (isClient) {
    window.removeEventListener('resize', handleResize)
  }
  selectorBridge.value?.stop()
  selectorBridge.value?.destroy()
  selectorBridge.value = null
  exampleIframeRef.value = null
})

watch(
  () => [route.params.topicId, route.query.topic],
  () => {
    syncTopicFromRoute().catch(error => {
      console.error('[LearningPage] 路由同步失败:', error)
    })
  }
)

watch(
  () => learningContent.value?.topic_id,
  () => {
    selectorBridge.value?.stop()
    selectedElementMeta.value = null
    selectedElementCode.value = defaultCodeMessage
    includeCumulative.value = false
    isSelecting.value = false
    expandedLevels.value = []
  }
)

watch(includeCumulative, newValue => {
  if (!selectorBridge.value) return
  selectorBridge.value.updateMode(newValue, allowedElements.value)
})

watch(allowedElements, newElements => {
  if (!selectorBridge.value) return
  selectorBridge.value.updateMode(includeCumulative.value, newElements)
})

watch(
  parsedLevels,
  levels => {
    if (!levels.length || !levels.some(level => level.level === expandedLevels.value[0])) {
      expandedLevels.value = []
    }
  },
  {immediate: true}
)
</script>

<template>
  <div
    id="LearningPage"
    :class="['learning-page', { 'learning-page--mobile': isMobile }]"
  >
    <div v-if="showError" class="learning-page__error">
      <a-alert
        type="error"
        :message="errorMessage"
        show-icon
        closable
        @close="clearError"
      />
    </div>

    <a-spin :spinning="loading" tip="正在初始化学习环境...">
      <template v-if="learningContent">
        <div class="content-container">
          <div class="page-stack">

            <section class="panel example-panel">
              <div class="panel-header">
                <div class="header-title-group">
                  <div class="icon-box"><GlobalOutlined /></div>
                  <div>
                    <h2 class="panel-title">示例探索</h2>
                    <p class="panel-subtitle">{{ topicTitle }}</p>
                  </div>
                </div>
              </div>

              <div class="panel-body">
                <div class="exploration-layout">
                  <div class="preview-column">
                    <div class="browser-mockup">
                      <div class="browser-header">
                        <div class="browser-dots">
                          <span class="dot dot-red"></span>
                          <span class="dot dot-yellow"></span>
                          <span class="dot dot-green"></span>
                        </div>
                        <div class="browser-address">example_pages/index.html</div>
                      </div>
                      <div class="browser-content">
                        <iframe
                          id="element-selector-iframe"
                          ref="exampleIframeRef"
                          src="/example_pages/index.html"
                          title="示例页面预览"
                          loading="lazy"
                          @load="handleIframeLoad"
                        />
                      </div>
                    </div>
                  </div>

                  <div class="code-column">
                    <div class="code-editor-card">
                      <div class="editor-header">
                        <div class="tab-active">
                          <CodeOutlined class="tab-icon"/> 选中元素源码
                        </div>
                      </div>
                      <div class="editor-body">
                        <pre class="code-content" v-text="selectedElementCode"></pre>
                      </div>
                    </div>

                    <div class="control-panel">
                      <div class="control-group main-actions">
                        <a-button type="primary" :disabled="isSelecting" @click="handleStartSelector">
                          <template #icon><SelectOutlined/></template>
                          开始选取
                        </a-button>
                        <a-button v-if="isSelecting" danger class="pulse-btn" @click="handleStopSelector">
                          <template #icon><PauseCircleOutlined/></template>
                          停止
                        </a-button>
                        <a-button v-else :disabled="!hasSelection" @click="handleClearSelection">
                          <template #icon><CloseCircleOutlined/></template>
                          清除
                        </a-button>
                      </div>

                      <div class="control-group settings">
                        <div class="setting-item">
                          <span class="setting-label">累积模式</span>
                          <a-switch
                            v-model:checked="includeCumulative"
                            size="small"
                          />
                        </div>
                        <p class="setting-hint">
                          {{ includeCumulative ? '可选择所有已学章节的元素' : '仅限当前章节元素' }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="panel knowledge-panel">
              <div class="panel-header">
                <div class="header-title-group">
                  <div class="icon-box icon-box-purple"><BulbOutlined /></div>
                  <div>
                    <h2 class="panel-title">核心知识点</h2>
                    <p class="panel-subtitle">循序渐进的理解过程</p>
                  </div>
                </div>
              </div>

              <div class="panel-body">
                <div v-if="parsedLevels.length">

                  <transition name="fade-slide" mode="out-in">
                    <div v-if="!activeLevelCard" class="levels-grid" key="list">
                      <div
                        v-for="level in parsedLevels"
                        :key="level.level"
                        class="level-card"
                        @click="toggleLevel(level.level)"
                      >
                        <div class="level-card-top">
                          <span class="level-badge">Level {{ level.level }}</span>
                          <ArrowRightOutlined class="arrow-icon"/>
                        </div>
                        <p class="level-summary">{{ level.summary }}</p>
                      </div>
                    </div>

                    <div v-else class="level-detail-view" key="detail">
                      <div class="detail-sidebar">
                        <a-button type="text" @click="collapseLevels" class="back-btn">
                          <ArrowLeftOutlined/> 返回列表
                        </a-button>
                        <div class="current-level-indicator">
                          Level {{ activeLevelCard.level }}
                        </div>
                      </div>
                      <div class="detail-content paper-style">
                        <div class="markdown-body" v-html="activeLevelCard.html"/>
                      </div>
                    </div>
                  </transition>

                </div>
                <a-empty v-else description="暂无知识点内容" :image="simpleImage"/>
              </div>

              <div class="panel-footer">
                <a-button type="primary" size="large" shape="round" @click="handleNavigateToTest" class="action-btn">
                  前往练习 <PlayCircleOutlined/>
                </a-button>
              </div>
            </section>

          </div>
        </div>
      </template>
      <div v-else-if="!loading" class="empty-state-wrapper">
        <a-empty description="尚未加载学习内容" />
      </div>
    </a-spin>
  </div>
</template>

<style scoped>
/* 全局容器与背景 */
.learning-page {
  width: 100%;
  min-height: 100%;
  background-color: #f8fafc; /* 极简灰背景 */
  background-image: radial-gradient(#e2e8f0 1px, transparent 1px);
  background-size: 24px 24px; /* 点阵背景纹理 */
  padding-bottom: 40px;
  display: flex;
  flex-direction: column;
}

.content-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px;
  width: 100%;
}

.page-stack {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 通用面板样式 */
.panel {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 10px 15px -3px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(226, 232, 240, 0.8);
  overflow: hidden;
  transition: box-shadow 0.3s ease;
}

.panel:hover {
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
}

.panel-header {
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
}

.header-title-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-box {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #eff6ff;
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.icon-box-purple {
  background: #f5f3ff;
  color: #8b5cf6;
}

.panel-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.2;
}

.panel-subtitle {
  margin: 2px 0 0;
  font-size: 13px;
  color: #64748b;
}

.panel-body {
  padding: 24px;
}

/* 探索区布局 */
.exploration-layout {
  display: grid;
  grid-template-columns: 1.6fr 1fr; /* 左宽右窄 */
  gap: 24px;
  align-items: stretch;
}

/* 浏览器 Mockup 样式 */
.browser-mockup {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
  background: white;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
}

.browser-header {
  background: #f1f5f9;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid #e2e8f0;
}

.browser-dots {
  display: flex;
  gap: 6px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot-red { background: #ef4444; }
.dot-yellow { background: #f59e0b; }
.dot-green { background: #22c55e; }

.browser-address {
  flex: 1;
  background: white;
  border-radius: 6px;
  padding: 4px 12px;
  font-size: 12px;
  color: #64748b;
  text-align: center;
  border: 1px solid #e2e8f0;
}

.browser-content {
  flex: 1;
  position: relative;
  background: white;
}

.browser-content iframe {
  width: 100%;
  height: 100%;
  border: none;
}

/* 代码编辑器与控制台 */
.code-column {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.code-editor-card {
  background: #1e293b; /* 深色背景 */
  border-radius: 12px;
  overflow: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 200px;
  box-shadow: inset 0 0 20px rgba(0,0,0,0.2);
}

.editor-header {
  background: #0f172a;
  padding: 8px 0;
  display: flex;
}

.tab-active {
  background: #1e293b;
  color: #e2e8f0;
  padding: 6px 16px;
  font-size: 12px;
  border-top: 2px solid #3b82f6;
  display: flex;
  align-items: center;
  gap: 8px;
}

.editor-body {
  flex: 1;
  padding: 16px;
  overflow: auto;
}

.code-content {
  font-family: 'Fira Code', 'Menlo', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #a5b4fc; /* 浅蓝紫色代码高亮 */
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 控制面板 */
.control-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.control-group.main-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.settings {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-label {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.setting-hint {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
}

/* 知识卡片区 */
.levels-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.level-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.level-card:hover {
  border-color: #8b5cf6;
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(139, 92, 246, 0.1);
}

.level-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.level-badge {
  background: #f5f3ff;
  color: #7c3aed;
  padding: 4px 10px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.arrow-icon {
  color: #cbd5e1;
  transition: transform 0.2s;
}

.level-card:hover .arrow-icon {
  color: #7c3aed;
  transform: translateX(4px);
}

.level-summary {
  color: #475569;
  font-size: 14px;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 知识详情视图 */
.level-detail-view {
  display: flex;
  gap: 32px;
  background: #fff;
  min-height: 400px;
}

.detail-sidebar {
  width: 180px;
  flex-shrink: 0;
  border-right: 1px solid #f1f5f9;
  padding-right: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.current-level-indicator {
  font-size: 24px;
  font-weight: 800;
  color: #e2e8f0;
  text-align: right;
  margin-top: 20px;
}

.detail-content {
  flex: 1;
  max-width: 800px;
}

.paper-style {
  font-size: 16px;
}

/* 底部操作栏 */
.panel-footer {
  padding: 16px 24px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: flex-end;
  background: #f8fafc;
}

.action-btn {
  height: 48px;
  padding-left: 32px;
  padding-right: 32px;
  font-weight: 600;
  font-size: 15px;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

/* 动效 */
.pulse-btn {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Markdown 样式覆盖 */
.markdown-body {
  color: #334155;
  line-height: 1.8;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  color: #1e293b;
  border-bottom: none;
}

.markdown-body :deep(code) {
  color: #ec4899;
  background: #fdf2f8;
  padding: 2px 6px;
  border-radius: 4px;
}

.markdown-body :deep(pre) {
  background: #1e293b;
  border-radius: 8px;
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .exploration-layout {
    grid-template-columns: 1fr;
  }

  .browser-mockup {
    min-height: 300px;
  }

  .code-editor-card {
    min-height: 160px;
  }

  .level-detail-view {
    flex-direction: column;
  }

  .detail-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #f1f5f9;
    padding-bottom: 12px;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }

  .current-level-indicator {
    margin-top: 0;
    font-size: 18px;
  }
}

@media (max-width: 768px) {
  .content-container {
    padding: 12px;
  }

  .panel-header {
    padding: 16px;
  }

  .panel-body {
    padding: 16px;
  }

  .levels-grid {
    grid-template-columns: 1fr;
  }
}
</style>
