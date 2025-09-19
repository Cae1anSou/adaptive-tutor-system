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
import websocket from './websocket_client.js';
import api_client from '../api_client.js'
import chatStorage from './chat_storage.js';
class ChatModule {
  constructor() {
    console.log('[DEBUG] ChatModule 脚本加载了');
    this.chatContainer = null;
    this.messagesContainer = null;
    this.inputElement = null;
    this.sendButton = null;
    this.isLoading = false;
  // 当为 true 时，生成期间始终自动滚到底部；生成结束后恢复用户自由滚动
  this.autoScrollDuringGeneration = false;
    this.streamElement = null;
    // 添加缓冲区用于存储完整的AI消息
    this.aiMessageBuffer = null;
    //websocket.userId = getParticipantId();
    //websocket.connect();
     // 订阅 WebSocket 消息
//stream_start
    websocket.subscribe("stream_start", (msg) => {
      console.log("[ChatModule]stream_start");
      // 展示AI回复
      //console.log("[ChatModule] 收到AI结果:", msg);
      //this.setLoadingState(true);
      // 收到结果后解除加载状态，解锁“提问”按钮
      //this.setLoadingState(false);
      // 双重保证：收到结果时清空输入框（即使发送时已清空）
      // 初始化AI消息缓冲区
      this.aiMessageBuffer = "";
    });
//streaming
    websocket.subscribe("streaming", (msg) => {
      // 流式中间数据
      console.log('[ChatModule] streaming raw msg:', msg);
      // 确保有一个占位元素
      if (!this.streamElement) {
        // 尝试寻找最后一个 AI 占位元素作为回退
        const lastAi = this.messagesContainer && this.messagesContainer.querySelector('.ai-message:last-of-type .markdown-content');
        if (lastAi) {
          this.streamElement = lastAi;
          console.log('[ChatModule] 在 streaming 时恢复 streamElement');
        }
      }

      // 解析消息，支持字符串或对象
      let chunk = '';
      try {
        if (typeof msg === 'string') {
          chunk = msg;
        } else if (msg === null || msg === undefined) {
          chunk = '';
        } else if (typeof msg === 'object') {
          // 常见字段优先级：data > ai_response > content > text
          chunk = msg.data || msg.ai_response || msg.content || msg.text || '';
          // 有时 data 是对象包含 text
          if (typeof chunk === 'object' && chunk !== null) {
            chunk = chunk.text || chunk.message || JSON.stringify(chunk);
          }
        }
      } catch (e) {
        console.warn('[ChatModule] 解析 stream chunk 时出错', e, msg);
        chunk = '';
      }

      // 将内容添加到缓冲区
      if (chunk) {
        this.aiMessageBuffer += chunk;
      }

      if (chunk && this.streamElement) {
        this.appendMessageContent(this.streamElement, chunk);
      } else if (chunk && !this.streamElement) {
        // 如果没有占位元素，直接新增一条 ai 消息并填充
        const el = this.addMessageToUI('ai', chunk, { persist: false });
        this.streamElement = el;
      }
    });
//stream_end
websocket.subscribe("stream_end", (msg) => {
      console.log('[ChatModule] stream_end raw msg:', msg);
      // if (!this.streamElement) {
      //   // 尝试恢复最后一个 AI 元素
      //   const lastAi = this.messagesContainer && this.messagesContainer.querySelector('.ai-message:last-of-type .markdown-content');
      //   if (lastAi) {
      //     this.streamElement = lastAi;
      //   }
      // }
    
      if (this.streamElement) {
        let finalChunk = '';
        try {
          if (typeof msg === 'string') {
            finalChunk = msg;
          } else if (msg && typeof msg === 'object') {
            finalChunk = msg.data || msg.ai_response || msg.content || msg.text || '';
            if (typeof finalChunk === 'object' && finalChunk !== null) {
              finalChunk = finalChunk.text || finalChunk.message || JSON.stringify(finalChunk);
            }
          }
        } catch (e) {
          console.warn('[ChatModule] 解析 stream_end msg 失败', e, msg);
        }

        // 将最终块添加到缓冲区
        // if (finalChunk) {
        //   this.aiMessageBuffer += finalChunk;
        // }

        // 使用完整缓冲区内容更新DOM
        if (this.aiMessageBuffer !== null && this.streamElement) {
          this.streamElement._renderBuffer = this.aiMessageBuffer;
          if (this.streamElement._flushFn) {
            this.streamElement._flushFn();
          }
        }

        // 将完整消息保存到localStorage
        if (this.aiMessageBuffer !== null) {
          try {
            const participantId = getParticipantId();
            if (participantId) {
              chatStorage.append(participantId, {
                role: 'assistant',
                content: this.aiMessageBuffer,
                mode: this.currentMode,
                contentId: this.currentContentId,
                ts: Date.now(),
              });
            }
          } catch (e) {
            console.warn('[ChatModule] 持久化完整AI消息失败:', e);
          }
        }
      }
      this.setLoadingState(false);
      if (this.inputElement) this.inputElement.value = '';
      this.streamElement = null;
      // 清空缓冲区
      this.aiMessageBuffer = null;
    });
    // websocket.subscribe("submission_progress", (msg) => {
    //   console.log("[ChatModule] 收到进度:", msg);
    //   this.addMessageToUI('ai', `进度: ${msg.data.progress * 100}%`);
    // });

    // websocket.subscribe("submission_result", (msg) => {
    //   console.log("[ChatModule] 收到最终结果:", msg);
    //   this.addMessageToUI('ai', msg.data.message);
    // });
  }

