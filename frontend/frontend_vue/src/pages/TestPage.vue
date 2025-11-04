<script setup lang="ts">
import {ref, onMounted, onUnmounted, computed, nextTick} from 'vue'
import {useRoute, useRouter} from 'vue-router'
import {message} from 'ant-design-vue'
import {
  FileTextOutlined,
  BarChartOutlined,
  BulbOutlined,
  RobotOutlined,
  ClockCircleOutlined,
  CheckOutlined
} from '@ant-design/icons-vue'
import {marked} from 'marked'
import * as monaco from 'monaco-editor'
import loader from '@monaco-editor/loader'
import {getTestTaskTestTasksTopicIdGet} from '@/api/testTasks'
import {
  submitTest2SubmissionSubmitTest2Post,
  getSubmissionResultSubmissionSubmitTest2ResultTaskIdGet
} from '@/api/submission'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const testTask = ref<API.TestTask | null>(null)
const testResult = ref<API.TestSubmissionResponse | null>(null)
const currentCode = ref<API.CodeContent>({html: '', css: '', js: ''})
const activeTab = ref('html')
const showAskAI = ref(false)
const chatMessages = ref<Array<{ role: 'user' | 'ai'; content: string; timestamp?: string }>>([])
const aiAskCount = ref(0)
const submissionCount = ref(0)
const failedSubmissionCount = ref(0)
const participantId = ref('')
const htmlEditor = ref<monaco.editor.IStandaloneCodeEditor | null>(null)
const cssEditor = ref<monaco.editor.IStandaloneCodeEditor | null>(null)
const jsEditor = ref<monaco.editor.IStandaloneCodeEditor | null>(null)
const htmlEditorRef = ref<HTMLElement | null>(null)
const cssEditorRef = ref<HTMLElement | null>(null)
const jsEditorRef = ref<HTMLElement | null>(null)

// 计算属性
const hasCodeContent = computed(() => {
  return currentCode.value.html || currentCode.value.css || currentCode.value.js
})

const parsedDescription = computed(() => {
  if (!testTask.value?.description_md) return ''
  return marked(testTask.value.description_md)
})

// 响应式布局计算
const isMobile = computed(() => {
  return window.innerWidth <= 768
})

// 基础样式
const baseStyles = {
  gap: '16px',
  padding: isMobile.value ? '12px' : '20px',
  panelBorderRadius: '6px',
  panelBorder: '1px solid #d9d9d9',
  panelBackground: '#fff',
  headerBackground: '#fafafa',
  headerBorder: '1px solid #f0f0f0',
  footerBackground: '#fafafa',
  footerBorder: '1px solid #f0f0f0'
}

// 页面主容器样式
const testPageStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: isMobile.value ? '1fr' : '1fr 2fr',
  gridTemplateRows: isMobile.value
    ? 'auto auto 400px'
    : '1fr 1fr',
  gap: baseStyles.gap,
  height: '100%',
  padding: baseStyles.padding,
  width: '100%',
  boxSizing: 'border-box'
}))

// 通用面板样式
const panelStyle = {
  border: baseStyles.panelBorder,
  borderRadius: baseStyles.panelBorderRadius,
  background: baseStyles.panelBackground,
  display: 'flex',
  flexDirection: 'column' as const,
  overflow: 'hidden'
}

// 面板头部样式
const panelHeaderStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '12px 16px',
  borderBottom: baseStyles.headerBorder,
  background: baseStyles.headerBackground,
  borderRadius: `${baseStyles.panelBorderRadius} ${baseStyles.panelBorderRadius} 0 0`,
  flexShrink: 0
}

// 面板内容样式
const panelContentStyle = {
  flex: '1',
  padding: '16px',
  overflowY: 'auto' as const,
  minHeight: '0'
}

// 面板底部样式
const panelFooterStyle = {
  padding: '12px 16px',
  borderTop: baseStyles.footerBorder,
  background: baseStyles.footerBackground,
  borderRadius: `0 0 ${baseStyles.panelBorderRadius} ${baseStyles.panelBorderRadius}`,
  flexShrink: 0
}

// 测试要求区域样式
const testRequirementsStyle = computed(() => ({
  ...panelStyle,
  gridRow: isMobile.value ? 'auto' : '1',
  gridColumn: isMobile.value ? '1' : '1',
  minHeight: isMobile.value ? 'auto' : '300px'
}))

