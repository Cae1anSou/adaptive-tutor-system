/**
 * Progress Service
 *
 * 提供用户学习进度的对接函数签名
 */

import ApiClient, { resolveEndpoint } from '/js/api_client.js';

/**
 * 获取指定用户的学习进度（GET /api/v1/progress/participants/{participant_id}/progress）。
 * @param {string} participantId - 用户ID
 * @returns {Promise<Object>} - 期望返回 { completed_topics: string[] }（包裹在 StandardResponse 中的 data）
 */
export async function getUserProgress(participantId) {
  const base = resolveEndpoint('progress', '/progress/participants');
  const endpoint = `${base}/${encodeURIComponent(participantId)}/progress`;
  const result = await ApiClient.get(endpoint);
  if (!result || typeof result !== 'object') {
    throw new Error('Invalid response');
  }
  if (Number(result.code) !== 200) {
    const msg = result.message || 'Get user progress failed';
    throw new Error(msg);
  }
  return result.data;
}

/**
 * 写入或同步用户进度（如有需要，可扩展对应接口）。
 * @param {string} participantId - 用户ID
 * @param {Object} payload - 进度变更载荷
 * @returns {Promise<Object>} - 标准响应的 data
 */
export async function updateUserProgress(participantId, payload) {
  const base = resolveEndpoint('progressUpdate', '/progress/participants');
  const endpoint = `${base}/${encodeURIComponent(participantId)}/progress`;
  const result = await ApiClient.post(endpoint, payload || {});
  if (!result || typeof result !== 'object') {
    throw new Error('Invalid response');
  }
  if (Number(result.code) !== 200) {
    const msg = result.message || 'Update user progress failed';
    throw new Error(msg);
  }
  return result.data;
}

