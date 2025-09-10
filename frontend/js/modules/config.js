// frontend/js/modules/config.js

// A globally accessible object to hold configuration.
export const AppConfig = {
  api_base_url: "/api/v1",
  backend_port: 8000,  // 默认端口，会被后端配置覆盖
  //  model_name_for_display:null
};

/**
 * Fetches configuration from the backend.
 * Should be called once when the application starts.
 */
export async function initializeConfig() {
  try {
    // We construct the URL manually here for the initial config fetch
    // 在所有环境中都使用相对路径，通过Nginx代理
    const configUrl = '/api/v1/config';
      
    const response = await fetch(configUrl, { credentials: 'same-origin' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const result = await response.json();

    if (result.code !== 200) {
      throw new Error(result.message);
    }

    Object.assign(AppConfig, result.data);
    console.log("Frontend configuration loaded:", AppConfig);
  } catch (error) {
    console.error("Could not initialize frontend configuration:", error);
    // Fallback to default port if config load fails in development
    // 确保即使配置加载失败，也有默认值，使用相对路径避免CORS问题
    const defaultPort = 8000;
    AppConfig.backend_port = AppConfig.backend_port || defaultPort;
    // 使用相对路径而不是绝对URL来避免CORS问题
    AppConfig.api_base_url = "/api/v1";
    console.log('[Config] Using fallback API base:', AppConfig.api_base_url);
  }
}

/**
 * 构建完整的后端API URL
 * @param {string} endpoint - API endpoint (e.g., /chat/completions)
 * @returns {string} 完整的API URL
 */
export function buildBackendUrl(endpoint = '') {
  const path = `${AppConfig.api_base_url}${endpoint}`;
  
  // 在所有环境中都使用相对路径，通过Nginx代理
  return path;
}

// 将函数添加到全局window对象，以便在非模块脚本中使用
window.buildBackendUrl = buildBackendUrl;
