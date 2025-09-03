// frontend/js/api_client.js
import { getParticipantId } from './modules/session.js';
import { buildBackendUrl } from './modules/config.js';
import {AppConfig} from './modules/config.js';

export function buildWebSocketUrl(id='') {
    return `${buildBackendUrl('/ws/user/')}${id}`;
}
// --- 新增：不带 participant_id 的通用请求方法 ---
async function _requestWithoutAuth(endpoint, options = {}) {
    const defaultOptions = {
        headers: { 'Content-Type': 'application/json' },
        ...options
    };
    
    const url = buildBackendUrl(endpoint);
    const response = await fetch(url, defaultOptions);
    return response.json();
}

async function getWithoutAuth(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const urlWithParams = queryString ? `${endpoint}?${queryString}` : endpoint;
    return _requestWithoutAuth(urlWithParams, { method: 'GET' });
}

async function postWithoutAuth(endpoint, body) {
    return _requestWithoutAuth(endpoint, {
        method: 'POST',
        body: JSON.stringify(body)
    });
}
// --- 新增结束 ---


async function post(endpoint, body) {
  const participantId = getParticipantId();
  if (!participantId) {
        // 如果没有ID，说明会话已丢失，应强制返回注册页
        window.location.href = '/pages/index.html';
        throw new Error("Session not found. Redirecting to login.");
  }

  // 自动在请求体中注入participant_id
  const fullBody = { ...body, participant_id: participantId };

  const response = await fetch(buildBackendUrl(endpoint), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(fullBody),
  });
  return response.json();
}

// ... 实现 get, put, delete 等方法
async function get(endpoint, params = {}) {
  const participantId = getParticipantId();
  if (!participantId) {
        // 如果没有ID，说明会话已丢失，应强制返回注册页
        window.location.href = '/pages/index.html';
        throw new Error("Session not found. Redirecting to login.");
  }
  
  // 自动添加participant_id到查询参数
  params.participant_id = participantId;
  
  const queryString = new URLSearchParams(params).toString();
  const url = `${buildBackendUrl(endpoint)}?${queryString}`;
  
  const response = await fetch(url, {
          method: 'GET',
          headers: { 'Content-Type': 'application/json' },
  });
  return response.json();
}

// 挂载到window对象上，以便全局访问
window.apiClient = {
  post,
  get,
  // --- 新增：暴露不带认证的方法 ---
  postWithoutAuth,
  getWithoutAuth
  // --- 新增结束 ---
};

// 默认导出
export default {
  post,
  get,
  // --- 新增：导出不带认证的方法 ---
  postWithoutAuth,
  getWithoutAuth
  // --- 新增结束 ---
};