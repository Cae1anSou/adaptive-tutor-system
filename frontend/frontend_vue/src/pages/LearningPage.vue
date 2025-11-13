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

    <a-spin :spinning="loading" tip="加载学习内容...">
      <template v-if="learningContent">
        <div class="content-container">
          <div class="page-stack">
            <section class="panel example-panel">
              <div class="panel-header">
                <GlobalOutlined class="panel-icon"/>
                <div>
                  <h2 class="panel-title">开放式示例页面探索</h2>
                  <p class="panel-subtitle">{{ topicTitle }}</p>
                </div>
              </div>
              <div class="panel-body">
                <div class="exploration-content">
                  <div class="preview-section">
                    <div class="ratio-16x9">
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
                  <div class="code-section">
                    <div class="info-content">
                      <div class="info-header">
                        <CodeOutlined/>
                        <h3>选中元素代码</h3>
                      </div>
                      <pre class="code-display" v-text="selectedElementCode"/>
                    </div>
                    <div class="code-panel-footer">
                      <div class="selector-controls">
                        <a-button type="primary" :disabled="isSelecting" @click="handleStartSelector">
                          <template #icon>
                            <SelectOutlined/>
                          </template>
                          选取元素
                        </a-button>
                        <a-button danger :disabled="!isSelecting" @click="handleStopSelector">
                          <template #icon>
                            <PauseCircleOutlined/>
                          </template>
                          停止选择
                        </a-button>
                        <a-button :disabled="!hasSelection" @click="handleClearSelection">
                          <template #icon>
                            <CloseCircleOutlined/>
                          </template>
                          清除选择
                        </a-button>
                      </div>
                      <div class="selector-toggle-container">
                        <div class="toggle-text">包含之前章节的元素</div>
                        <a-switch
                          v-model:checked="includeCumulative"
                          :checked-children="'开启'"
                          :un-checked-children="'关闭'"
                        />
                        <p class="toggle-hint">
                          开启后可选择当前及之前所有章节的元素，关闭时仅可选择当前章节元素。
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="panel knowledge-panel">
              <div class="panel-header">
                <BulbOutlined class="panel-icon"/>
                <div>
                  <h2 class="panel-title">渐进式知识点展示</h2>
                  <p class="panel-subtitle">分层深入当前知识点的核心概念</p>
                </div>
              </div>
              <div class="panel-body">
                <div v-if="parsedLevels.length">
                  <div v-if="!activeLevelCard" class="levels-overview">
                    <div
                      v-for="level in parsedLevels"
                      :key="level.level"
                      class="level-card level-card--compact"
                      @click="toggleLevel(level.level)"
                    >
                      <div class="level-card__badge">Level {{ level.level }}</div>
                      <p class="level-summary level-summary--compact">{{ level.summary }}</p>
                      <div class="level-card__hint">
                        查看详情
                        <ArrowRightOutlined/>
                      </div>
                    </div>
                  </div>
                  <div v-else class="level-detail">
                    <div class="level-detail__actions">
                      <a-button type="link" @click="collapseLevels">
                        <template #icon>
                          <ArrowLeftOutlined/>
                        </template>
                        返回知识点列表
                      </a-button>
                    </div>
                    <div class="level-card level-card--expanded">
                      <div class="level-header">
                        <h3>Level {{ activeLevelCard.level }}</h3>
                        <p class="level-summary">{{ activeLevelCard.summary }}</p>
                      </div>
                      <div class="level-body">
                        <div class="markdown-body" v-html="activeLevelCard.html"/>
                      </div>
                    </div>
                  </div>
                </div>
                <a-empty v-else description="暂无知识点内容"/>
              </div>
              <div class="knowledge-actions">
                <a-button type="primary" size="large" @click="handleNavigateToTest">
                  <template #icon>
                    <PlayCircleOutlined/>
                  </template>
                  开始练习
                </a-button>
              </div>
            </section>
          </div>
        </div>
      </template>

      <a-empty v-else-if="!loading" description="尚未加载学习内容"/>
    </a-spin>
  </div>
</template>

<style scoped>
.learning-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
  min-height: 100%;
  padding-bottom: 12px;
  background: linear-gradient(160deg, #f5f7fb 0%, #ecf2ff 55%, #f7f8ff 100%);
}

.learning-page__error {
  margin-bottom: 4px;
}

.content-container {
  display: flex;
  justify-content: center;
  width: 100%;
  padding: 0 12px;
  box-sizing: border-box;
  backdrop-filter: blur(2px);
}

.page-stack {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1280px;
  gap: 24px;
}

.learning-page--mobile .content-container {
  padding: 0 8px;
}

.learning-page--mobile .page-stack {
  gap: 20px;
}

