/**
 * Chat History Manager
 * 
 * 前端聊天历史缓存管理器
 * 职责：
 * - 管理前端聊天历史缓存
 * - 提供增量历史获取
 * - 与后端同步历史数据
 * - 优化性能，减少重复构建
 */

//Aeolyn:现有代码每次调用都重复构建上下文，这里改成了缓存在前端，每次调用都从缓存中获取

/**
 * 聊天历史管理器
 */
export class ChatHistoryManager {
  constructor() {
    this.history = [];
    this.lastMessageId = null;
    this.participantId = null;
    this.isInitialized = false;
  }

  /**
   * 初始化历史管理器
   * @param {string} participantId - 参与者ID
   */
  async initialize(participantId) {
    this.participantId = participantId;
    
    // 尝试从localStorage恢复缓存
    this._loadFromCache();
    
    // 如果缓存为空或过期，从后端同步
    if (this.history.length === 0 || this._isCacheExpired()) {
      await this.syncFromBackend();
    }
    
    this.isInitialized = true;
    console.log(`ChatHistoryManager initialized for participant: ${participantId}`);
  }

  /**
   * 添加新消息到缓存
   * @param {string} role - 消息角色 ('user' 或 'assistant')
   * @param {string} content - 消息内容
   * @param {string} messageId - 消息ID（可选，后端生成）
   * @returns {string} 消息ID
   */
  addMessage(role, content, messageId = null) {
    const message = {
      id: messageId || this._generateId(),
      role,
      content,
      timestamp: new Date().toISOString()
    };
    
    this.history.push(message);
    this.lastMessageId = message.id;
    
    // 保存到缓存
    this._saveToCache();
    
    return message.id;
  }

  /**
   * 获取增量历史（只返回上次请求后的新消息）
   * @param {string} lastMessageId - 上次请求的最后消息ID
   * @returns {Array} 增量历史消息
   */
  getIncrementalHistory(lastMessageId) {
    if (!lastMessageId) return this.history;
    
    const lastIndex = this.history.findIndex(msg => msg.id === lastMessageId);
    return lastIndex >= 0 ? this.history.slice(lastIndex + 1) : this.history;
  }

  /**
   * 获取完整历史
   * @returns {Array} 完整历史消息
   */
  getFullHistory() {
    return [...this.history];
  }

  /**
   * 获取最后N条消息
   * @param {number} count - 消息数量
   * @returns {Array} 最后N条消息
   */
  getLastMessages(count = 10) {
    return this.history.slice(-count);
  }

  /**
   * 从后端同步历史
   * @returns {Promise<void>}
   */
  async syncFromBackend() {
    if (!this.participantId) {
      console.warn('Cannot sync from backend: participantId not set');
      return;
    }

    try {
      const { ChatService } = await import('../services/chat_service.js');
      const history = await ChatService.getChatHistory(this.participantId);
      
      // 转换格式并去重
      const newHistory = history.map(msg => ({
        id: msg.id || this._generateId(),
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp || new Date().toISOString()
      }));

      // 合并历史，避免重复
      this.history = this._mergeHistory(this.history, newHistory);
      
      if (this.history.length > 0) {
        this.lastMessageId = this.history[this.history.length - 1].id;
      }
      
      // 保存到缓存
      this._saveToCache();
      
      console.log(`Synced ${newHistory.length} messages from backend`);
    } catch (error) {
      console.warn('Failed to sync history from backend:', error);
      // 同步失败不影响本地缓存的使用
    }
  }

  /**
   * 清空历史
   */
  clearHistory() {
    this.history = [];
    this.lastMessageId = null;
    this._saveToCache();
  }

  /**
   * 获取历史统计信息
   * @returns {Object} 统计信息
   */
  getStats() {
    const userMessages = this.history.filter(msg => msg.role === 'user').length;
    const assistantMessages = this.history.filter(msg => msg.role === 'assistant').length;
    
    return {
      total: this.history.length,
      user: userMessages,
      assistant: assistantMessages,
      lastMessageId: this.lastMessageId,
      isInitialized: this.isInitialized
    };
  }

  /**
   * 搜索历史消息
   * @param {string} query - 搜索关键词
   * @returns {Array} 匹配的消息
   */
  searchHistory(query) {
    if (!query || query.trim() === '') return [];
    
    const lowerQuery = query.toLowerCase();
    return this.history.filter(msg => 
      msg.content.toLowerCase().includes(lowerQuery)
    );
  }

  /**
   * 生成唯一ID
   * @private
   */
  _generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
  }

  /**
   * 保存到本地缓存
   * @private
   */
  _saveToCache() {
    if (!this.participantId) return;
    
    try {
      const cacheData = {
        history: this.history,
        lastMessageId: this.lastMessageId,
        timestamp: Date.now()
      };
      
      localStorage.setItem(`chat_history_${this.participantId}`, JSON.stringify(cacheData));
    } catch (error) {
      console.warn('Failed to save chat history to cache:', error);
    }
  }

  /**
   * 从本地缓存加载
   * @private
   */
  _loadFromCache() {
    if (!this.participantId) return;
    
    try {
      const cached = localStorage.getItem(`chat_history_${this.participantId}`);
      if (cached) {
        const cacheData = JSON.parse(cached);
        this.history = cacheData.history || [];
        this.lastMessageId = cacheData.lastMessageId || null;
      }
    } catch (error) {
      console.warn('Failed to load chat history from cache:', error);
      this.history = [];
      this.lastMessageId = null;
    }
  }

  /**
   * 检查缓存是否过期（24小时）
   * @private
   */
  _isCacheExpired() {
    if (!this.participantId) return true;
    
    try {
      const cached = localStorage.getItem(`chat_history_${this.participantId}`);
      if (cached) {
        const cacheData = JSON.parse(cached);
        const cacheAge = Date.now() - (cacheData.timestamp || 0);
        return cacheAge > 24 * 60 * 60 * 1000; // 24小时
      }
    } catch (error) {
      console.warn('Failed to check cache expiration:', error);
    }
    
    return true;
  }

  /**
   * 合并历史记录，避免重复
   * @private
   */
  _mergeHistory(existingHistory, newHistory) {
    const existingIds = new Set(existingHistory.map(msg => msg.id));
    const uniqueNewMessages = newHistory.filter(msg => !existingIds.has(msg.id));
    
    return [...existingHistory, ...uniqueNewMessages].sort((a, b) => 
      new Date(a.timestamp) - new Date(b.timestamp)
    );
  }
}

// 创建全局实例
export const chatHistoryManager = new ChatHistoryManager();

// 向后兼容的导出
export const getChatHistory = () => chatHistoryManager.getFullHistory();
export const addChatMessage = (role, content, messageId) => chatHistoryManager.addMessage(role, content, messageId);
