// frontend/js/modules/chat_storage.js
// 简单的基于 localStorage 的聊天持久化

const CHAT_HISTORY_PREFIX = 'chat_history:';
const SCHEMA_VERSION = 1;
const DEFAULT_MAX_MESSAGES = 200; // 每个用户保留的最大消息条数

function _key(participantId) {
  return `${CHAT_HISTORY_PREFIX}${participantId}`;
}

function _loadRaw(participantId) {
  try {
    const raw = localStorage.getItem(_key(participantId));
    if (!raw) return { version: SCHEMA_VERSION, items: [] };
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.items)) {
      return { version: SCHEMA_VERSION, items: [] };
    }
    return parsed;
  } catch (e) {
    console.warn('[chat_storage] 解析历史失败，重置为空:', e);
    return { version: SCHEMA_VERSION, items: [] };
  }
}

function _saveRaw(participantId, data) {
  try {
    localStorage.setItem(_key(participantId), JSON.stringify(data));
  } catch (e) {
    console.warn('[chat_storage] 保存失败:', e);
  }
}

function load(participantId) {
  const data = _loadRaw(participantId);
  return data.items || [];
}

function append(participantId, message, options = {}) {
  const { maxMessages = DEFAULT_MAX_MESSAGES } = options;
  const data = _loadRaw(participantId);
  const item = {
    role: message.role, // 'user' | 'assistant'
    content: message.content,
    mode: message.mode || null,
    contentId: message.contentId || null,
    ts: message.ts || Date.now(),
  };
  data.items.push(item);
  // 裁剪为最近 maxMessages 条
  if (data.items.length > maxMessages) {
    data.items = data.items.slice(data.items.length - maxMessages);
  }
  _saveRaw(participantId, data);
}

function clear(participantId) {
  try {
    localStorage.removeItem(_key(participantId));
  } catch (e) {
    console.warn('[chat_storage] 清空失败:', e);
  }
}

function hasHistory(participantId) {
  const items = load(participantId);
  return items && items.length > 0;
}

export default {
  load,
  append,
  clear,
  hasHistory,
};

