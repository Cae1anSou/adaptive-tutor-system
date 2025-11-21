<template>
  <div class="ai-sider-container">

    <div class="sider-header">
      <div class="header-title">
        <robot-outlined class="icon" />
        <span>AI Assistant</span>
      </div>
      <span class="model-tag">GPT-4o</span>
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
import { ref, nextTick } from 'vue';
import { RobotOutlined, EditOutlined, ArrowUpOutlined, LoadingOutlined } from '@ant-design/icons-vue';
import MarkdownIt from 'markdown-it';

// --- 逻辑部分完全保持不变 ---
interface Message {
  role: 'user' | 'assistant';
  content: string;
  isStreaming?: boolean;
  isEditing?: boolean;
}

const messages = ref<Message[]>([
  { role: 'assistant', content: '你好！我是你的 AI 助手，有什么可以帮你的吗？' }
]);
const inputMessage = ref('');
const editingContent = ref('');
const isGlobalLoading = ref(false);
const isInputFocused = ref(false);
const scrollRef = ref<HTMLElement | null>(null);
const md = new MarkdownIt({ html: true, linkify: true });

const scrollToBottom = async () => {
  await nextTick();
  if (scrollRef.value) {
    scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
  }
};

const renderMarkdown = (text: string) => md.render(text);

const simulateStreamResponse = async () => {
  isGlobalLoading.value = true;
  const aiMsgIndex = messages.value.push({ role: 'assistant', content: '', isStreaming: true }) - 1;
  await scrollToBottom();

  const fullResponse = "这是一个模拟的流式回复。\n\n现在这个组件使用的是 **纯 CSS**，可以直接在 Antd 项目中使用而没有冲突。\n- 列表项 1\n- 列表项 2";
  const chars = fullResponse.split('');

  for (let char of chars) {
    await new Promise(r => setTimeout(r, 30));
    messages.value[aiMsgIndex].content += char;
    scrollToBottom();
  }

  messages.value[aiMsgIndex].isStreaming = false;
  isGlobalLoading.value = false;
};

const handleSend = () => {
  const content = inputMessage.value.trim();
  if (!content || isGlobalLoading.value) return;
  messages.value.push({ role: 'user', content });
  inputMessage.value = '';
  scrollToBottom();
  simulateStreamResponse();
};

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
  messages.value = messages.value.slice(0, index);
  messages.value.push({ role: 'user', content: newContent });
  simulateStreamResponse();
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
