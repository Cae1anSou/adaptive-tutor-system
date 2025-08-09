import { initializeConfig, AppConfig } from './js/modules/config.js';
import { ensureSession, getLocalParticipantId, saveLocalParticipantId } from '/js/services/session_service.js';

window.addEventListener('DOMContentLoaded', async () => {
  try {
   
    await initializeConfig();

   
    let pid = getLocalParticipantId();
    if (!pid) {
      const tmpId = (window.crypto && window.crypto.randomUUID)
        ? window.crypto.randomUUID()
        : `pid-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      saveLocalParticipantId(tmpId);
    }
    await ensureSession();

   
    console.log('当前模型：', AppConfig.model_name_for_display);

    // 初始化完成后跳转到学习页面（可改为其它页面）
    window.location.href = '/pages/learning_page.html';
  } catch (err) {
    console.error('应用初始化失败：', err);
  }
});