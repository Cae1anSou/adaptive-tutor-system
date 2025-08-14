/**
 * Chat Integration Module
 * 
 * 提供在现有页面中集成新API Client的简单方法
 */

import { sendMessage } from '/js/services/chat_service.js';
import { ensureSession } from '/js/services/session_service.js';

/**
 * 替换现有的directSendMessage函数
 * 使用新的API Client发送消息
 */
export async function enhancedSendMessage() {
  const messageInput = document.getElementById('user-message');
  const message = messageInput.value.trim();
  
  if (!message) {
    alert('请输入消息内容');
    return;
  }
  
  // 禁用发送按钮，显示加载状态
  const sendButton = document.getElementById('send-message');
  const originalText = sendButton.textContent;
  sendButton.disabled = true;
  sendButton.textContent = '发送中...';
  
  try {
    // 确保会话存在
    await ensureSession();
    
    // 添加用户消息到聊天界面
    addMessageToChat('user', message);
    
    // 构建聊天上下文
    const chatParams = {
      userMessage: message,
      conversationHistory: getChatHistoryFromUI(),
      codeContext: getCodeContext(),
      taskContext: getTaskContext(),
      topicId: getTopicIdFromUrl()
    };
    
    // 使用新的API Client发送消息
    const result = await sendMessage(chatParams);
    
    // 添加AI回复到聊天界面
    addMessageToChat('ai', result.ai_response);
    
  } catch (error) {
    console.error('发送消息失败:', error);
    addMessageToChat('ai', '抱歉，我暂时无法回复，请稍后再试。');
  } finally {
    // 恢复发送按钮状态
    sendButton.disabled = false;
    sendButton.textContent = originalText;
    
    // 清空输入框
    messageInput.value = '';
  }
}

/**
 * 获取聊天历史
 */
function getChatHistoryFromUI() {
  const chatMessages = document.getElementById('ai-chat-messages');
  if (!chatMessages) return [];
  
  const history = [];
  const messages = chatMessages.querySelectorAll('.user-message, .ai-message');
  
  messages.forEach(message => {
    const isUser = message.classList.contains('user-message');
    const content = message.querySelector('.user-content, .ai-content').textContent;
    
    history.push({
      role: isUser ? 'user' : 'assistant',
      content: content,
      timestamp: new Date().toISOString()
    });
  });
  
  return history;
}

/**
 * 获取代码上下文
 */
function getCodeContext() {
  // 这里应该根据实际的代码编辑器获取代码
  // 示例实现，需要根据实际项目调整
  const htmlEditor = document.getElementById('html-editor');
  const cssEditor = document.getElementById('css-editor');
  const jsEditor = document.getElementById('js-editor');
  
  if (htmlEditor || cssEditor || jsEditor) {
    return {
      html: htmlEditor ? htmlEditor.value : '',
      css: cssEditor ? cssEditor.value : '',
      js: jsEditor ? jsEditor.value : ''
    };
  }
  
  return null;
}

/**
 * 获取任务上下文
 */
function getTaskContext() {
  const urlParams = new URLSearchParams(window.location.search);
  const taskId = urlParams.get('task');
  
  if (taskId) {
    return `task:${taskId}`;
  }
  
  return null;
}

/**
 * 从URL获取主题ID
 */
function getTopicIdFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('topic') || null;
}

/**
 * 添加消息到聊天界面
 */
function addMessageToChat(role, content) {
  const chatMessages = document.getElementById('ai-chat-messages');
  if (!chatMessages) return;
  
  const messageDiv = document.createElement('div');
  messageDiv.className = role === 'user' ? 'user-message' : 'ai-message';
  
  const contentDiv = document.createElement('div');
  contentDiv.className = role === 'user' ? 'user-content' : 'ai-content';
  
  if (role === 'ai') {
    const markdownDiv = document.createElement('div');
    markdownDiv.className = 'markdown-content';
    markdownDiv.innerHTML = content.replace(/\n/g, '<br>');
    contentDiv.appendChild(markdownDiv);
  } else {
    contentDiv.textContent = content;
  }
  
  messageDiv.appendChild(contentDiv);
  chatMessages.appendChild(messageDiv);
  
  // 滚动到底部
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * 初始化聊天集成
 */
export function initChatIntegration() {
  // 替换现有的directSendMessage函数
  window.directSendMessage = enhancedSendMessage;
  
  console.log('Chat integration initialized');
}