.panel {
  background: rgba(255, 255, 255, 0.92);
  border-radius: 18px;
  border: 1px solid rgba(209, 213, 219, 0.6);
  box-shadow: 0 20px 45px rgba(79, 70, 229, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}


.panel-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 18px 22px 16px;
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.08), rgba(236, 233, 255, 0.5));
  border-bottom: 1px solid rgba(199, 210, 254, 0.65);
}

.panel-icon {
  font-size: 20px;
  color: #4f46e5;
  margin-top: 2px;
}

.panel-title {
  margin: 0;
  font-size: 19px;
  font-weight: 600;
  color: #1e1b4b;
}

.panel-subtitle {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.panel-body {
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
}

.example-panel {
  flex: 1;
}

.exploration-content {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: 24px;
  flex: 1;
  min-height: 320px;
}

.preview-section {
  flex: 1;
  min-height: 280px;
}

.ratio-16x9 {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(17, 24, 39, 0.03);
}

.ratio-16x9 iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff;
}

.code-section {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-content {
  background: linear-gradient(135deg, #f9fafe 0%, #f1f5ff 100%);
  border: 1px solid rgba(191, 219, 254, 0.7);
  border-radius: 14px;
  padding: 18px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1f2937;
  margin-bottom: 12px;
}

.info-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.code-display {
  flex: 1;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  padding: 14px;
  font-family: 'Menlo', 'Courier New', monospace;
  font-size: 13px;
  color: #111827;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid rgba(203, 213, 225, 0.85);
  line-height: 1.7;
}

.code-panel-footer {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: auto;
}

.selector-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selector-toggle-container {
  border-top: 1px dashed #dbe0ea;
  padding-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.toggle-text {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.toggle-hint {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.knowledge-panel {
  gap: 0;
}

.level-card {
  position: relative;
  border-radius: 16px;
  border: 1px solid rgba(196, 181, 253, 0.65);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.95), rgba(237, 233, 254, 0.85));
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  display: flex;
  flex-direction: column;
}

.levels-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.level-card--compact {
  padding: 18px;
  min-height: 150px;
  cursor: pointer;
}

.level-card__badge {
  font-weight: 700;
  color: #4338ca;
  font-size: 14px;
  margin-bottom: 8px;
}

.level-header h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #312e81;
}

.level-summary {
  margin: 6px 0 0;
  color: #5b21b6;
  font-size: 14px;
  line-height: 1.6;
}

.level-summary--compact {
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.level-card__hint {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #4c1d95;
  font-size: 13px;
  font-weight: 600;
  opacity: 0.85;
}

.level-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 360px;
}

.level-detail__actions {
  display: flex;
  justify-content: flex-end;
}

.level-card--expanded {
  padding: 26px 24px;
  box-shadow: 0 18px 40px rgba(168, 85, 247, 0.18);
  border-color: #a855f7;
  flex: 1;
  cursor: default;
}

.level-body {
  margin-top: 18px;
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.knowledge-actions {
  padding: 18px 22px 22px;
  border-top: 1px solid rgba(199, 210, 254, 0.6);
  display: flex;
  justify-content: flex-end;
}

.knowledge-actions .ant-btn {
  min-width: 160px;
}

.selector-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.selector-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: rgba(248, 250, 255, 0.85);
  border: 1px solid rgba(191, 219, 254, 0.7);
  border-radius: 12px;
  padding: 14px;
}

.selector-title {
  font-weight: 600;
  color: #1d4ed8;
}

.selector-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.topic-collapse :deep(.ant-collapse-header) {
  font-weight: 600;
  color: #1f2937;
  padding: 12px 16px !important;
}

.topic-collapse :deep(.ant-collapse-item-active) .ant-collapse-header {
  color: #4338ca;
}

.markdown-body {
  line-height: 1.7;
  color: #1f2937;
}

.markdown-body :deep(p) {
  margin-bottom: 12px;
}

.markdown-body :deep(pre) {
  background: #111827;
  color: #f9fafb;
  padding: 14px;
  border-radius: 10px;
  overflow-x: auto;
}

.markdown-body :deep(code) {
  background: rgba(99, 102, 241, 0.12);
  border-radius: 4px;
  padding: 2px 6px;
  font-family: 'Menlo', 'Courier New', monospace;
  font-size: 13px;
}

@media (max-width: 1280px) {
  .page-stack {
    gap: 20px;
  }
}

@media (max-width: 1024px) {
  .exploration-content {
    grid-template-columns: 1fr;
    gap: 18px;
  }

  .levels-overview {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  }
}

@media (max-width: 768px) {
  .panel {
    border-radius: 16px;
  }

  .panel-body {
    padding: 16px;
  }

  .exploration-content {
    min-height: 0;
  }

  .knowledge-actions {
    padding: 12px 16px 16px;
  }

  .levels-overview {
    grid-template-columns: 1fr;
  }
}
</style>
