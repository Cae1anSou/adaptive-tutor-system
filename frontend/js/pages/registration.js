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

    // 重置按钮状态（处理页面后退的情况）
    if (startButton) {
        startButton.disabled = false;
        startButton.innerHTML = '<iconify-icon icon="mdi:play" width="20" height="20"></iconify-icon> 开始学习';
    }

    // 监听输入变化
    if (nicknameInput) {
        nicknameInput.addEventListener('input', checkFormValid);
        nicknameInput.addEventListener('blur', validateNickname);
    }

    if (themeSelector) {
        themeSelector.addEventListener('change', checkFormValid);
    }

    // 开始按钮点击处理
    if (startButton) {
        startButton.addEventListener('click', async () => {
            const nickname = nicknameInput?.value.trim() || '';
            const theme = themeSelector?.value || '';

            // 验证输入
            if (!nickname) {
                showError('请输入学习昵称');
                nicknameInput?.focus();
                return;
            }

            if (!theme) {
                showError('请选择学习主题');
                themeSelector?.focus();
                return;
            }

            // 禁用按钮，防止重复点击
            startButton.disabled = true;
            const originalText = startButton.innerHTML;
            startButton.innerHTML = '<iconify-icon icon="mdi:loading" width="20" height="20" class="spin"></iconify-icon> 启动中...';

            try {
                // 生成基于昵称和主题的用户ID
                const participantId = generateParticipantId(nickname, theme);

                // 使用统一的apiClient方法发送请求
                const result = await apiClient.postWithoutAuth('/session/initiate', {
                    participant_id: participantId,
                    nickname: nickname,
                    theme: theme
                });

                if (result.code === 200 || result.code === 201) {
                    saveParticipantId(result.data.participant_id);
                    // 直接跳转到学习页面
                    navigateTo('/pages/learning_page.html', '1_1', true);
                } else {
                    showError(result.message || '启动失败，请重试');
                    // 恢复按钮状态
                    startButton.disabled = false;
                    startButton.innerHTML = originalText;
                    checkFormValid();
                }
            } catch (error) {
                console.error('启动请求失败:', error);
                showError('网络错误，请检查网络连接后重试');
                // 恢复按钮状态
                startButton.disabled = false;
                startButton.innerHTML = originalText;
                checkFormValid();
            }
        });
    }

    // 检查表单是否有效
    function checkFormValid() {
        const nickname = nicknameInput?.value.trim() || '';
        const theme = themeSelector?.value || '';
        const isValid = nickname.length >= 2 && theme;

        if (startButton) {
            startButton.disabled = !isValid;
        }
    }

    // 验证昵称
    function validateNickname() {
        const nickname = nicknameInput?.value.trim() || '';
        if (nickname && nickname.length < 2) {
            showError('昵称至少需要2个字符');
            return false;
        }
        return true;
    }

    // 生成参与者ID（直接使用昵称）
    function generateParticipantId(nickname, theme) {
        // 清理昵称，只保留字母数字和中文
        const cleanNickname = nickname.replace(/[^\w\u4e00-\u9fa5]/g, '').trim();
        return cleanNickname;
    }


    // 获取主题名称
    function getThemeName(theme) {
        const names = {
            'pets': '宠物世界',
            'shopping': '购物商城',
            'travel': '旅游探索',
            'food': '美食天地',
            'fitness': '健身达人',
            'music': '音乐空间'
        };
        return names[theme] || '学习';
    }

    // 显示错误提示
    function showError(message) {
        // 简单的错误提示，可以后续优化为更好的UI组件
        alert('❌ ' + message);
    }

    // 显示成功提示
    function showSuccess(message) {
        // 简单的成功提示，可以后续优化为更好的UI组件
        alert('✅ ' + message);
    }

    // 初始化检查表单状态
    checkFormValid();
});

// 监听页面显示事件（包括从缓存恢复）
window.addEventListener('pageshow', (event) => {
    const startButton = document.getElementById('start-button');
    if (startButton) {
        // 重置按钮状态
        startButton.disabled = false;
        startButton.innerHTML = '<iconify-icon icon="mdi:play" width="20" height="20"></iconify-icon> 开始学习';

        // 重新检查表单有效性
        const nicknameInput = document.getElementById('nickname-input');
        const themeSelector = document.getElementById('theme-selector');
        if (nicknameInput && themeSelector) {
            const nickname = nicknameInput.value.trim() || '';
            const theme = themeSelector.value || '';
            const isValid = nickname.length >= 2 && theme;
            startButton.disabled = !isValid;
        }
    }
});