  /**
   * 初始化聊天模块
   * @param {string} mode - 模式 ('learning' 或 'sent2')
   * @param {string} contentId - 内容ID (学习内容ID或测试任务ID)
   * @param {Object} options - 配置选项
   * @param {boolean} options.enableEnterToSend - 是否启用Enter键发送消息，默认为true
   */
  init(mode, contentId, options = {}) {
    // 记录当前上下文，便于持久化
    this.currentMode = mode;
    this.currentContentId = contentId;
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
    this.bindEvents(mode, contentId, options);

    // 从本地存储回放历史（若存在）
    try {
      const participantId = getParticipantId();
      const history = participantId ? chatStorage.load(participantId) : [];
      if (history && history.length > 0) {
        // 有历史：清空默认示例消息，回放
        this.messagesContainer.innerHTML = '';
        for (const msg of history) {
          const sender = msg.role === 'user' ? 'user' : 'ai';
          this.addMessageToUI(sender, msg.content, { persist: false });
        }
      }
    } catch (e) {
      console.warn('[ChatModule] 回放历史失败:', e);
    }

    console.log('[ChatModule] 聊天模块初始化完成');
  }

  /**
   * 绑定事件监听器
   * @param {string} mode - 模式 ('learning' 或 'sent2')
   * @param {string} contentId - 内容ID
   * @param {Object} options - 配置选项
   * @param {boolean} options.enableEnterToSend - 是否启用Enter键发送消息，默认为true
   */
  bindEvents(mode, contentId, options = {}) {
    // 设置默认选项
    const { enableEnterToSend = true } = options;
    
    // 发送按钮点击事件
    this.sendButton.addEventListener('click', () => {
      this.sendMessage(mode, contentId);
      console.log('点击');
    });

    // 回车键发送消息（Shift+Enter换行）
    if (enableEnterToSend) {
      this.inputElement.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage(mode, contentId);
        }
      });
    }
  }

  /**
   * 发送消息到后端
   * @param {string} mode - 模式 ('learning' 或 'sent2')
   * @param {string} contentId - 内容ID
   */
  async sendMessage(mode, contentId) {
  // alert('sendMessage 我进来了'); 
    try { 
          console.log('[DEBUG]点击发送');
          const message = this.inputElement.value.trim();
          if (!message || this.isLoading) return;

          // 清空输入框
          this.inputElement.value = '';

          // 添加用户消息到UI（并持久化上下文）
          this.addMessageToUI('user', message, { mode, contentId });
          // 创建AI占位元素并保存到 this.streamElement
          const aiEl = this.addMessageToUI('ai', "", { mode, contentId });
          this.streamElement = aiEl;
          // 开始生成：启用强制自动滚动
          this.autoScrollDuringGeneration = true;
          console.log('[chat] created streamElement', this.streamElement);
     } catch (error) {
      console.log('[ERROR] 发送消息时出错:', error);
    }
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
      if (mode === 'sent2') {
        const sent2Results = this._getsent2Results();
        if (sent2Results) {
          requestBody.sent2_results = sent2Results;
        }
      }
      
      // 发送请求以触发后端处理，实际回复通过 WebSocket 返回
      // 等待请求返回（通常为确认/排队），错误时在 catch 中解锁按钮
      await api_client.post('/chat/ai/chat2', requestBody);


     
    } catch (error) {
      console.error('[ChatModule] 发送消息时出错:', error);
      this.addMessageToUI('ai', `抱歉，我无法回答你的问题。错误信息: ${error.message}`);
      // 请求失败（不会有 WebSocket 结果），需要解锁按钮
      this.setLoadingState(false);
    }
  }
 
     appendMessageContent(messageContentElement, content) {
    // 检查元素是否存在
    if (!messageContentElement) return;
    
    // 初始化缓冲
    if (!messageContentElement._renderBuffer) messageContentElement._renderBuffer = '';
    messageContentElement._renderBuffer += content;

    const messagesContainer = this.messagesContainer;

    // 如果已经有定时器就不重复开
    if (!messageContentElement._renderTimer) {
        messageContentElement._renderTimer = setInterval(() => {
            if (!messageContentElement._renderBuffer) return;

            // 全量渲染：拿到完整内容
            const fullText = messageContentElement._renderBuffer;

      // 每次都把整个内容重新解析
      messageContentElement.innerHTML = marked.parse(fullText);

      // 滚动到底部：如果正在生成且强制滚动开启，始终滚动；否则仅在接近底部时滚动
      try {
        const distanceFromBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight;
        if (this.autoScrollDuringGeneration) {
          messagesContainer.scrollTo({ top: messagesContainer.scrollHeight, behavior: 'auto' });
        } else {
          const threshold = 80;
          if (distanceFromBottom <= threshold) {
            const useSmooth = distanceFromBottom < threshold;
            messagesContainer.scrollTo({ top: messagesContainer.scrollHeight, behavior: useSmooth ? 'smooth' : 'auto' });
          }
        }
      } catch (e) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
        }, 100); // 每隔 2 秒全量渲染一次
    }

    // 在 stream_end 时调用，确保完整内容最终渲染
    messageContentElement._flushFn = () => {
        if (messageContentElement._renderBuffer) {
            messageContentElement.innerHTML = marked.parse(messageContentElement._renderBuffer);
        }
        if (messageContentElement._renderTimer) {
            clearInterval(messageContentElement._renderTimer);
            messageContentElement._renderTimer = null;
        }
    };
}
  /**
   * 添加消息到UI
   * @param {string} sender - 发送者 ('user' 或 'ai')
   * @param {string} content - 消息内容
   */
  addMessageToUI(sender, content, options = {}) {
    const { persist = true, mode = null, contentId = null } = options;
    if (!this.messagesContainer) return;

    // 确保content不是undefined或null
    const safeContent = content || "";

    const messageElement = document.createElement('div');
    messageElement.classList.add(`${sender}-message`);
    let aiContent;
    if (sender === 'user') {
      const contentDiv = document.createElement('div');
      contentDiv.className = 'markdown-content';
      contentDiv.textContent = safeContent;
      messageElement.innerHTML = `
        <div class="user-avatar">你</div>
        <div class="user-content">
          ${contentDiv.outerHTML}
        </div>
      `;
      //alert(safeContent);
    } else {
      messageElement.innerHTML = `
        <div class="ai-avatar">AI</div>
        <div class="ai-content">
          <div class="markdown-content"></div>
        </div>
      `;
      aiContent = messageElement.querySelector('.markdown-content');
      // 如果初始 content 非空，立刻进入增量渲染流程
      if (safeContent) {
        try {
          this.appendMessageContent(aiContent, safeContent);
        } catch (e) {
          console.warn('[ChatModule] append 初始 AI 内容失败，回退为 textContent', e);
          aiContent.textContent = safeContent;
        }
      }
    }

    this.messagesContainer.appendChild(messageElement);

    // 滚动到底部：如果正在生成且强制滚动开启则强制，否则仅在接近底部时滚动
    try {
      const distanceFromBottom = this.messagesContainer.scrollHeight - this.messagesContainer.scrollTop - this.messagesContainer.clientHeight;
      if (this.autoScrollDuringGeneration) {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
      } else {
        const threshold = 80;
        if (distanceFromBottom <= threshold) this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
      }
    } catch (e) {
      // ignore
    }
    
    // 持久化消息 (对于AI消息，仅在非流式传输时保存，流式传输的消息由stream_end处理)
    try {
      if (persist) {
        const participantId = getParticipantId();
        if (participantId) {
          // 对于AI消息且在流式传输过程中，不立即保存，等待stream_end处理
          const isStreamingAI = sender === 'ai' && this.isLoading && this.aiMessageBuffer !== null;
          
          if (!isStreamingAI) {
            chatStorage.append(participantId, {
              role: sender === 'user' ? 'user' : 'assistant',
              content: safeContent,
              mode,
              contentId,
              ts: Date.now(),
            });
          }
        }
      }
    } catch (e) {
      console.warn('[ChatModule] 持久化消息失败:', e);
    }
    if (sender === 'ai') {
      console.log('返回内容', aiContent);
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
      if (this.autoScrollDuringGeneration) {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
      } else {
        const wasNearBottom = this.messagesContainer ? (this.messagesContainer.scrollHeight - this.messagesContainer.scrollTop - this.messagesContainer.clientHeight) <= 80 : true;
        if (wasNearBottom) this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
      }
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
  _getsent2Results() {
    const resultsContainer = document.getElementById('sent2-results-content');
    if (!resultsContainer || !resultsContainer.innerHTML.trim()) {
      return null;
    }

    const results = [];
    const overallStatus = resultsContainer.classList.contains('sent2-result-passed') ? 'success' : 'error';

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
          // 如果是AI消息且有渲染缓冲区，优先使用缓冲区内容
          if (isAiMessage && markdownContent._renderBuffer) {
            textContent = markdownContent._renderBuffer;
          } else {
            // 否则使用元素的文本内容
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
