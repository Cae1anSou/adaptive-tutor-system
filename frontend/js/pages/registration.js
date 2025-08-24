// frontend/js/pages/registration.js
import { saveParticipantId, checkAndRedirect } from '../modules/session.js';
import { AppConfig, initializeConfig } from '../modules/config.js';
import { setupHeaderTitle } from '../modules/navigation.js';
import websocket from '../modules/socket.js';
// 页面加载时先检查是否已有会话
// checkAndRedirect(); // 暂时注释掉，避免在注册页面直接跳转

document.addEventListener('DOMContentLoaded', async () => {
    // 初始化配置
    await initializeConfig();
    // 设置标题点击跳转到首页（刷新）
    setupHeaderTitle('/index.html');
    
    const startButton = document.getElementById('start-button');
    const usernameInput = document.getElementById('username-input');

    if (startButton && usernameInput) {
        startButton.addEventListener('click', async () => {
            const username = usernameInput.value.trim();
            //websocket.userId = username; // 设置WebSocket的用户ID
            //websocket.connect(); // 尝试连接WebSocket
            // 简单的输入校验
            if (!username) {
                alert('请输入用户ID');
                return;
            }

            // 禁用按钮，防止重复点击
            startButton.disabled = true;
            startButton.textContent = '处理中...';

            try {
                // 确保backend_port有默认值
                const backendPort = AppConfig.backend_port || 8000;
                // 构建完整的后端API URL
                const backendUrl = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
                    ? `http://localhost:${backendPort}${AppConfig.api_base_url}/session/initiate`
                    : `${AppConfig.api_base_url}/session/initiate`;
                    
                const response = await fetch(backendUrl, { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ participant_id: username }),
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const result = await response.json();

                if (result.code === 200 || result.code === 201) {
                    saveParticipantId(result.data.participant_id);
                    // 注册成功后，跳转到知识图谱页面
                    window.location.href = `/pages/knowledge_graph.html`;
                } else {
                    alert(result.message || '注册失败，请重试');
                }
            } catch (error) {
                console.error('注册请求失败:', error);
                alert('网络错误，请检查网络连接后重试');
            } finally {
                // 恢复按钮状态
                startButton.disabled = false;
                startButton.textContent = '开始学习';
            }
        });
    }
});