// 测试结果区域样式
const testResultsStyle = computed(() => ({
  ...panelStyle,
  gridRow: isMobile.value ? 'auto' : '2',
  gridColumn: isMobile.value ? '1' : '1',
  minHeight: isMobile.value ? 'auto' : '250px'
}))

// 编辑器区域样式
const editorContainerStyle = computed(() => ({
  ...panelStyle,
  gridRow: isMobile.value ? 'auto' : '1 / 3',
  gridColumn: isMobile.value ? '1' : '2',
  minHeight: isMobile.value ? '400px' : 'auto'
}))

// 编辑器标签样式
const editorTabsStyle = {
  marginLeft: 'auto',
  display: 'flex',
  gap: '4px'
}

// 编辑器内容区域样式
const editorContentStyle = {
  flex: '1',
  position: 'relative' as const,
  minHeight: '0'
}

// 代码编辑器样式
const codeEditorStyle = {
  height: '100%',
  width: '100%'
}

// 加载占位符样式
const loadingPlaceholderStyle = {
  display: 'flex',
  flexDirection: 'column' as const,
  alignItems: 'center',
  justifyContent: 'center',
  height: '100%',
  color: '#666',
  textAlign: 'center' as const
}

// 结果占位符样式
const resultPlaceholderStyle = {
  ...loadingPlaceholderStyle,
  color: '#999'
}

// 测试结果通过样式
const testResultPassedStyle = {
  color: '#52c41a',
  '& h4': {
    color: '#52c41a',
    marginBottom: '8px'
  }
}

// 测试结果失败样式
const testResultFailedStyle = {
  color: '#ff4d4f',
  '& h4': {
    color: '#ff4d4f',
    marginBottom: '8px'
  }
}

// Markdown内容样式
const markdownContentStyle = {
  lineHeight: 1.6,
  '& h1, h2, h3, h4, h5, h6': {
    marginTop: '16px',
    marginBottom: '8px'
  },
  '& p': {
    marginBottom: '12px'
  },
  '& ul, ol': {
    paddingLeft: '20px',
    marginBottom: '12px'
  },
  '& pre': {
    backgroundColor: '#f5f5f5',
    padding: '12px',
    borderRadius: '4px',
    overflowX: 'auto',
    marginBottom: '12px'
  },
  '& code': {
    backgroundColor: '#f5f5f5',
    padding: '2px 4px',
    borderRadius: '3px',
    fontFamily: "'Monaco', 'Menlo', 'Ubuntu Mono', monospace",
    fontSize: '13px'
  }
}

// Monaco Editor 初始化函数
async function initializeMonacoEditor() {
  try {
    // 配置 Monaco Editor
    const monacoInstance = await loader.init()
    
    // 创建 HTML 编辑器
    if (htmlEditorRef.value) {
      htmlEditor.value = monacoInstance.editor.create(htmlEditorRef.value, {
        value: currentCode.value.html,
        language: 'html',
        theme: 'vs',
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 13,
        lineNumbers: 'on',
        automaticLayout: true
      })

      // 监听内容变化
      htmlEditor.value.onDidChangeModelContent(() => {
        currentCode.value.html = htmlEditor.value?.getValue() || ''
      })
    }

    // 创建 CSS 编辑器
    if (cssEditorRef.value) {
      cssEditor.value = monacoInstance.editor.create(cssEditorRef.value, {
        value: currentCode.value.css,
        language: 'css',
        theme: 'vs',
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 13,
        lineNumbers: 'on',
        automaticLayout: true
      })

      // 监听内容变化
      cssEditor.value.onDidChangeModelContent(() => {
        currentCode.value.css = cssEditor.value?.getValue() || ''
      })
    }

    // 创建 JS 编辑器
    if (jsEditorRef.value) {
      jsEditor.value = monacoInstance.editor.create(jsEditorRef.value, {
        value: currentCode.value.js,
        language: 'javascript',
        theme: 'vs',
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 13,
        lineNumbers: 'on',
        automaticLayout: true
      })

      // 监听内容变化
      jsEditor.value.onDidChangeModelContent(() => {
        currentCode.value.js = jsEditor.value?.getValue() || ''
      })
    }
  } catch (error) {
    console.error('Monaco Editor 初始化失败:', error)
    message.error('代码编辑器初始化失败')
  }
}

