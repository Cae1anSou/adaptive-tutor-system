<template>
  <div class="ai-sider-container">

    <div class="sider-header">
      <div class="header-title">
        <robot-outlined class="icon" />
        <span>AI Assistant</span>
      </div>
      <span class="model-tag">Deepseek-V3.1</span>
    </div>

    <div ref="scrollRef" class="message-list custom-scrollbar">
      <div v-for="(msg, index) in messages" :key="index" class="message-item group">

        <div v-if="msg.role === 'assistant'" class="msg-ai animate-fade-in">
          <div class="avatar-ai">
            <robot-outlined />
          </div>
          <div class="content-wrapper">
            <div class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
            <span v-if="msg.isStreaming" class="cursor-blink"></span>
          </div>
        </div>

        <div v-else-if="msg.role === 'system'" class="msg-system animate-fade-in">
             <div class="system-bubble">
                <div class="system-icon"><bulb-outlined /></div>
                <div class="system-content">{{ msg.content }}</div>
             </div>
        </div>

        <div v-else class="msg-user animate-slide-up">

          <div v-if="!msg.isEditing" class="user-bubble-wrapper">
            <div class="edit-btn-wrapper">
              <button @click="startEditing(index)" class="icon-btn" title="重新编辑">
                <edit-outlined />
              </button>
            </div>
            <div class="user-bubble">
              {{ msg.content }}
            </div>
          </div>

          <div v-else class="edit-box">
            <textarea
              v-model="editingContent"
              rows="3"
              placeholder="修改你的提问..."
            ></textarea>
            <div class="edit-actions">
              <button @click="cancelEditing(index)" class="btn-cancel">取消</button>
              <button @click="confirmEdit(index)" class="btn-confirm">重新发送</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="input-area">
      <div class="input-wrapper" :class="{ 'focused': isInputFocused }">
        <textarea
          v-model="inputMessage"
          @focus="isInputFocused = true"
          @blur="isInputFocused = false"
          @keydown.enter.prevent="handleSend"
          placeholder="输入您的问题..."
          rows="1"
        ></textarea>
        <button
          @click="handleSend"
          :disabled="!inputMessage.trim() || isGlobalLoading"
          class="send-btn"
        >
          <arrow-up-outlined v-if="!isGlobalLoading" />
          <loading-outlined v-else />
        </button>
      </div>
      <p class="disclaimer">AI 生成内容仅供参考</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { RobotOutlined, EditOutlined, ArrowUpOutlined, LoadingOutlined, BulbOutlined } from '@ant-design/icons-vue';
import MarkdownIt from 'markdown-it';
import { message as antMessage } from 'ant-design-vue';

import websocket from '@/api/websocket';
import { chatWithAi2ChatAiChat2Post } from '@/api/chat';
import chatStorage, { type ChatMessage } from '@/utils/chatStorage';
import { useUserStore } from '@/stores/user';
import { useChatContextStore } from '@/stores/chatContext';

// Store & State
const userStore = useUserStore();
const chatContextStore = useChatContextStore();

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  isStreaming?: boolean;
  isEditing?: boolean;
  id?: string; // Optional ID for de-duplication
}

const messages = ref<Message[]>([]);
const inputMessage = ref('');
const editingContent = ref('');
const isGlobalLoading = ref(false);
const isInputFocused = ref(false);
const scrollRef = ref<HTMLElement | null>(null);
const md = new MarkdownIt({ html: true, linkify: true });

// Scroll Helper
const scrollToBottom = async () => {
  await nextTick();
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
  }
};

const renderMarkdown = (text: string) => md.render(text);

// --- Real Logic ---

// 1. Initialize & Load History
const initChat = () => {
  if (userStore.participantId) {
    const history = chatStorage.load(userStore.participantId);
    // Transform storage format to UI format if needed
    messages.value = history.map(h => ({
      role: h.role as any, // 'user' | 'assistant'
      content: h.content
    })) as Message[];
    
    // If empty, add greeting
    if (messages.value.length === 0) {
       messages.value.push({ role: 'assistant', content: '你好！我是你的 AI 助手，有什么可以帮你的吗？' });
    }
    
    scrollToBottom();
  }
};

// 2. WebSocket Subscription
onMounted(() => {
  initChat();
  websocket.connect(); // Explicitly connect
  websocket.subscribe('stream_start', handleStreamStart);
  websocket.subscribe('streaming', handleStreaming);
  websocket.subscribe('stream_end', handleStreamEnd);
  
  // Watch for external triggers (e.g. from TestPage)
  // Input trigger
  watch(() => chatContextStore.pendingMessage, (newMsg) => {
      if (newMsg) {
          inputMessage.value = newMsg;
          chatContextStore.clearPendingMessage();
          handleSend();
      }
  });

  // Message Sync Trigger (From ActiveHint or other sources)
  watch(() => chatContextStore.messages, (newStoreMessages) => {
      if (newStoreMessages && newStoreMessages.length > 0) {
          // Find messages that are not in local state
          // Using a simple check: loop through store messages and see if ID matches
          // Since local messages might not have IDs (from storage), we might need to rely on timestamps or content if ID missing
          // But ActiveHint messages HAVE IDs.
          
          newStoreMessages.forEach(storeMsg => {
             const exists = messages.value.some(m => m.id === storeMsg.id);
             if (!exists) {
                 messages.value.push({
                     role: storeMsg.role as any,
                     content: storeMsg.content,
                     id: storeMsg.id
                 });
                 scrollToBottom();
             }
          });
      }
  }, { deep: true });
});

