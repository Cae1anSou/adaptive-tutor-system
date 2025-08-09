/**
 * Content Service
 *
 * 提供学习内容与测试任务内容的对接函数签名
 */

import ApiClient, { resolveEndpoint } from '/js/api_client.js';
/**
 * 获取学习内容（GET /api/v1/learning-content/{topic_id}）。
 * @param {string} topicId - 主题ID
 * @returns {Promise<Object>} - 期望返回 LearningContent（包裹在 StandardResponse 中的 data）
 */


export async function getLearningContent(topicId) {
  // 端点映射
  // 约定：AppConfig.endpoints.learningContent -> "/learning-content"
  // 回退："/learning-content"
  const endpointBase = resolveEndpoint('learningContent', '/learning-content');
  const endpoint = `${endpointBase}/${encodeURIComponent(topicId)}`;

  const result = await ApiClient.get(endpoint);
  if (!result || typeof result !== 'object') {
    throw new Error('Invalid response');
  }
  if (Number(result.code) !== 200) {
    const msg = result.message || 'Get learning content failed';
    throw new Error(msg);
  }
  return result.data;
}

/**
 * 获取测试任务内容（GET /api/v1/test-tasks/{topic_id}）。
 * @param {string} topicId - 主题ID
 * @returns {Promise<Object>} - 期望返回 TestTask（包裹在 StandardResponse 中的 data）
 */
export async function getTestTask(topicId) {
  // 解析端点
  // 约定：AppConfig.endpoints.testTasks -> "/test-tasks"
  // 回退："/test-tasks"
  const endpointBase = resolveEndpoint('testTasks', '/test-tasks');
  const endpoint = `${endpointBase}/${encodeURIComponent(topicId)}`;

  const result = await ApiClient.get(endpoint);
  if (!result || typeof result !== 'object') {
    throw new Error('Invalid response');
  }
  if (Number(result.code) !== 200) {
    const msg = result.message || 'Get test task failed';
    throw new Error(msg);
  }
  return result.data;
}





