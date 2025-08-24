//TODO:Aeolyn:对接chat.js
//TODO:Aeolyn:对接上chat.js后将manager和connector逻辑分离
import {AppConfig} from './config.js'
class WebSocketManager {
            constructor() {
                this.socket = null;
                this.userId = null;
                this.reconnectAttempts = 0;
                this.maxReconnectAttempts = 5;
                this.currentAiMessageElement = null;
                this.onMessageCallback = null;
                this.onOpenCallback = null;
                this.onCloseCallback = null;
            }
            // 允许外部注册回调
            onMessage(callback) {
                 this.onMessageCallback = callback;
            }
            onOpen(callback) {
                 this.onOpenCallback = callback;
            }
            onClose(callback) {
                 this.onCloseCallback = callback;
            }
            // 连接WebSocket
            connect() {
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    //this.addMessage('WebSocket 已经连接', 'system');
                    //弹出界面
                    //alert('WebSocket 已经连接');
                    return;
                }
                try {
                    //alert('开始连接WebSocket');
                    // 构建WebSocket URL，包含用户ID作为查询参数
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    // 分开写 host 和 port
                    const host = window.location.hostname;  // 只拿到域名或IP，不带端口
                    const port =  AppConfig.backend_port;
                    // 没有 port 时用默认 80/443
                    const wsUrl = `${protocol}//${host}:${port}/ws/chat/${this.userId}`;
                    //const wsUrl = `${protocol}//localhost:8000/ws/chat/${this.userId}`;
                    alert('WebSocket URL: ' + wsUrl);
                    this.socket = new WebSocket(wsUrl);
                    
                    this.socket.onopen = () => {
                        if (this.onOpenCallback) {
                               this.onOpenCallback();
                            }
                        this.updateConnectionStatus(true);
                        this.addMessage('WebSocket 连接已建立', 'system');
                        this.reconnectAttempts = 0; // 重置重连尝试次数
                        
                        // 启用发送消息的输入框和按钮
                        document.getElementById('messageInput').disabled = false;
                        document.getElementById('sendBtn').disabled = false;
                    };
                    //TODO:Aeolyn:将流式输出部分拆成单独的工具函数
                    this.socket.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            if (this.onMessageCallback) {
                               this.onMessageCallback(data, event);
                            }
                            /* 
                            if (data.type === "stream_start") {
                                // 开始流式传输
                                //this.showTypingIndicator(false);
                                this.currentAiMessageElement = this.addMessage('', 'ai', 'AI');
                            } else if (data.type === "stream") {
                                // 流式传输中
                                if (this.currentAiMessageElement) {
                                    this.appendMessageContent(this.currentAiMessageElement, data.message);
                                }
                            } else if (data.type === "stream_end") {
                                        // 流式传输结束：如果 stream_end 携带最后一段文本，先通过 appendMessageContent 入缓冲，
                                        // 然后调用元素的分片 flush 函数完成剩余内容，避免一次性大块追加
                                        if (this.currentAiMessageElement) {
                                            const el = this.currentAiMessageElement;
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
                                        this.currentAiMessageElement = null;
                                    } else {
                                // 普通消息
                                this.addMessage(data.message, 'received', data.sender);
                            }
                            */
                        } catch (e) {
                            //this.addMessage(event.data, 'received', '系统');
                            console.error('解析消息错误:', e);
                        }
                    };
                    
                    this.socket.onclose = (event) => {
                        //this.updateConnectionStatus(false);
                        //this.addMessage('WebSocket 连接已关闭', 'system');
                        
                        // 禁用发送消息的输入框和按钮
                        // document.getElementById('messageInput').disabled = true;
                        // document.getElementById('sendBtn').disabled = true;
                        if (this.onCloseCallback) {
                               this.onCloseCallback();
                            }
                        // 尝试重新连接
                        if (this.reconnectAttempts < this.maxReconnectAttempts) {
                            this.reconnectAttempts++;
                            //this.addMessage(`尝试重新连接 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`, 'system');
                            setTimeout(() => this.connect(), 3000);
                        }
                    };
                    
                    this.socket.onerror = (error) => {
                        //this.addMessage('WebSocket 错误发生', 'system');
                        console.error('WebSocket error:', error);
                    };
                    
                } catch (error) {
                    console.error('Failed to connect WebSocket:', error);
                    //this.addMessage('连接失败: ' + error.message, 'system');
                }
            }
            
            
            // // 发送消息
            // sendMessage(message) {
            //     if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            //         const messageData = {
            //             userId: this.userId,
            //             message: message
            //         };
            //         this.socket.send(JSON.stringify(messageData));
            //         //this.addMessage(message, 'sent', '我');
            //         //this.showTypingIndicator(true);
            //     } else {
            //         this.addMessage('无法发送消息，WebSocket未连接', 'system');
            //     }
            // }
            
            // 断开WebSocket连接
            disconnect() {
                if (this.socket) {
                    this.socket.close();
                    this.socket = null;
                }
                //this.updateConnectionStatus(false);
            }
            
            // 更新连接状态UI
            // updateConnectionStatus(connected) {
            //     const statusDot = document.getElementById('statusDot');
            //     const statusText = document.getElementById('statusText');
                
            //     if (connected) {
            //         statusDot.classList.add('connected');
            //         statusText.textContent = '已连接';
            //     } else {
            //         statusDot.classList.remove('connected');
            //         statusText.textContent = '未连接';
            //     }
            // }
            
            // 显示/隐藏打字指示器
            // showTypingIndicator(show) {
            //     const typingIndicator = document.getElementById('typingIndicator');
            //     typingIndicator.style.display = show ? 'block' : 'none';
            // }
            
            // 添加消息到消息容器
            // addMessage(message, type, sender = '系统') {
            //     const messagesContainer = document.getElementById('messagesContainer');
                
            //     // // 移除初始系统消息（如果存在）
            //     // const systemMessage = messagesContainer.querySelector('.system-message');
            //     // if (systemMessage && messagesContainer.children.length > 1) {
            //     //     systemMessage.remove();
            //     // }
                
            //     let messageContent; // 在函数作用域顶部声明变量
                
            //     if (type === 'system') {
            //         const systemMsgElement = document.createElement('div');
            //         systemMsgElement.className = 'system-message';
            //         systemMsgElement.textContent = message;
            //         messagesContainer.appendChild(systemMsgElement);
            //     } else {
            //         const messageElement = document.createElement('div');
            //         messageElement.className = `message ${type}`;
                    
            //         const messageInfo = document.createElement('div');
            //         messageInfo.className = 'message-info';
            //         //messageInfo.textContent = `${sender} • ${new Date().toLocaleTimeString()}`;
                    
            //         messageContent = document.createElement('div');
            //         messageContent.className = 'message-content';
            //         messageContent.textContent = message;
                    
            //         messageElement.appendChild(messageInfo);
            //         messageElement.appendChild(messageContent);
            //         messagesContainer.appendChild(messageElement);
            //     }
                
            //     // 滚动到底部
            //     messagesContainer.scrollTop = messagesContainer.scrollHeight;
                
            //     return messageContent;
            // }
            
            // 追加内容到消息元素（更平滑的流式渲染）
            // TODO:流式参考
            // appendMessageContent(messageContentElement, content) {
            //     // 按流缓冲起来，使用 requestAnimationFrame 分片追加，避免每次小片段都触发大量重排
            //     if (!messageContentElement._streamBuffer) messageContentElement._streamBuffer = '';
            //     messageContentElement._streamBuffer += content;

            //     // 如果已有调度则无需重复调度
            //     if (messageContentElement._rafScheduled) return;
            //     messageContentElement._rafScheduled = true;

            //     const messagesContainer = document.getElementById('messagesContainer');

            //     const FLUSH_CHUNK = 2; // 每帧最多追加的字符数，调大或调小以平衡流畅度与实时性

            //     const flush = () => {
            //         messageContentElement._rafScheduled = false;

            //         // 每次从缓冲区取出一段字符追加
            //         const buffer = messageContentElement._streamBuffer || '';
            //         if (!buffer) return;

            //         const toAppend = buffer.slice(0, FLUSH_CHUNK);
            //         // 使用 textContent 追加纯文本，避免 XSS 和重解析
            //         messageContentElement.textContent += toAppend;

            //         // 剩余写回缓冲区
            //         messageContentElement._streamBuffer = buffer.slice(FLUSH_CHUNK);

            //         // 平滑滚动到底部，但仅在用户接近底部时使用 smooth，避免用户查看历史消息时被打断
            //         try {
            //             const distanceFromBottom = messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight;
            //             const useSmooth = distanceFromBottom < 80; // 阈值可调整
            //             messagesContainer.scrollTo({ top: messagesContainer.scrollHeight, behavior: useSmooth ? 'smooth' : 'auto' });
            //         } catch (e) {
            //             // fallback
            //             messagesContainer.scrollTop = messagesContainer.scrollHeight;
            //         }

            //         // 如果还有缓冲则在下一帧继续刷新
            //         if (messageContentElement._streamBuffer && messageContentElement._streamBuffer.length > 0) {
            //             messageContentElement._rafScheduled = true;
            //             requestAnimationFrame(flush);
            //         }
            //     };

            //     // 将 flush 暴露到元素，以便 stream_end 调用时触发分片完成
            //     messageContentElement._flushFn = () => {
            //         // 如果已经在调度中，flush 会在当前 rAF 循环中自动完成
            //         if (messageContentElement._rafScheduled) return;
            //         messageContentElement._rafScheduled = true;
            //         requestAnimationFrame(flush);
            //     };

            //     // 首次调度
            //     requestAnimationFrame(flush);
            // }
        }
// 导出单例
const websocket = new WebSocketManager();
export default websocket;