onUnmounted(() => {
  websocket.unsubscribe('stream_start', handleStreamStart);
  websocket.unsubscribe('streaming', handleStreaming);
  websocket.unsubscribe('stream_end', handleStreamEnd);
});

// 3. WS Handlers
const handleStreamStart = () => {
    isGlobalLoading.value = true;
    messages.value.push({ role: 'assistant', content: '', isStreaming: true });
    scrollToBottom();
};

const handleStreaming = (data: any) => {
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.content += (data.message || '');
        scrollToBottom();
    }
};

const handleStreamEnd = () => {
    isGlobalLoading.value = false;
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg) {
        lastMsg.isStreaming = false;
        // Persist to storage
        if (userStore.participantId) {
            chatStorage.append(userStore.participantId, {
                role: 'assistant',
                content: lastMsg.content,
                ts: Date.now(),
                mode: chatContextStore.mode,
                contentId: chatContextStore.contentId
            });
        }
    }
};

// 4. Send Message
const handleSend = async () => {
  const text = inputMessage.value.trim();
  if (!text || isGlobalLoading.value) return;

  // Add User Message
  messages.value.push({ role: 'user', content: text });
  inputMessage.value = '';
  scrollToBottom();

  // Save user message
  if (userStore.participantId) {
      chatStorage.append(userStore.participantId, {
          role: 'user',
          content: text,
          ts: Date.now(),
          mode: chatContextStore.mode,
          contentId: chatContextStore.contentId
      });
  }

  isGlobalLoading.value = true;

  try {
      // Prepare Context
      let codeContext = { html: '', css: '', js: '' };
      let testResults = null;
      let augmentedMessage = text;

      if (chatContextStore.mode === 'test') {
          // Code Context
          codeContext = { ...chatContextStore.codeContext };
          
          // Test Results Context
          if (chatContextStore.taskContext.status) {
              testResults = [{
                  passed: chatContextStore.taskContext.status === 'success',
                  message: chatContextStore.taskContext.error || ''
              }];
              
              // Append status to message to ensure AI attention
              augmentedMessage += `\n\n[System Context]\nTest Status: ${chatContextStore.taskContext.status}`;
              if (chatContextStore.taskContext.error) {
                  augmentedMessage += `\nError Message: ${chatContextStore.taskContext.error}`;
              }
          }
          
          // Task Description (Optional, if AI needs it explicitly in context)
          if (chatContextStore.taskContext.description) {
             // Just a hint, usually content_id handles this on backend, but we can provide snippet if needed
             // augmentedMessage += `\nTask Description Snippet: ...`;
          }

      } else if (chatContextStore.mode === 'learning') {
          // Selection Context
          if (chatContextStore.selectionContext.code) {
              codeContext.html = chatContextStore.selectionContext.code; // Treat selected HTML as the html context
              
              if (chatContextStore.selectionContext.meta) {
                  augmentedMessage += `\n\n[Selected Element Info]\nMetadata: ${JSON.stringify(chatContextStore.selectionContext.meta)}`;
              }
          }
          
          if (chatContextStore.additionalContext.title) {
               // augmentedMessage += `\nLearning Topic: ${chatContextStore.additionalContext.title}`;
          }
      }

      await chatWithAi2ChatAiChat2Post({
         participant_id: userStore.participantId || '',
         user_message: augmentedMessage,
         conversation_history: messages.value.map(m => ({ role: m.role, content: m.content })),
         mode: chatContextStore.mode,
         content_id: chatContextStore.contentId,
         code_context: codeContext,
         test_results: testResults
      });
  } catch (e) {
      console.error(e);
      antMessage.error('发送失败，请稍后重试');
      isGlobalLoading.value = false;
  }
};

// 5. Editing Logic (Kept mostly same, adjusted to call handleSend)
const startEditing = (index: number) => {
  messages.value.forEach(m => m.isEditing = false);
  messages.value[index].isEditing = true;
  editingContent.value = messages.value[index].content;
};

const cancelEditing = (index: number) => {
  messages.value[index].isEditing = false;
};

const confirmEdit = (index: number) => {
  const newContent = editingContent.value.trim();
  if (!newContent) return;
  
  // Cut off history after this point
  messages.value = messages.value.slice(0, index);
  // Set as input and send
  inputMessage.value = newContent;
  handleSend();
};
</script>

