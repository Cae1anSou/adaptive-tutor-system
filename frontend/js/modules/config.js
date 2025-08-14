// frontend/js/modules/config.js

// A globally accessible object to hold configuration.
export const AppConfig = {
  api_base_url: "/api/v1",
  backend_port: 8000  // 默认端口，会被后端配置覆盖
  //  model_name_for_display:null
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