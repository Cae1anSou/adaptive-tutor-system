/**
 * Chat UI Layer
 * 
 * UI层：纯UI操作，DOM操作，用户交互
 * 职责：
 * - DOM操作
 * - 用户交互处理
 * - 界面状态管理
 * - 无业务逻辑，只负责界面展示
 */

/**
 * 聊天UI管理器
 */
export class ChatUI {
  /**
   * 添加消息到聊天界面
   * @param {string} role - 消息角色 ('user' 或 'assistant')
   * @param {string} content - 消息内容
   * @param {string} messageId - 消息ID（可选）
   */
  static addMessage(role, content, messageId = null) {
    const chatMessages = document.getElementById('ai-chat-messages');
    if (!chatMessages) {
      console.warn('Chat messages container not found');
      return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = role === 'user' ? 'user-message' : 'ai-message';
    
    // 添加消息ID作为数据属性
    if (messageId) {
      messageDiv.setAttribute('data-message-id', messageId);
    }
    
    const contentDiv = document.createElement('div');
    contentDiv.className = role === 'user' ? 'user-content' : 'ai-content';
    
    if (role === 'assistant') {
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
    this._scrollToBottom(chatMessages);
  }

  /**
   * 清空聊天消息
   */
  static clearMessages() {
    const chatMessages = document.getElementById('ai-chat-messages');
    if (chatMessages) {
      chatMessages.innerHTML = '';
    }
  }

  /**
   * 获取用户输入的消息
   * @returns {string} 用户消息
   */
  static getUserMessage() {
    const messageInput = document.getElementById('user-message');
    return messageInput ? messageInput.value.trim() : '';
  }

  /**
   * 清空用户输入框
   */
  static clearUserInput() {
    const messageInput = document.getElementById('user-message');
    if (messageInput) {
      messageInput.value = '';
    }
  }

  /**
   * 设置发送按钮状态
   * @param {boolean} disabled - 是否禁用
   * @param {string} text - 按钮文本
   */
  static setSendButtonState(disabled, text = '发送') {
    const sendButton = document.getElementById('send-message');
    if (sendButton) {
      sendButton.disabled = disabled;
      sendButton.textContent = text;
    }
  }

  /**
   * 设置输入框状态
   * @param {boolean} disabled - 是否禁用
   */
  static setInputState(disabled) {
    const messageInput = document.getElementById('user-message');
    if (messageInput) {
      messageInput.disabled = disabled;
      if (!disabled) {
        messageInput.focus();
      }
    }
  }

  /**
   * 显示加载状态
   */
  static showLoading() {
    this.setSendButtonState(true, '发送中...');
    this.setInputState(true);
  }

  /**
   * 隐藏加载状态
   */
  static hideLoading() {
    this.setSendButtonState(false, '发送');
    this.setInputState(false);
    this.clearUserInput(); // 清空输入框
  }

  /**
   * 显示错误消息
   * @param {string} message - 错误消息
   */
  static showError(message) {
    // 可以在这里添加错误提示UI，比如toast或alert
    console.error('Chat UI Error:', message);
    alert(message);
  }

  /**
   * 滚动到底部
   * @private
   */
  static _scrollToBottom(element) {
    element.scrollTop = element.scrollHeight;
  }

  /**
   * 检查聊天界面是否已初始化
   * @returns {boolean}
   */
  static isInitialized() {
    return !!document.getElementById('ai-chat-messages');
  }


}

// 向后兼容的导出
export const addMessageToChat = ChatUI.addMessage;