<style scoped>
/* 这里将 Tailwind 的工具类转换为了标准的 CSS
  使用了 CSS 变量来管理灰阶，方便微调
*/
.ai-sider-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: #ffffff;
  border-left: 1px solid #f0f0f0; /* Antd 的边框色 */
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: #333;
}

/* Header */
.sider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #fafafa;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  font-size: 14px;
  color: #333;
}

.header-title .icon {
  font-size: 18px;
  color: #666;
}

.model-tag {
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 4px;
}

/* 消息列表 */
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  scroll-behavior: smooth;
}

/* AI 消息样式 */
.msg-ai {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.avatar-ai {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f0f2f5 0%, #e6e8eb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 4px;
  color: #666;
  font-size: 14px;
}

.content-wrapper {
  flex: 1;
  font-size: 14px;
  line-height: 1.6;
  color: #4b5563;
}

/* 系统消息样式 */
.msg-system {
  display: flex;
  justify-content: center;
  margin: 10px 0;
}

.system-bubble {
  background: #f0f7ff; /* 浅蓝色背景 */
  border: 1px solid #bae0ff;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  max-width: 90%;
  color: #1677ff;
  font-size: 13px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.system-icon {
  font-size: 16px;
  margin-top: 2px;
}

.system-content {
  line-height: 1.5;
  color: #1f2937;
}

/* 用户消息样式 */
.msg-user {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.user-bubble-wrapper {
  position: relative;
  max-width: 85%;
  /* 这里的 group-hover 逻辑需要 CSS 实现：父级 hover 时显示子级 */
}

/* 模拟 Tailwind group-hover */
.message-item:hover .edit-btn-wrapper {
  opacity: 1;
}

.edit-btn-wrapper {
  position: absolute;
  left: -40px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0;
  transition: opacity 0.2s;
}

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  color: #9ca3af;
  border-radius: 50%;
  transition: all 0.2s;
}
.icon-btn:hover {
  color: #333;
  background: #f3f4f6;
}

.user-bubble {
  background: #1f2937; /* 深色背景 */
  color: white;
  padding: 10px 16px;
  border-radius: 16px;
  border-top-right-radius: 2px; /* 特殊圆角 */
  box-shadow: 0 2px 5px rgba(0,0,0,0.05);
  font-size: 14px;
  line-height: 1.5;
}

/* 编辑框模式 */
.edit-box {
  width: 100%;
  max-width: 90%;
  background: white;
  border: 1px solid #e5e7eb;
  padding: 10px;
  border-radius: 12px;
  box-shadow: 0 0 0 2px #f9fafb;
}

.edit-box textarea {
  width: 100%;
  border: none;
  resize: none;
  outline: none;
  font-size: 14px;
  color: #374151;
  background: transparent;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.btn-cancel {
  font-size: 12px;
  color: #9ca3af;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
}
.btn-cancel:hover { color: #4b5563; }

.btn-confirm {
  font-size: 12px;
  background: #1f2937;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-confirm:hover { background: #000; }

/* 底部输入区 */
.input-area {
  padding: 20px;
  background: white;
  border-top: 1px solid #fafafa;
}

.input-wrapper {
  position: relative;
  background: #f9fafb;
  border: 1px solid transparent;
  border-radius: 12px;
  transition: all 0.3s;
}

.input-wrapper.focused {
  background: white;
  border-color: #e5e7eb;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.input-wrapper textarea {
  width: 100%;
  background: transparent;
  border: none;
  outline: none;
  padding: 12px 16px;
  padding-right: 48px; /* 留出按钮位置 */
  resize: none;
  font-size: 14px;
  min-height: 46px;
  max-height: 120px;
}

.send-btn {
  position: absolute;
  right: 8px;
  bottom: 8px;
  border: none;
  background: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  color: #9ca3af;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  color: #1f2937;
  background: #e5e7eb;
}

.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.disclaimer {
  text-align: center;
  font-size: 10px;
  color: #d1d5db;
  margin-top: 8px;
}

/* 动画与工具 */
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e5e7eb; border-radius: 10px; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in { animation: fadeIn 0.3s ease-out forwards; }

.cursor-blink {
  display: inline-block;
  width: 6px;
  height: 16px;
  background: #9ca3af;
  margin-left: 4px;
  vertical-align: middle;
  animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* Markdown 基础样式 (极简版) */
:deep(.markdown-body p) { margin-bottom: 0.8em; }
:deep(.markdown-body ul) { padding-left: 1.5em; list-style-type: disc; margin-bottom: 0.8em; }
:deep(.markdown-body code) { background: #f3f4f6; padding: 2px 4px; border-radius: 4px; font-size: 0.9em; }
:deep(.markdown-body pre) { background: #f3f4f6; padding: 12px; border-radius: 8px; overflow-x: auto; }
</style>