// 初始化
onMounted(async () => {
  await initializePage()

  // 等待 DOM 更新后初始化 Monaco Editor
  await nextTick()
  await initializeMonacoEditor()
})

// 组件卸载时清理编辑器
onUnmounted(() => {
  // 销毁 Monaco Editors
  htmlEditor.value?.dispose()
  cssEditor.value?.dispose()
  jsEditor.value?.dispose()
})

async function initializePage() {
  try {
    // 优先从路由参数获取topicId，其次从查询参数获取
    let topicId = route.params.topicId as string || route.query.topic as string

    // 如果都没有，尝试获取默认题目（比如1_1）
    if (!topicId) {
      topicId = getDefaultTopicId()
      message.info(`未指定题目，加载默认题目: ${topicId}`)
    }

    if (!topicId) {
      message.error('无效的测试链接')
      return
    }

    // 获取参与者ID
    participantId.value = localStorage.getItem('participantId') || 'anonymous'

    // 加载测试任务
    await loadTestTask(topicId)

  } catch (error) {
    console.error('初始化页面时出错:', error)
    message.error('无法加载测试任务')
  }
}

// 获取默认题目ID
function getDefaultTopicId(): string {
  // 可以根据用户进度从localStorage或后端获取
  // 这里简化处理，返回第一个题目
  const learnedNodes = JSON.parse(localStorage.getItem('learnedNodes') || '[]')

  // 简单的逻辑：如果没有学习记录，从1_1开始
  if (learnedNodes.length === 0) {
    return '1_1'
  }

  // 如果有学习记录，找到下一个未学习的题目
  const allTopics = [
    '1_1', '1_2', '1_3',
    '2_1', '2_2', '2_3',
    '3_1', '3_2', '3_3',
    '4_1', '4_2', '4_3',
    '5_1', '5_2', '5_3',
    '6_1', '6_2', '6_3'
  ]

  for (const topic of allTopics) {
    if (!learnedNodes.includes(topic)) {
      return topic
    }
  }

  return '1_1' // 兜底
}

// 导航到指定题目
function navigateToTest(topicId: string, queryParams?: Record<string, string>) {
  router.push({
    name: 'test',
    params: {topicId},
    query: queryParams
  })
}

// 导航到学习页面
function navigateToLearning(topicId: string, queryParams?: Record<string, string>) {
  router.push({
    name: 'learning',
    params: {topicId},
    query: queryParams
  })
}

// 获取下一个题目
function getNextTopic(currentTopicId: string): string | null {
  const [chapter, section] = currentTopicId.split('_').map(Number)

  // 如果是章节测试（如 2_end）
  if (currentTopicId.endsWith('_end')) {
    const chapterNum = parseInt(currentTopicId.replace('_end', ''))
    const nextChapterFirst = `${chapterNum + 1}_1`
    return nextChapterFirst
  }

  // 普通题目
  let nextChapter = chapter
  let nextSection = section + 1

  // 处理章节边界
  if (nextSection > 3) {
    nextChapter += 1
    nextSection = 1
  }

  // 检查是否超出范围
  if (nextChapter > 6) {
    return null // 所有题目完成
  }

  return `${nextChapter}_${nextSection}`
}

// 处理测试成功
function handleTestSuccess(currentTopicId: string) {
  // 标记当前题目为已学习
  const learnedNodes = JSON.parse(localStorage.getItem('learnedNodes') || '[]')
  if (!learnedNodes.includes(currentTopicId)) {
    learnedNodes.push(currentTopicId)
    localStorage.setItem('learnedNodes', JSON.stringify(learnedNodes))
  }

  // 获取下一个题目
  const nextTopic = getNextTopic(currentTopicId)

  if (nextTopic) {
    // 延迟跳转，给用户时间看到成功消息
    setTimeout(() => {
      message.success(`准备进入下一个题目: ${nextTopic}`, 2)
      navigateToTest(nextTopic)
    }, 2000)
  } else {
    // 所有题目完成
    setTimeout(() => {
      message.success('恭喜！您已完成所有题目！', 3)
      router.push('/graph')
    }, 2000)
  }
}

