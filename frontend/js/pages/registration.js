// frontend/js/pages/registration.js
import { saveLocalParticipantId } from '../services/session_service.js';
import ApiClient, { resolveEndpoint } from '../api_client.js';

// 页面加载时先检查是否已有会话
// TODO: 实现 checkAndRedirect 逻辑

const startButton = document.getElementById('start-button');
const usernameInput = document.getElementById('username-input');

startButton.addEventListener('click', async () => {
  // ... (按钮禁用、输入校验等UI逻辑) ...
  const username = usernameInput.value.trim();
  const endpoint = resolveEndpoint('sessionInitiate', '/session/initiate');
  const result = await ApiClient.post(endpoint, { username });

  if (result.code === 200 || result.code === 201) {
        saveLocalParticipantId(result.data.participant_id);
        // 注册成功后，跳转到“前测问卷”页面，这是科研流程的一部分
        window.location.href = `/survey.html?type=pre-test`;
  } else {
        alert(result.message);
  }
});