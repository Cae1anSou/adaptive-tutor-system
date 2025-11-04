<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { 
  FileTextOutlined, 
  BarChartOutlined, 
  BulbOutlined, 
  RobotOutlined,
  MessageOutlined,
  UserOutlined,
  ClockCircleOutlined,
  CheckOutlined
} from '@ant-design/icons-vue'
import { getTestTaskTestTasksTopicIdGet } from '@/api/testTasks'
import { submitTest2SubmissionSubmitTest2Post, getSubmissionResultSubmissionSubmitTest2ResultTaskIdGet } from '@/api/submission'
import { chatWithAi2ChatAiChat2Post, getChatResultChatAiChat2ResultTaskIdGet } from '@/api/chat'

const route = useRoute()
const router = useRouter()

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const testTask = ref<API.TestTask | null>(null)
const testResult = ref<API.TestSubmissionResponse | null>(null)
const currentCode = ref<API.CodeContent>({ html: '', css: '', js: '' })
const activeTab = ref('html')
const showAskAI = ref(false)
const chatMessages = ref<Array<{ role: 'user' | 'ai'; content: string; timestamp?: string }>>([])
const userMessage = ref('')
const aiAskCount = ref(0)
const submissionCount = ref(0)
const failedSubmissionCount = ref(0)
const participantId = ref('')

// 计算属性
const hasCodeContent = computed(() => {
  return currentCode.value.html || currentCode.value.css || currentCode.value.js
})

// 初始化
onMounted(async () => {
  await initializePage()
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
    params: { topicId },
    query: queryParams
  })
}

// 导航到学习页面
function navigateToLearning(topicId: string, queryParams?: Record<string, string>) {
  router.push({
    name: 'learning',
    params: { topicId },
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
    const response = await getTestTaskTestTasksTopicIdGet({ topic_id: topicId })
    
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
      const response = await getSubmissionResultSubmissionSubmitTest2ResultTaskIdGet({ task_id: taskId })
      
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

// 发送用户消息
async function sendMessage() {
  if (!userMessage.value.trim()) return
  
  const messageContent = userMessage.value.trim()
  userMessage.value = ''
  
  // 添加用户消息到聊天记录
  chatMessages.value.push({
    role: 'user',
    content: messageContent,
    timestamp: new Date().toISOString()
  })
  
  try {
    // 构建聊天请求
    const chatRequest: API.ChatRequest = {
      participant_id: participantId.value,
      user_message: messageContent,
      conversation_history: chatMessages.value.slice(0, -1).map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp
      })),
      code_context: currentCode.value,
      mode: 'test',
      content_id: testTask.value?.topic_id,
      test_results: testResult.value ? [testResult.value] : undefined
    }
    
    // 发送聊天请求
    const response = await chatWithAi2ChatAiChat2Post(chatRequest)
    
    if (response.data?.code === 200 && response.data?.data) {
      // 轮询获取AI回复
      await pollChatResult(response.data.data.task_id)
    } else {
      message.error(response.data?.message || '发送消息失败')
    }
    
  } catch (error) {
    console.error('发送消息时出错:', error)
    message.error('发送消息失败')
  }
}

// 轮询聊天结果
async function pollChatResult(taskId: string) {
  const maxAttempts = 30
  let attempts = 0
  
  const poll = async () => {
    try {
      attempts++
      const response = await getChatResultChatAiChat2ResultTaskIdGet({ task_id: taskId })
      
      if (response.data?.code === 200 && response.data?.data) {
        // 添加AI回复到聊天记录
        chatMessages.value.push({
          role: 'ai',
          content: response.data.data.ai_response,
          timestamp: new Date().toISOString()
        })
        
        aiAskCount.value++
      } else if (attempts < maxAttempts) {
        setTimeout(poll, 1000)
      } else {
        message.error('获取AI回复超时')
      }
    } catch (error) {
      console.error('获取AI回复时出错:', error)
      if (attempts < maxAttempts) {
        setTimeout(poll, 1000)
      } else {
        message.error('获取AI回复失败')
      }
    }
  }
  
  poll()
}


