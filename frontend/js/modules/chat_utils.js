/**
 * Chat Utils Module
 * 
 * 提供聊天相关的通用工具函数
 */

/**
 * 从URL获取主题ID
 * @returns {string|null} 主题ID
 */
export function getTopicIdFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('topic') || null;
}

/**
 * 从URL获取任务ID
 * @returns {string|null} 任务ID
 */
export function getTaskIdFromUrl() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('task') || null;
}

/**
 * 获取代码上下文
 * @returns {Object|null} 代码上下文对象
 */
export function getCodeContext() {
  // 统一的编辑器获取函数
  const getEditorValue = (editorId, globalName) => {
    // 方法1: 直接通过ID获取
    const element = document.getElementById(editorId);
    if (element) {
      return element.value || element.textContent || '';
    }
    
    // 方法2: 尝试获取全局编辑器实例
    if (window[globalName] && typeof window[globalName].getValue === 'function') {
      return window[globalName].getValue();
    }
    
    return '';
  };
  
  const htmlCode = getEditorValue('html-editor', 'htmlEditor') || 
                   getEditorValue('html-monaco-editor', 'htmlMonacoEditor');
  const cssCode = getEditorValue('css-editor', 'cssEditor') || 
                  getEditorValue('css-monaco-editor', 'cssMonacoEditor');
  const jsCode = getEditorValue('js-editor', 'jsEditor') || 
                 getEditorValue('js-monaco-editor', 'jsMonacoEditor');
  
  // 如果所有方法都获取不到代码，返回null
  if (!htmlCode && !cssCode && !jsCode) {
    return null;
  }
  
  // 返回符合CodeContent schema的对象
  return {
    html: htmlCode || "",
    css: cssCode || "",
    js: jsCode || ""
  };
}

/**
 * 获取任务上下文
 * 根据schemas定义，应该返回TestTask对象
 * @returns {Object|null} TestTask对象或null
 */
export function getTaskContext() {
  const taskId = getTaskIdFromUrl();
  
  if (taskId) {
    // 返回符合TestTask schema的对象
    return {
      topic_id: taskId,
      title: `Task ${taskId}`,
      description_md: `Task description for ${taskId}`,
      start_code: {
        html: "",
        css: "",
        js: ""
      },
      checkpoints: []
    };
  }
  
  return null;
}

/**
 * 从本地存储或全局变量获取真实的测试任务数据
 * @returns {Object|null} TestTask对象或null
 */
export function getRealTaskContext() {
  const taskId = getTaskIdFromUrl();
  
  if (!taskId) return null;
  
  // 尝试从localStorage获取任务数据
  try {
    const storedTask = localStorage.getItem(`task_${taskId}`);
    if (storedTask) {
      return JSON.parse(storedTask);
    }
  } catch (error) {
    console.warn('Failed to parse stored task data:', error);
  }
  
  // 尝试从全局变量获取
  if (window.currentTask && window.currentTask.topic_id === taskId) {
    return window.currentTask;
  }
  
  // 如果都没有，返回null，让后端处理
  return null;
}




