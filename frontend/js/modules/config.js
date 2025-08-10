// frontend/js/modules/config.js

// A globally accessible object to hold configuration.
export const AppConfig = {
  api_base_url: "/api/v1"
  //  model_name_for_display:null
};

/**
 * Fetches configuration from the backend.
 * Should be called once when the application starts.
 */

export async function initializeConfig() {
  try {
    const response = await fetch(`${window.FrontendConfig.getApiBaseUrl()}/config/`);
    const result = await response.json();

    if (result.code !== 200) {
      throw new Error(result.message);
    }

    Object.assign(AppConfig, result.data);
    console.log("Frontend configuration loaded:", AppConfig);
  } catch (error) {
    console.error("Could not initialize frontend configuration:", error);
  }
}