async function loadTestTask(topicId: string) {
  try {
    loading.value = true
    const response = await getTestTaskTestTasksTopicIdGet({topic_id: topicId})

    if (response.data?.code === 200 && response.data?.data) {
      testTask.value = response.data.data
      currentCode.value = response.data.data.start_code
    } else {
      message.error(response.data?.message || '获取测试任务失败')
    }
  } catch (error) {
    console.error('加载测试任务时出错:', error)
    message.error('加载测试任务失败')
  } finally {
    loading.value = false
  }
}

// 提交代码
async function submitCode() {
  if (!testTask.value) return

  try {
    submitting.value = true
    const topicId = testTask.value.topic_id

    const submissionData: API.TestSubmissionRequest = {
      participant_id: participantId.value,
      topic_id: topicId,
      code: currentCode.value
    }

    // 使用异步提交接口
    const response = await submitTest2SubmissionSubmitTest2Post(submissionData)

    if (response.data?.code === 200 && response.data?.data) {
      // 轮询获取结果
      await pollSubmissionResult(response.data.data.task_id)
    } else {
      message.error(response.data?.message || '提交失败')
    }
  } catch (error) {
    console.error('提交代码时出错:', error)
    message.error('提交失败: ' + (error as Error).message)
  } finally {
    submitting.value = false
  }
}

// 轮询提交结果
async function pollSubmissionResult(taskId: string) {
  const maxAttempts = 30 // 最多轮询30次
  let attempts = 0

  const poll = async () => {
    try {
      attempts++
      const response = await getSubmissionResultSubmissionSubmitTest2ResultTaskIdGet({task_id: taskId})

      if (response.data?.code === 200 && response.data?.data) {
        testResult.value = response.data.data
        submissionCount.value++

        if (!response.data.data.passed) {
          failedSubmissionCount.value++
        } else {
          // 测试通过，标记为已学习并处理跳转
          handleTestSuccess(testTask.value!.topic_id)
        }

        // 根据结果显示AI询问按钮
        showAskAI.value = !response.data.data.passed

        message.success(response.data.data.passed ? '恭喜！测试通过！' : '测试未通过，请继续努力')
      } else if (attempts < maxAttempts) {
        // 继续轮询
        setTimeout(poll, 1000)
      } else {
        message.error('获取评测结果超时')
      }
    } catch (error) {
      console.error('获取评测结果时出错:', error)
      if (attempts < maxAttempts) {
        setTimeout(poll, 1000)
      } else {
        message.error('获取评测结果失败')
      }
    }
  }

  poll()
}

// 询问AI
async function askAI() {
  if (!testTask.value || !testResult.value) return

  try {
    const question = `您好！我注意到您的代码测试未通过。我可以帮您分析测试结果中的错误原因。

**测试结果:**
${testResult.value.message || '无具体信息'}

**详细信息:**
${(testResult.value.details || []).join('\n') || '无详细信息'}

您希望我详细解释哪个检查点的错误原因呢？请告诉我您的具体问题，我会针对性地为您解答！`

    // 添加AI消息到聊天记录
    chatMessages.value.push({
      role: 'ai',
      content: question,
      timestamp: new Date().toISOString()
    })

    aiAskCount.value++

    // 记录行为事件（如果需要的话）
    console.log('AI询问次数:', aiAskCount.value)

  } catch (error) {
    console.error('询问AI时出错:', error)
    message.error('询问AI失败')
  }
}

// Tab切换
function handleTabChange(tab: string) {
  activeTab.value = tab
  
  // 延迟重新布局当前编辑器，确保 DOM 更新完成
  setTimeout(() => {
    const currentEditor = tab === 'html' ? htmlEditor.value : 
                         tab === 'css' ? cssEditor.value : jsEditor.value
    currentEditor?.layout()
    currentEditor?.focus()
  }, 100)
}

// 获取解题思路
async function getProblemSolvingHint() {
  if (!testTask.value) return

  try {
    const hintMessage = `您好！我注意到您点击了"给点灵感"按钮。我可以为您提供一些关于这道题的解题思路和关键知识点。

**题目要求：**
${testTask.value.description_md || '暂无描述'}

**您希望我提供哪方面的帮助？**
1. 整体解题思路分析
2. 关键知识点讲解
3. 代码实现要点
4. 常见错误及调试建议

请告诉我您的需求，我会针对性地为您解答！`

    chatMessages.value.push({
      role: 'ai',
      content: hintMessage,
      timestamp: new Date().toISOString()
    })

  } catch (error) {
    console.error('获取解题思路时出错:', error)
    message.error('获取解题思路失败')
  }
}
</script>

