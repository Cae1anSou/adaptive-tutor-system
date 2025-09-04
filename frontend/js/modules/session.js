import chatStorage from './chat_storage.js';
const PARTICIPANT_ID_KEY = 'participant_id';

export function saveParticipantId(id) {
  const prev = localStorage.getItem(PARTICIPANT_ID_KEY);
  if (prev && prev !== id) {
    try {
      // 用户切换账号时清空旧账号的聊天记录
      chatStorage.clear(prev);
    } catch (e) {
      console.warn('[session] 清空旧用户聊天历史失败:', e);
    }
  }
  localStorage.setItem(PARTICIPANT_ID_KEY, id);
}

export function getParticipantId() {
  return localStorage.getItem(PARTICIPANT_ID_KEY);
}

export function clearParticipantId() {
  localStorage.removeItem(PARTICIPANT_ID_KEY);
}

// 在页面加载时检查，如果已有会话，可以直接跳转，避免重复注册
export function checkAndRedirect() {
  if (getParticipantId()) {
        // 如果当前不是知识图谱页，则跳转过去
        if (!window.location.pathname.includes('knowledge_graph.html')) {
           window.location.href = '/pages/knowledge_graph.html';
        }
  }
}
