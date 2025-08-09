/**
 * Chat Service
 *
 * 提供聊天相关的对接函数签名
 * 
 */

import ApiClient, { resolveEndpoint } from '/js/api_client.js';


/**
 * 发送聊天消息至后端聊天接口
 * @param {Object} params - 参数对象
 * @param {string} params.userMessage - 用户输入消息
 * @param {Array<Object>} [params.conversationHistory] - 历史消息列表
 * @param {Object} [params.codeContext] - 代码上下文（可选）
 * @param {Object} [params.taskContext] - 任务上下文（可选）
 * @param {string} [params.topicId] - 当前学习主题ID（可选）
 * @returns {Promise<Object>} - 期望返回 ChatResponse（包裹在 StandardResponse 中的 data）
 */
export async function sendMessage(params) {
  const endpoint = resolveEndpoint('chat', '/chat/ai/chat');

  const {
    userMessage,
    conversationHistory = [],
    codeContext = undefined,
    taskContext = undefined,
    topicId = undefined,
  } = params || {};

  const payload = {
    user_message: userMessage,
    conversation_history: conversationHistory,
    code_context: codeContext,
    task_context: taskContext,
    topic_id: topicId,
  };

  const result = await ApiClient.post(endpoint, payload);

  if (!result || typeof result !== 'object') {
    throw new Error('Invalid response');
  }
  if (Number(result.code) !== 200) {
    const msg = result.message || 'Chat API error';
    throw new Error(msg);
  }
  return result.data;
}

/**
 * 构建聊天上下文
 * @param {Array<Object>} history - 现有对话历史
 * @param {Object} latest - 最新一条消息
 * @returns {Array<Object>} - 合并后的对话历史
 */
export function buildConversationHistory(history, latest) {
  const safeHistory = Array.isArray(history) ? history.slice() : [];
  if (latest && typeof latest === 'object') {
    const withTimestamp = {
      timestamp: latest.timestamp || new Date().toISOString(),
      ...latest,
    };
    safeHistory.push(withTimestamp);
  }
  return safeHistory;
}

