// frontend/js/modules/chat.js
/**
 * Chat 前端聊天模块
 *
 * 目标：
 * - 提供一个通用的聊天界面，供学习页面和测试页面使用
 * - 处理与后端 /api/v1/chat/ai/chat 端点的通信
 * - 管理聊天UI的渲染和交互
 */

import { getParticipantId } from './session.js';
import { marked } from "https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js";
import websocket from './socket.js';
class ChatModule {
  constructor() {
    this.chatContainer = null;
    this.messagesContainer = null;
    this.inputElement = null;
    this.sendButton = null;
    this.isLoading = false;
    websocket.userId = getParticipantId();
    websocket.connect();
  }

  /**
   * 初始化聊天模块
   * @param {string} mode - 模式 ('learning' 或 'test')
   * @param {string} contentId - 内容ID (学习内容ID或测试任务ID)
   */
  init(mode, contentId) {
    // 获取聊天界面元素
    this.chatContainer = document.querySelector('.ai-chat-messages');
    this.messagesContainer = document.getElementById('ai-chat-messages');
    this.inputElement = document.getElementById('user-message');
    this.sendButton = document.getElementById('send-message');

    if (!this.chatContainer || !this.messagesContainer || !this.inputElement || !this.sendButton) {
      console.warn('[ChatModule] 聊天界面元素未找到，无法初始化聊天模块');
      return;
    }

    // 绑定事件监听器
    this.bindEvents(mode, contentId);

    console.log('[ChatModule] 聊天模块初始化完成');
  }

