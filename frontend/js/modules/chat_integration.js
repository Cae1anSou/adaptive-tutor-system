/**
 * Chat Integration Layer
 * 
 * 集成层：连接服务层和UI层，处理页面特定的业务逻辑
 * 职责：
 * - 协调多个服务
 * - 处理页面状态
 * - 错误处理和用户友好的错误消息
 * - 业务逻辑编排
 */

import { ChatService } from '../services/chat_service.js';
import { getLocalParticipantId, ensureSession } from '../services/session_service.js';
import { ChatUI } from './chat_ui.js';
import { AppConfig } from './config.js';
import { chatHistoryManager } from './chat_history_manager.js';
import { 
    getCodeContext, 
    getTaskContext, 
    getRealTaskContext,
    getTopicIdFromUrl
} from './chat_utils.js';

/**
 * 聊天集成管理器
 */
export class ChatIntegrationManager {
  constructor() {
    this.isLoading = false;
    this.errorHandler = null;
    this.lastRequestMessageId = null; // 记录上次请求的最后消息ID
  }

  /**
   * 初始化事件绑定
   */
  async initEventListeners() {
    // 初始化历史管理器
    const participantId = getLocalParticipantId();
    if (participantId) {
      await chatHistoryManager.initialize(participantId);
    }

    // 绑定发送按钮点击事件
    const sendButton = document.getElementById('send-message');
    if (sendButton) {
      sendButton.addEventListener('click', () => {
        const message = ChatUI.getUserMessage();
        if (message) {
          this.sendMessage(message);
        }
      });
    }

    // 绑定回车键发送事件
    const messageInput = document.getElementById('user-message');
    if (messageInput) {
      messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          const message = ChatUI.getUserMessage();
          if (message) {
            this.sendMessage(message);
          }
        }
      });
    }
  }

  /**
   * 设置错误处理器
   * @param {Function} handler - 错误处理函数
   */
  setErrorHandler(handler) {
    this.errorHandler = handler;
  }

  /**
   * 发送消息的主要方法
   * @param {string} message - 用户消息
   * @returns {Promise<void>}
   */
  async sendMessage(message) {
    if (!message || !message.trim()) {
      this._showError('请输入消息内容');
      return;
    }

    if (this.isLoading) {
      return; // 防止重复发送
    }

    this.isLoading = true;
    ChatUI.showLoading();

    try {
      // 确保会话存在
      await ensureSession();
      
      // 添加用户消息到UI和缓存
      const userMessageId = chatHistoryManager.addMessage('user', message);
      ChatUI.addMessage('user', message, userMessageId);
      
      // 构建聊天上下文
      const chatParams = this._buildChatParams(message);
      
      // 添加详细的调试日志
      console.log('发送到后端的完整参数:', JSON.stringify(chatParams, null, 2));
      
      // 调用服务层发送消息
      const result = await ChatService.sendMessage(chatParams);
      
      // 添加AI回复到UI和缓存
      const aiMessageId = chatHistoryManager.addMessage('assistant', result.ai_response);
      ChatUI.addMessage('assistant', result.ai_response, aiMessageId);
      
      // 更新最后请求的消息ID
      this.lastRequestMessageId = chatHistoryManager.lastMessageId;
      
    } catch (error) {
      console.error('发送消息失败:', error);
      const userFriendlyError = this._getUserFriendlyError(error);
      ChatUI.addMessage('assistant', userFriendlyError);
      
      // 调用自定义错误处理器
      if (this.errorHandler) {
        this.errorHandler(error);
      }
    } finally {
      this.isLoading = false;
      ChatUI.hideLoading();
    }
  }

  /**
   * 加载聊天历史
   * @returns {Promise<void>}
   */
  async loadChatHistory() {
    try {
      const participantId = getLocalParticipantId();
      if (!participantId) {
        console.warn('No participant ID found, skipping chat history load');
        return;
      }

      // 确保历史管理器已初始化
      if (!chatHistoryManager.isInitialized) {
        await chatHistoryManager.initialize(participantId);
      }

      // 从缓存获取历史
      const history = chatHistoryManager.getFullHistory();
      
      // 清空现有聊天界面
      ChatUI.clearMessages();
      
      // 添加历史消息到UI
      history.forEach(msg => {
        const role = msg.role === 'user' ? 'user' : 'assistant';
        ChatUI.addMessage(role, msg.content, msg.id);
      });
      
      // 更新最后请求的消息ID
      if (history.length > 0) {
        this.lastRequestMessageId = history[history.length - 1].id;
      }
      
    } catch (error) {
      console.error('加载聊天历史失败:', error);
      if (this.errorHandler) {
        this.errorHandler(error);
      }
    }
  }

  /**
   * 构建聊天参数
   * @private
   */
  _buildChatParams(userMessage) {
    // 获取完整的对话历史（排除当前正在发送的消息）
    const fullHistory = chatHistoryManager.getFullHistory();
    
    // 优先使用真实的任务上下文，如果没有则使用模拟数据
    const taskContext = getRealTaskContext() || getTaskContext();
    
    // 添加调试日志
    console.log('构建聊天参数:', {
      userMessage,
      historyLength: fullHistory.length,
      taskContext: taskContext ? '有任务上下文' : '无任务上下文',
      codeContext: getCodeContext() ? '有代码上下文' : '无代码上下文'
    });
    
    return {
      userMessage: userMessage,
      conversationHistory: fullHistory,
      codeContext: getCodeContext(),
      taskContext: taskContext,
      topicId: getTopicIdFromUrl()
    };
  }

  /**
   * 获取用户友好的错误消息
   * @private
   */
  _getUserFriendlyError(error) {
    const errorMessage = error.message || '未知错误';
    const errorMessages = AppConfig.errorMessages || {};
    
    if (errorMessage.includes('Session not found')) {
      return errorMessages.sessionNotFound || '会话已过期，请重新登录。';
    } else if (errorMessage.includes('Network error') || errorMessage.includes('Failed to fetch')) {
      return errorMessages.networkError || '网络连接失败，请检查后端服务器是否运行。';
    } else if (errorMessage.includes('Unexpected token')) {
      return '服务器返回格式错误，请检查后端服务。';
    } else if (errorMessage.includes('501')) {
      return 'API方法不支持，请检查后端服务配置。';
    } else if (errorMessage.includes('404')) {
      return 'API端点不存在，请检查后端服务。';
    } else if (errorMessage.includes('500')) {
      return errorMessages.serverError || '服务器内部错误，请稍后重试。';
    } else if (errorMessage.includes('400')) {
      return errorMessages.invalidRequest || '请求参数错误，请检查输入内容。';
    } else if (errorMessage.includes('403')) {
      return errorMessages.accessDenied || '访问被拒绝，请检查权限设置。';
    }
    
    return errorMessages.unknownError || '抱歉，我暂时无法回复，请稍后再试。';
  }

  /**
   * 显示错误消息
   * @private
   */
  _showError(message) {
    if (this.errorHandler) {
      this.errorHandler(new Error(message));
    } else {
      ChatUI.showError(message);
    }
  }
}

// 创建全局实例
export const chatIntegration = new ChatIntegrationManager();

// 向后兼容的导出
export const enhancedSendMessage = () => {
  const message = ChatUI.getUserMessage();
  if (message) {
    return chatIntegration.sendMessage(message);
  }
};

export const initChatIntegration = async () => {
  console.log('Chat integration initialized');
  // 初始化事件绑定
  await chatIntegration.initEventListeners();
  return chatIntegration;
};