// Tab切换
function handleTabChange(tab: string) {
  activeTab.value = tab
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
  <div id="TestPage" class="test-page">
    <!-- 测试要求区域 -->
    <div class="test-requirements-container panel">
      <div class="panel-header">
        <FileTextOutlined />
        <h3>测试要求</h3>
      </div>
      <div class="panel-content markdown-content">
        <div v-if="loading" class="loading-placeholder">
          <a-spin size="large" />
          <p>加载中...</p>
        </div>
        <div v-else-if="testTask" v-html="testTask.description_md"></div>
        <div v-else class="error-placeholder">
          <p>无法加载测试要求</p>
        </div>
      </div>
      <div class="panel-footer">
        <a-button 
          type="primary" 
          @click="getProblemSolvingHint"
          :disabled="loading"
        >
          <BulbOutlined />
          给点灵感
        </a-button>
      </div>
    </div>

    <!-- 测试结果区域 -->
    <div class="test-results-container panel">
      <div class="panel-header">
        <BarChartOutlined />
        <h3>测试结果</h3>
      </div>
      <div class="panel-content">
        <div v-if="!testResult" class="result-placeholder">
          <ClockCircleOutlined style="font-size: 32px; color: #999;" />
          <p>请先开始写代码，然后点击"提交"，稍等后就会出现测试结果</p>
        </div>
        <div v-else :class="testResult.passed ? 'test-result-passed' : 'test-result-failed'">
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
      <div v-if="showAskAI" class="panel-footer">
        <a-button type="primary" @click="askAI">
          <RobotOutlined />
          询问AI
        </a-button>
      </div>
    </div>

    <!-- 编辑器区域 -->
    <div class="editor-container panel">
      <div class="panel-header">
        <h3>编辑器</h3>
        <div class="editor-tabs">
          <div class="editor-tabs-left">
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

      <div class="editor-content">
        <!-- HTML编辑器 -->
        <div v-show="activeTab === 'html'" class="code-editor">
          <a-textarea
            v-model:value="currentCode.html"
            placeholder="在这里输入HTML代码..."
            :rows="15"
          />
        </div>

        <!-- CSS编辑器 -->
        <div v-show="activeTab === 'css'" class="code-editor">
          <a-textarea
            v-model:value="currentCode.css"
            placeholder="在这里输入CSS代码..."
            :rows="15"
          />
        </div>

        <!-- JS编辑器 -->
        <div v-show="activeTab === 'js'" class="code-editor">
          <a-textarea
            v-model:value="currentCode.js"
            placeholder="在这里输入JavaScript代码..."
            :rows="15"
          />
        </div>
      </div>

      <div class="editor-actions">
        <a-button 
          type="primary" 
          @click="submitCode"
          :loading="submitting"
          :disabled="!hasCodeContent || loading"
        >
          <CheckOutlined />
          提交
        </a-button>
      </div>
    </div>

    <!-- 修改建议区域 -->
    <div class="chat-container panel">
      <div class="panel-header">
        <MessageOutlined />
        <h3>修改建议</h3>
      </div>
      <div class="chat-content">
        <div class="chat-messages">
          <div 
            v-for="(msg, index) in chatMessages" 
            :key="index"
            :class="['message', msg.role === 'user' ? 'user-message' : 'ai-message']"
          >
            <div class="message-avatar">
              <UserOutlined v-if="msg.role === 'user'" />
              <RobotOutlined v-else />
            </div>
            <div class="message-content">
              <div v-html="msg.content"></div>
            </div>
          </div>
        </div>
        <div class="chat-input">
          <a-input-search
            v-model:value="userMessage"
            placeholder="在这里输入你的问题..."
            enter-button="提问"
            @search="sendMessage"
            :disabled="loading"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.test-page {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 16px;
  height: 100%;
  padding: 16px;
}

.panel {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
  border-radius: 6px 6px 0 0;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.panel-content {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}

.panel-footer {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
  border-radius: 0 0 6px 6px;
}

/* 测试要求区域 */
.test-requirements-container {
  grid-row: 1;
}

.loading-placeholder, .error-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.markdown-content {
  line-height: 1.6;
}

/* 测试结果区域 */
.test-results-container {
  grid-row: 2;
}

.result-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  text-align: center;
}

.test-result-passed {
  color: #52c41a;
}

.test-result-failed {
  color: #ff4d4f;
}

.test-result-passed h4 {
  color: #52c41a;
  margin-bottom: 8px;
}

.test-result-failed h4 {
  color: #ff4d4f;
  margin-bottom: 8px;
}

/* 编辑器区域 */
.editor-container {
  grid-row: 1 / 3;
  grid-column: 2;
}

.editor-tabs {
  margin-left: auto;
}

.editor-tabs-left {
  display: flex;
  gap: 4px;
}

.editor-content {
  flex: 1;
  position: relative;
}

.code-editor {
  height: 100%;
}

.code-editor :deep(.ant-input) {
  height: 100% !important;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.4;
  resize: none;
}

.editor-actions {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  background: #fafafa;
  border-radius: 0 0 6px 6px;
}

/* 聊天区域 */
.chat-container {
  grid-row: 1 / 3;
  grid-column: 3;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.message {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.user-message {
  flex-direction: row-reverse;
}

.user-message .message-content {
  background: #1890ff;
  color: white;
  border-radius: 12px 12px 4px 12px;
}

.ai-message .message-content {
  background: #f5f5f5;
  border-radius: 12px 12px 12px 4px;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e6f7ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #1890ff;
  flex-shrink: 0;
}

.user-message .message-avatar {
  background: #1890ff;
  color: white;
}

.message-content {
  max-width: 70%;
  padding: 8px 12px;
  word-wrap: break-word;
}

.chat-input {
  padding: 16px;
  border-top: 1px solid #f0f0f0;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .test-page {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto 1fr auto;
  }
  
  .test-requirements-container,
  .test-results-container,
  .editor-container,
  .chat-container {
    grid-row: auto;
    grid-column: 1;
  }
  
  .editor-container {
    min-height: 400px;
  }
  
  .chat-container {
    min-height: 300px;
  }
}
</style>
