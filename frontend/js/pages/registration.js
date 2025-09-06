// frontend/js/pages/registration.js
import { saveParticipantId, checkAndRedirect } from '../modules/session.js';
import { AppConfig, initializeConfig } from '../modules/config.js';
import { setupHeaderTitle, navigateTo } from '../modules/navigation.js';
import websocket from '../modules/websocket_client.js';
import apiClient from '../api_client.js';

// 页面加载时先检查是否已有会话
// checkAndRedirect(); // 暂时注释掉，避免在注册页面直接跳转

document.addEventListener('DOMContentLoaded', async () => {
    // 初始化配置
    await initializeConfig();
    // 设置标题点击跳转到首页（刷新）
    setupHeaderTitle('/index.html');

    const startButton = document.getElementById('start-button');
    const nicknameInput = document.getElementById('nickname-input');
    const themeSelector = document.getElementById('theme-selector');

    // 检查表单有效性
    function checkFormValid() {
        const nickname = nicknameInput.value.trim();
        const theme = themeSelector.value;
        return nickname.length > 0 && theme.length > 0;
    }

    // 验证昵称
    function validateNickname(nickname) {
        if (!nickname) {
            return { valid: false, message: '请输入昵称' };
        }
        if (nickname.length < 2) {
            return { valid: false, message: '昵称至少需要2个字符' };
        }
        if (nickname.length > 20) {
            return { valid: false, message: '昵称不能超过20个字符' };
        }
        // 检查是否包含特殊字符
        const specialChars = /[<>:"/\\|?*]/;
        if (specialChars.test(nickname)) {
            return { valid: false, message: '昵称不能包含特殊字符' };
        }
        return { valid: true };
    }

    // 获取主题名称
    function getThemeName(themeValue) {
        const themeNames = {
            'pets': '萌宠乐园',
            'shopping': '时尚购物',
            'music': '影音娱乐'
        };
        return themeNames[themeValue] || themeValue;
    }

    // 生成参与者ID
    function generateParticipantId() {
        const nickname = nicknameInput.value.trim();
        const cleanNickname = nickname.replace(/[^a-zA-Z0-9\u4e00-\u9fa5]/g, '');
        return cleanNickname;
    }

    // 显示错误信息
    function showError(message) {
        alert(message);
    }

    // 显示成功信息
    function showSuccess(message) {
        alert(message);
    }

    // 监听输入变化，实时检查表单有效性
    if (nicknameInput) {
        nicknameInput.addEventListener('input', () => {
            startButton.disabled = !checkFormValid();
        });
    }

    if (themeSelector) {
        themeSelector.addEventListener('change', () => {
            startButton.disabled = !checkFormValid();
        });
    }

    // 重置按钮状态（处理浏览器后退情况）
    startButton.disabled = !checkFormValid();

    // 处理页面显示事件（包括从浏览器缓存恢复）
    window.addEventListener('pageshow', (event) => {
        // 重置按钮状态
        startButton.disabled = !checkFormValid();
        startButton.innerHTML = `
            <iconify-icon icon="mdi:play" width="20" height="20"></iconify-icon>
            开始学习
        `;
    });

    if (startButton && nicknameInput && themeSelector) {
        startButton.addEventListener('click', async () => {
            const nickname = nicknameInput.value.trim();
            const theme = themeSelector.value;

            // 验证昵称
            const nicknameValidation = validateNickname(nickname);
            if (!nicknameValidation.valid) {
                showError(nicknameValidation.message);
                return;
            }

            // 验证主题选择
            if (!theme) {
                showError('请选择学习主题');
                return;
            }

            // 禁用按钮，防止重复点击
            startButton.disabled = true;
            startButton.innerHTML = `
                <iconify-icon icon="mdi:loading" width="20" height="20" style="animation: spin 1s linear infinite;"></iconify-icon>
                启动中...
            `;

            try {
                // 生成参与者ID
                const participantId = generateParticipantId();

                // 使用统一的apiClient方法发送请求
                const result = await apiClient.postWithoutAuth('/session/initiate', {
                    participant_id: participantId,
                    group: 'control'
                });

                if (result.code === 200 || result.code === 201) {
                    saveParticipantId(result.data.participant_id);

                    // 直接跳转到学习页面，不显示确认弹窗
                    navigateTo('/pages/learning_page.html', '1_1', true);
                } else {
                    showError(result.message || '注册失败，请重试');
                }
            } catch (error) {
                console.error('注册请求失败:', error);
                showError('网络错误，请检查网络连接后重试');
            } finally {
                // 恢复按钮状态
                startButton.disabled = false;
                startButton.innerHTML = `
                    <iconify-icon icon="mdi:play" width="20" height="20"></iconify-icon>
                    开始学习
                `;
            }
        });
    }
});