  /**
   * 绑定事件监听器
   * @param {string} mode - 模式 ('learning' 或 'test')
   * @param {string} contentId - 内容ID
   */
  bindEvents(mode, contentId) {
    // 发送按钮点击事件
    this.sendButton.addEventListener('click', () => {
      this.sendMessage(mode, contentId);
    });

    // 回车键发送消息（Shift+Enter换行）
    this.inputElement.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage(mode, contentId);
      }
    });
  }

  /**
   * 发送消息到后端
   * @param {string} mode - 模式 ('learning' 或 'test')
   * @param {string} contentId - 内容ID
   */
  async sendMessage(mode, contentId) {
    const message = this.inputElement.value.trim();
    if (!message || this.isLoading) return;

    // 清空输入框
    this.inputElement.value = '';

    // 添加用户消息到UI
    this.addMessageToUI('user', message);

    // 设置加载状态
    this.setLoadingState(true);

    try {
      // 构建请求体 (participant_id 会由 apiClient 自动注入)
      const requestBody = {
        user_message: message,
        conversation_history: this.getConversationHistory(),
        code_context: this.getCodeContext(),
        mode: mode,
        content_id: contentId
      };

      // 如果是测试模式，添加测试结果
      if (mode === 'test') {
        const testResults = this._getTestResults();
        if (testResults) {
          requestBody.test_results = testResults;
        }
      }
    

      let block=this.addMessageToUI('ai', "");
      let currentAiMessageElement=block;
      const messageData = {
                        type: "ai_message",
                        userId: getParticipantId(),
                        message: message
                    };
      websocket.socket.send(JSON.stringify(messageData))
      websocket.onMessage((data, rawEvent) => {
                    //console.log("外部捕获消息:", data);
                    if (data.type === "stream_start") {
                        // 开始流式传输
                        //this.showTypingIndicator(false);
                        //currentAiMessageElement = addMessage('', 'ai', 'AI');
                    } else if (data.type === "stream") {
                        // 流式传输中
                        if (currentAiMessageElement) {
                            this.appendMessageContent(currentAiMessageElement, data.message);
                        }
                    } else if (data.type === "stream_end") {
                                // 流式传输结束：如果 stream_end 携带最后一段文本，先通过 appendMessageContent 入缓冲，
                                // 然后调用元素的分片 flush 函数完成剩余内容，避免一次性大块追加
                                if (currentAiMessageElement) {
                                    const el = currentAiMessageElement;
                                    if (data.message) {
                                        this.appendMessageContent(el, data.message);
                                    }
                                    if (el._flushFn) {
                                        el._flushFn();
                                    } else if (el._streamBuffer && el._streamBuffer.length > 0) {
                                        el.textContent += el._streamBuffer;
                                        el._streamBuffer = '';
                                    }
                                }
                                currentAiMessageElement = null;
                    } 
                    
            });



      // if (data.code === 200 && data.data && typeof data.data.ai_response === 'string') {
      //   // 添加AI回复到UI
      //   this.addMessageToUI('ai', data.data.ai_response);
      // } else {
      //   // 即使请求成功，但如果响应内容为空或格式不正确，也抛出错误
      //   throw new Error(data.message || 'AI回复内容为空或格式不正确');
      // }
    } catch (error) {
      console.error('[ChatModule] 发送消息时出错:', error);
      this.addMessageToUI('ai', `抱歉，我无法回答你的问题。错误信息: ${error.message}`);
    } finally {
      // 取消加载状态
      this.setLoadingState(false);
    }
  }
     appendMessageContent(messageContentElement, content) {
                // 按流缓冲起来，使用 requestAnimationFrame 分片追加，避免每次小片段都触发大量重排
                if (!messageContentElement._streamBuffer) messageContentElement._streamBuffer = '';
                messageContentElement._streamBuffer += content;

                // 如果已有调度则无需重复调度
                if (messageContentElement._rafScheduled) return;
                messageContentElement._rafScheduled = true;

                const messagesContainer = this.messagesContainer

                const FLUSH_CHUNK = 2; // 每帧最多追加的字符数，调大或调小以平衡流畅度与实时性

                const flush = () => {
                    messageContentElement._rafScheduled = false;

                    // 每次从缓冲区取出一段字符追加
                    const buffer = messageContentElement._streamBuffer || '';
                    if (!buffer) return;

                    const toAppend = buffer.slice(0, FLUSH_CHUNK);
                    // 使用 textContent 追加纯文本，避免 XSS 和重解析
                    messageContentElement.textContent += toAppend;

                    // 剩余写回缓冲区
                    messageContentElement._streamBuffer = buffer.slice(FLUSH_CHUNK);

                    // 平滑滚动到底部，但仅在用户接近底部时使用 smooth，避免用户查看历史消息时被打断
                    try {
                        const distanceFromBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight;
                        const useSmooth = distanceFromBottom < 80; // 阈值可调整
                        messagesContainer.scrollTo({ top: messagesContainer.scrollHeight, behavior: useSmooth ? 'smooth' : 'auto' });
                    } catch (e) {
                        // fallback
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    }

                    // 如果还有缓冲则在下一帧继续刷新
                    if (messageContentElement._streamBuffer && messageContentElement._streamBuffer.length > 0) {
                        messageContentElement._rafScheduled = true;
                        requestAnimationFrame(flush);
                    }
                };

                // 将 flush 暴露到元素，以便 stream_end 调用时触发分片完成
                messageContentElement._flushFn = () => {
                    // 如果已经在调度中，flush 会在当前 rAF 循环中自动完成
                    if (messageContentElement._rafScheduled) return;
                    messageContentElement._rafScheduled = true;
                    requestAnimationFrame(flush);
                };

                // 首次调度
                requestAnimationFrame(flush);
            }
  /**
   * 添加消息到UI
   * @param {string} sender - 发送者 ('user' 或 'ai')
   * @param {string} content - 消息内容
   */
  addMessageToUI(sender, content) {
    if (!this.messagesContainer) return;

    const messageElement = document.createElement('div');
    messageElement.classList.add(`${sender}-message`);
    let aiContent;
    if (sender === 'user') {
      const contentDiv = document.createElement('div');
      contentDiv.className = 'markdown-content';
      contentDiv.textContent = content;
      messageElement.innerHTML = `
        <div class="user-avatar">你</div>
        <div class="user-content">
          ${contentDiv.outerHTML}
        </div>
      `;
    } else {
      messageElement.innerHTML = `
        <div class="ai-avatar">AI</div>
        <div class="ai-content">
          <div class="markdown-content">${content}</div>
        </div>
      `;
      aiContent = messageElement.querySelector('.ai-content');
    }

    this.messagesContainer.appendChild(messageElement);

    // 滚动到底部
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    if (sender === 'ai') {
      return aiContent;
    }
  }
  
  /**
   * 设置加载状态
   * @param {boolean} loading - 是否加载中
   */
  setLoadingState(loading) {
    this.isLoading = loading;
    if (this.sendButton) {
      this.sendButton.disabled = loading;
      this.sendButton.textContent = loading ? '发送中...' : '提问';
    }
    
    // 添加或移除加载指示器
    if (loading) {
      const loadingElement = document.createElement('div');
      loadingElement.id = 'ai-loading';
      loadingElement.classList.add('ai-message');
      loadingElement.innerHTML = `
        <div class="ai-avatar">AI</div>
        <div class="ai-content">
          <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      `;
      this.messagesContainer.appendChild(loadingElement);
      this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    } else {
      const loadingElement = document.getElementById('ai-loading');
      if (loadingElement) {
        loadingElement.remove();
      }
    }
  }

  /**
   * 获取测试结果
   * @returns {Array|null} 测试结果数组或null
   * @private
   */
  /**
   * 获取测试结果
   * @returns {Array|null} 测试结果数组或null
   * @private
   */
  _getTestResults() {
    const resultsContainer = document.getElementById('test-results-content');
    if (!resultsContainer || !resultsContainer.innerHTML.trim()) {
      return null;
    }

    const results = [];
    const overallStatus = resultsContainer.classList.contains('test-result-passed') ? 'success' : 'error';

    // 提取主标题和副标题
    const mainHeader = resultsContainer.querySelector('h4');
    const subMessage = resultsContainer.querySelector('p');

    if (mainHeader) {
      results.push({
        status: overallStatus,
        message: mainHeader.textContent.trim()
      });
    }

    if (subMessage && subMessage.textContent.trim()) {
      results.push({
        status: 'info',
        message: subMessage.textContent.trim()
      });
    }

    // 提取详细信息
    const detailItems = resultsContainer.querySelectorAll('ul > li');
    detailItems.forEach(item => {
      results.push({
        status: overallStatus === 'success' ? 'info' : 'error', // 细节项跟随总体状态
        message: item.textContent.trim()
      });
    });

    return results.length > 0 ? results : null;
  }

  /**
   * 获取对话历史
   * @returns {Array} 对话历史数组
   */
  getConversationHistory() {
    if (!this.messagesContainer) {
      console.warn('[ChatModule] 消息容器未找到，无法获取对话历史');
      return [];
    }

    const history = [];
    // 获取所有消息元素（用户消息和AI消息，但不包括加载指示器）
    const messageElements = this.messagesContainer.querySelectorAll('.user-message, .ai-message:not(#ai-loading)');

    messageElements.forEach(element => {
      const isUserMessage = element.classList.contains('user-message');
      const isAiMessage = element.classList.contains('ai-message');

      if (isUserMessage || isAiMessage) {
        // 提取消息文本内容
        let textContent = '';
        const markdownContent = element.querySelector('.markdown-content');
        
        if (markdownContent) {
          // 如果是AI消息，markdownContent包含HTML，需要提取纯文本
          // 如果是用户消息，markdownContent是纯文本节点
          if (isAiMessage) {
            textContent = markdownContent.textContent || markdownContent.innerText || '';
          } else {
            textContent = markdownContent.textContent || markdownContent.innerText || '';
          }
        } else {
          // 作为后备方案，尝试从其他内容元素获取文本
          const contentElement = element.querySelector('.user-content, .ai-content');
          if (contentElement) {
            textContent = contentElement.textContent || contentElement.innerText || '';
          }
        }

        // 添加到历史记录中
        history.push({
          role: isUserMessage ? 'user' : 'assistant',
          content: textContent.trim()
        });
      }
    });

    return history;
  }

  /**
   * 获取代码上下文
   * @returns {Object} 代码上下文对象
   */
  getCodeContext() {
    // 尝试从全局编辑器状态获取代码
    try {
      if (window.editorState) {
        return {
          html: window.editorState.htmlEditor?.getValue() || '',
          css: window.editorState.cssEditor?.getValue() || '',
          js: window.editorState.jsEditor?.getValue() || ''
        };
      }
    } catch (e) {
      console.warn('[ChatModule] 获取代码上下文时出错:', e);
    }
    
    // 如果无法获取，返回空字符串
    return {
      html: '',
      css: '',
      js: ''
    };
  }

}

// 导出单例
const chatModule = new ChatModule();
export default chatModule;