<template>
  <div id="TestPage" :style="testPageStyle as any">
    <!-- 测试要求区域 -->
    <div :style="testRequirementsStyle as any">
      <div :style="panelHeaderStyle as any">
        <FileTextOutlined/>
        <h3 style="margin: 0; font-size: 16px; font-weight: 600;">测试要求</h3>
      </div>
      <div :style="panelContentStyle as any">
        <div v-if="loading" :style="loadingPlaceholderStyle as any">
          <a-spin size="large"/>
          <p>加载中...</p>
        </div>
        <div v-else-if="testTask" :style="markdownContentStyle as any" v-html="parsedDescription"></div>
        <div v-else :style="loadingPlaceholderStyle as any">
          <p>无法加载测试要求</p>
        </div>
      </div>
      <div :style="panelFooterStyle as any">
        <a-button
          type="primary"
          @click="getProblemSolvingHint"
          :disabled="loading"
        >
          <BulbOutlined/>
          给点灵感
        </a-button>
      </div>
    </div>

    <!-- 测试结果区域 -->
    <div :style="testResultsStyle as any">
      <div :style="panelHeaderStyle as any">
        <BarChartOutlined/>
        <h3 style="margin: 0; font-size: 16px; font-weight: 600;">测试结果</h3>
      </div>
      <div :style="panelContentStyle as any">
        <div v-if="!testResult" :style="resultPlaceholderStyle as any">
          <ClockCircleOutlined style="font-size: 32px; color: #999;"/>
          <p>请先开始写代码，然后点击"提交"，稍等后就会出现测试结果</p>
        </div>
        <div v-else :style="testResult.passed ? testResultPassedStyle : testResultFailedStyle">
          <h4>
            {{ testResult.passed ? '✅ 恭喜！通过测试！' : '❌ 未通过测试' }}
          </h4>
          <p>{{ testResult.message || '' }}</p>
          <div v-if="testResult.details && testResult.details.length > 0">
            <h5>详细信息:</h5>
            <ul>
              <li v-for="(detail, index) in testResult.details" :key="index">
                {{ detail }}
              </li>
            </ul>
          </div>
        </div>
      </div>
      <div v-if="showAskAI" :style="panelFooterStyle as any">
        <a-button type="primary" @click="askAI">
          <RobotOutlined/>
          询问AI
        </a-button>
      </div>
    </div>

    <!-- 编辑器区域 -->
    <div :style="editorContainerStyle as any">
      <div :style="panelHeaderStyle as any">
        <h3 style="margin: 0; font-size: 16px; font-weight: 600;">编辑器</h3>
        <div :style="editorTabsStyle as any">
          <div>
            <a-button
              :type="activeTab === 'html' ? 'primary' : 'default'"
              @click="handleTabChange('html')"
            >
              HTML
            </a-button>
            <a-button
              :type="activeTab === 'css' ? 'primary' : 'default'"
              @click="handleTabChange('css')"
            >
              CSS
            </a-button>
            <a-button
              :type="activeTab === 'js' ? 'primary' : 'default'"
              @click="handleTabChange('js')"
            >
              JS
            </a-button>
          </div>
        </div>
      </div>

      <div :style="editorContentStyle as any">
        <!-- HTML编辑器 -->
        <div v-show="activeTab === 'html'" :style="codeEditorStyle as any">
          <div 
            ref="htmlEditorRef"
            :style="{ height: '100%', width: '100%' }"
          ></div>
        </div>

        <!-- CSS编辑器 -->
        <div v-show="activeTab === 'css'" :style="codeEditorStyle as any">
          <div 
            ref="cssEditorRef"
            :style="{ height: '100%', width: '100%' }"
          ></div>
        </div>

        <!-- JS编辑器 -->
        <div v-show="activeTab === 'js'" :style="codeEditorStyle as any">
          <div 
            ref="jsEditorRef"
            :style="{ height: '100%', width: '100%' }"
          ></div>
        </div>
      </div>

      <div :style="panelFooterStyle as any">
        <a-button
          type="primary"
          @click="submitCode"
          :loading="submitting"
          :disabled="!hasCodeContent || loading"
        >
          <CheckOutlined/>
          提交
        </a-button>
      </div>
    </div>
  </div>
</template>

