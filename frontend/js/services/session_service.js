/**
 * Session Service
 *
 * 提供会话初始化与本地会话管理的函数签名
 */

import ApiClient, { resolveEndpoint } from '/js/api_client.js';

/**
 * 确保本地存在 participant_id；若不存在，调用后端会话接口创建
 
 * @returns {Promise<string>} - 有效的 participant_id
 */
export async function ensureSession() {
  const existing = getLocalParticipantId();
  if (existing) return existing;
  const endpoint = resolveEndpoint('sessionInitiate', '/session/initiate');
  const body = { group: 'experimental' };
  const result = await ApiClient.post(endpoint, body);
  if (!result || typeof result !== 'object') {
    throw new Error('Invalid response');
  }
  if (Number(result.code) !== 200) {
    const msg = result.message || 'Session initiate failed';
    throw new Error(msg);
  }
  const data = result.data || {};
  if (!data.participant_id) {
    throw new Error('Missing participant_id in response');
  }
  saveLocalParticipantId(data.participant_id);
  return data.participant_id;
}

/**
 * 读取本地 participant_id。
 * @returns {string|null}
 */
export function getLocalParticipantId() {
  try {
    return window.localStorage.getItem('participant_id');
  } catch (_) {
    return null;
  }
}

/**
 * 保存本地 participant_id。
 * @param {string} id - participant_id
 */
export function saveLocalParticipantId(id) {
  try {
    window.localStorage.setItem('participant_id', String(id || ''));
  } catch (_) {
    // ignore
  }
}

