// frontend/js/api_client.js
import { getLocalParticipantId } from './services/session_service.js';
import { AppConfig } from './modules/config.js';

export async function post(endpoint, body) {
  const participantId = getLocalParticipantId();
  if (!participantId) {
        // 如果没有ID，说明会话已丢失，应强制返回注册页
        window.location.href = '/index.html';
        throw new Error("Session not found. Redirecting to login.");
  }

  // 自动在请求体中注入participant_id
  const fullBody = { ...body, participant_id: participantId };

  // 构建完整的后端API地址
  const backendUrl = `${AppConfig.api_base_url}${endpoint}`;
  const response = await fetch(backendUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(fullBody),
  });
  return response.json();
}
// ... 实现 get, put, delete 等方法
export async function get(endpoint) {
  const participantId = getLocalParticipantId();
  if (!participantId) {
        // 如果没有ID，说明会话已丢失，应强制返回注册页
        window.location.href = '/index.html';
        throw new Error("Session not found. Redirecting to login.");
  }
  // 构建完整的后端API地址
  const backendUrl = `${AppConfig.api_base_url}${endpoint}?participant_id=${participantId}`;
  const response = await fetch(backendUrl, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
  });
  return response.json();
}
// TODO:实现put, delete等方法

/**
 * 解析端点映射，避免硬编码路径。
 * 优先从 AppConfig.endpoints[key] 获取，缺失时回退到 fallback。
 * 返回相对路径（不拼接 api_base_url），由 ApiClient 负责拼接基址。
 * @param {string} key
 * @param {string} fallback
 * @returns {string}
 */
export function resolveEndpoint(key, fallback) {
  const endpoints = (AppConfig && AppConfig.endpoints) || {};
  return endpoints[key] || fallback;
}

export default { get, post, resolveEndpoint };