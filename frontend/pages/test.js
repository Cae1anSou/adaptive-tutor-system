let currentAiMessageElement = null;
import websocket from '../js/modules/socket.js';
            websocket.onOpen(() => {
              updateConnectionStatus(true); 
               document.getElementById('messageInput').disabled = false;
               document.getElementById('sendBtn').disabled = false; 
            });
            websocket.onMessage((data, rawEvent) => {
                    //console.log("外部捕获消息:", data);
                    if (data.type === "stream_start") {
                        // 开始流式传输
                        //this.showTypingIndicator(false);
                        currentAiMessageElement = addMessage('', 'ai', 'AI');
                    } else if (data.type === "stream") {
                        // 流式传输中
                        if (currentAiMessageElement) {
                            appendMessageContent(currentAiMessageElement, data.message);
                        }
                    } else if (data.type === "stream_end") {
                                // 流式传输结束：如果 stream_end 携带最后一段文本，先通过 appendMessageContent 入缓冲，
                                // 然后调用元素的分片 flush 函数完成剩余内容，避免一次性大块追加
                                if (currentAiMessageElement) {
                                    const el = currentAiMessageElement;
                                    if (data.message) {
                                        appendMessageContent(el, data.message);
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
                    else {
                        // 普通消息
                        addMessage(data.message, 'received', data.sender);
                    }
            });
            websocket.onClose(() => {
                updateConnectionStatus(false);
                document.getElementById('messageInput').disabled = true;
                document.getElementById('sendBtn').disabled = true;
            });
           // 添加消息到消息容器
            function addMessage(message, type, sender = '系统') {
                const messagesContainer = document.getElementById('messagesContainer');
                
                // // 移除初始系统消息（如果存在）
                // const systemMessage = messagesContainer.querySelector('.system-message');
                // if (systemMessage && messagesContainer.children.length > 1) {
                //     systemMessage.remove();
                // }
                
                let messageContent; // 在函数作用域顶部声明变量
                
                if (type === 'system') {
                    const systemMsgElement = document.createElement('div');
                    systemMsgElement.className = 'system-message';
                    systemMsgElement.textContent = message;
                    messagesContainer.appendChild(systemMsgElement);
                } else {
                    const messageElement = document.createElement('div');
                    messageElement.className = `message ${type}`;
                    
                    const messageInfo = document.createElement('div');
                    messageInfo.className = 'message-info';
                    messageInfo.textContent = `${sender} • ${new Date().toLocaleTimeString()}`;
                    
                    messageContent = document.createElement('div');
                    messageContent.className = 'message-content';
                    messageContent.textContent = message;
                    
                    messageElement.appendChild(messageInfo);
                    messageElement.appendChild(messageContent);
                    messagesContainer.appendChild(messageElement);
                }
                
                // 滚动到底部
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                
                return messageContent;
            }    
            function appendMessageContent(messageContentElement, content) {
                // 按流缓冲起来，使用 requestAnimationFrame 分片追加，避免每次小片段都触发大量重排
                if (!messageContentElement._streamBuffer) messageContentElement._streamBuffer = '';
                messageContentElement._streamBuffer += content;

                // 如果已有调度则无需重复调度
                if (messageContentElement._rafScheduled) return;
                messageContentElement._rafScheduled = true;

                const messagesContainer = document.getElementById('messagesContainer');

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
            function updateConnectionStatus(connected) {
                const statusDot = document.getElementById('statusDot');
                const statusText = document.getElementById('statusText');
                
                if (connected) {
                    statusDot.classList.add('connected');
                    statusText.textContent = '已连接';
                } else {
                    statusDot.classList.remove('connected');
                    statusText.textContent = '未连接';
                }
            }
        // 添加事件监听器
        document.getElementById('connectBtn').addEventListener('click', () => {
            websocket.connect();
        });

        document.getElementById('disconnectBtn').addEventListener('click', () => {
            websocket.disconnect();
        });

        document.getElementById('sendBtn').addEventListener('click', () => {
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();
            if (message) {
                addMessage(message, 'sent', '我');
                websocket.sendMessage(message);
                messageInput.value = '';
            }
        });

        document.getElementById('messageInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                document.getElementById('sendBtn').click();
            }
        });