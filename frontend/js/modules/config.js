// frontend/js/modules/config.js

// A globally accessible object to hold configuration.
export const AppConfig = {
  api_base_url: "/api/v1",
  backend_port: 8000,  // 默认端口，会被后端配置覆盖
  endpoints: {
    chat: '/chat/ai/chat',
    chatHistory: '/chat/history',
    sessionInitiate: '/session/initiate',
    config: '/config/'
  },
  // API响应状态码
  statusCodes: {
    SUCCESS: 200,
    BAD_REQUEST: 400,
    UNAUTHORIZED: 401,
    FORBIDDEN: 403,
    NOT_FOUND: 404,
    INTERNAL_SERVER_ERROR: 500,
    NOT_IMPLEMENTED: 501
  },
  // 错误消息配置，避免硬编码
  errorMessages: {
    sessionNotFound: '会话已过期，请重新登录。',
    networkError: '网络连接失败，请检查后端服务器是否运行。',
    serverError: '服务器内部错误，请稍后重试。',
    invalidRequest: '请求参数错误，请检查输入内容。',
    accessDenied: '访问被拒绝，请检查权限设置。',
    unknownError: '抱歉，我暂时无法回复，请稍后再试。'
  }
};

/**
 * Fetches configuration from the backend.
 * Should be called once when the application starts.
 */
export async function initializeConfig() {
  try {
    // 构建配置API的URL
    const hostname = window.location.hostname;
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
    const configUrl = isLocalhost 
      ? `http://localhost:${AppConfig.backend_port}/api/v1/config/`
      : '/api/v1/config/';
      
    const response = await fetch(configUrl);
    const result = await response.json();

    if (result.code !== 200) {
      throw new Error(result.message);
    }

    Object.assign(AppConfig, result.data);
    console.log("Frontend configuration loaded:", AppConfig);
  } catch (error) {
    console.error("Could not initialize frontend configuration:", error);
    console.log("Using default configuration:", AppConfig);
  }
}