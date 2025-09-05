//import { buildWebSocketUrl } from '../api_client.js';
import { buildBackendUrl } from './config.js';
import { getParticipantId } from './session.js';
function buildWebSocketUrl(endpoint) {
    const backendUrl = buildBackendUrl(endpoint); 
    // 将 http:// 或 https:// 替换为 ws:// 或 wss://
    let wsUrl = backendUrl.replace(/^(http)/, 'ws');
    return wsUrl;
}

class WebSocketManager {
            constructor() {
                this.socket = null;
                //this.state = "CLOSED";//CONNECTING|OPEN|CLOSED
                this.reconnectAttempts = 0;
                this.maxReconnectAttempts = 5;
                this.subscribers = {};  //{type:[callbacks]}
            }
            
            subscribe(type,callback){
                if(!this.subscribers[type])this.subscribers[type] = [];
                this.subscribers[type].push(callback);
            }

            unsubscribe(type,callback){
                if (this.subscribers[type]) {
                this.subscribers[type] = this.subscribers[type].filter(cb => cb !== callback);
            }}

            // 取消所有特定类型的消息订阅
            unsubscribeAll(type) {
                if (this.subscribers[type]) {
                    this.subscribers[type] = [];
                }
            }

            _dispatch_message(rawMessage){
                const { type, taskid, message, error, timestamp } = rawMessage;
                if (this.subscribers[type]) {
                   this.subscribers[type].forEach(callback => callback(message));
                    }else {
                    console.warn(`收到未处理的消息类型: ${type}`, message);
                    }
            }
            
            // 连接WebSocket
            async connect() {
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    return;
                }
                try {
                    // 获取 participantId 并确保正确编码
                    const participantId = getParticipantId();
                    if (!participantId) {
                        console.error('无法获取 participantId，无法建立 WebSocket 连接');
                        return;
                    }
                    //const wsUrl = buildWebSocketUrl(getParticipantId());
                    // 正确编码 participantId（特别是中文字符）
                    const encodedParticipantId = encodeURIComponent(participantId);
                    const wsUrl = buildWebSocketUrl(`/ws/user/${encodedParticipantId}`);
                    //const wsUrl = `${protocol}//localhost:8000/ws/chat/${this.userId}`;
                    //alert('WebSocket URL: ' + wsUrl);
                    this.socket = new WebSocket(wsUrl);
                    this.socket.onopen = () => {
                        this.reconnectAttempts = 0; // 重置重连尝试次数
                       
                    };
                    this.socket.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            this._dispatch_message(data);
                        } catch (e) {
                            //this.addMessage(event.data, 'received', '系统');
                            console.error('解析消息错误:', e);
                        }
                    };
                    
                    this.socket.onclose = (event) => {
                        this._tryReconnect();
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
            _tryReconnect() {
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    const delay = Math.pow(2, this.reconnectAttempts) * 1000;
                    console.log(`重连中 (${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})，等待 ${delay}ms`);
                    setTimeout(() => this.connect(), delay);
                    this.reconnectAttempts++;
                } else {
                    console.error("WebSocket 达到最大重连次数");
                }
            }
            
            // 断开WebSocket连接
            disconnect() {
                if (this.socket) {
                    this.socket.close();
                    this.socket = null;
                }
            }
            
            
        }
// 导出单例
const websocket = new WebSocketManager();
export default websocket;