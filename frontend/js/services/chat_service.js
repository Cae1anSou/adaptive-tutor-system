/**
 * Chat Service Layer
 * 
 * 服务层：纯业务逻辑，与后端API交互，数据转换
 * 职责：
 * - 与后端API通信
 * - 数据格式转换
 * - 错误处理
 * - 无UI依赖，可复用
 */

import ApiClient, { resolveEndpoint } from '/js/api_client.js';
import { AppConfig } from '/js/modules/config.js';

/**
 * 聊天服务类
 */
export class ChatService {
  /**
   * 发送消息到AI聊天接口
   * 
   * @param {Object} chatParams - 聊天参数
   * @param {string} chatParams.userMessage - 用户消息
   * @param {Array} chatParams.conversationHistory - 对话历史（可选）
   * @param {Object} chatParams.codeContext - 代码上下文（可选）
   * @param {string} chatParams.taskContext - 任务上下文（可选）
   * @param {string} chatParams.topicId - 主题ID（可选）
   * @returns {Promise<Object>} AI回复结果
   */
  static async sendMessage(chatParams) {
    const endpoint = resolveEndpoint('chat', '/chat/ai/chat');
    
    // 构建请求体 - ApiClient会自动注入participant_id
    const requestBody = {
      user_message: chatParams.userMessage,
      conversation_history: chatParams.conversationHistory || [],
      code_context: chatParams.codeContext || null,
      task_context: chatParams.taskContext || null,
      topic_title: chatParams.topicId || null
    };
    
    try {
      const result = await ApiClient.post(endpoint, requestBody);
      
      // 验证响应格式
      this._validateResponse(result);
      
      return result.data;
    } catch (error) {
      console.error('Chat service error:', error);
      throw this._handleError(error, endpoint);
    }
  }

  /**
   * 获取聊天历史（从后端数据库获取）
   * 
   * @param {string} participantId - 参与者ID
   * @returns {Promise<Array>} 聊天历史记录
   */
  static async getChatHistory(participantId) {
    if (!participantId) {
      throw new Error('participantId is required');
    }
    
    const endpoint = resolveEndpoint('chatHistory', `/chat/history/${participantId}`);
    
    try {
      const result = await ApiClient.get(endpoint);
      
      if (result.code !== AppConfig.statusCodes.SUCCESS) {
        throw new Error(result.message || '获取聊天历史失败');
      }
      
      return result.data || [];
    } catch (error) {
      console.error('Get chat history error:', error);
      throw this._handleError(error, endpoint);
    }
  }

  /**
   * 验证API响应格式
   * @private
   */
  static _validateResponse(result) {
    if (!result || typeof result !== 'object') {
      throw new Error('Invalid response format from server');
    }
    
    if (result.code !== AppConfig.statusCodes.SUCCESS) {
      throw new Error(result.message || `API request failed with code ${result.code}`);
    }
    
    if (!result.data || typeof result.data !== 'object') {
      throw new Error('Invalid data structure in response');
    }
    
    if (!result.data.ai_response || typeof result.data.ai_response !== 'string') {
      throw new Error('Missing or invalid ai_response in response data');
    }
  }

  /**
   * 统一错误处理
   * @private
   */
  static _handleError(error, endpoint) {
    // 如果是网络错误，添加更多上下文信息
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      return new Error(`Network error: Unable to connect to chat service at ${endpoint}`);
    }
    
    return error;
  }
}

// 向后兼容的导出
export const sendMessage = ChatService.sendMessage;
export const getChatHistory = ChatService.getChatHistory;
