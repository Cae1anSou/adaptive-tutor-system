// ==================== 文档模块 ====================
// 统一的模块状态管理
const ModuleState = {
    currentTopicData: null,  // 存储当前主题的完整数据
    isInitialized: false,    // 防重复初始化标志
    initPromise: null        // 初始化Promise，防止重复调用
};

// 渲染主题内容
function renderTopicContent() {
    console.log('[DocsModule] 开始渲染主题内容');
    
    const knowledgeContent = document.getElementById('knowledge-content');
    if (!knowledgeContent) {
        console.warn('[DocsModule] knowledge-content 元素不存在');
        return;
    }
    
    // 如果没有主题数据，不清空现有内容
    if (!ModuleState.currentTopicData) {
        console.log('[DocsModule] 没有主题数据，保持现有内容');
        return;
    }
    
    const topicData = ModuleState.currentTopicData;
    const levels = topicData.levels || [];
    
    console.log('[DocsModule] 主题数据:', topicData);
    console.log('[DocsModule] 等级数据:', levels);
    
    // 如果没有等级数据，不清空现有内容
    if (levels.length === 0) {
        console.log('[DocsModule] 没有等级数据，保持现有内容');
        return;
    }
    
    // 更新现有卡片的内容文本
    levels.forEach((level, index) => {
        console.log(`[DocsModule] 更新等级 ${level.level} 的内容:`, level.description);
        
        const card = knowledgeContent.querySelector(`.level-card[data-level="${level.level}"]`);
        if (card) {
            const contentText = card.querySelector('.content-text');
            if (contentText) {
                contentText.textContent = level.description || '暂无内容';
                console.log(`[DocsModule] 等级 ${level.level} 内容更新成功`);
            } else {
                console.warn(`[DocsModule] 等级 ${level.level} 的 content-text 元素未找到`);
            }
        } else {
            console.warn(`[DocsModule] 等级 ${level.level} 的卡片元素未找到`);
        }
    });
    
    // 更新页面标题
    const headerTitle = document.querySelector('.header-title');
    if (headerTitle && topicData.title) {
        headerTitle.textContent = topicData.title;
        console.log('[DocsModule] 页面标题已更新:', topicData.title);
    }
    
    // 注意：事件绑定由主应用负责，这里不重复绑定
    // 避免与learning_page.js中的事件绑定冲突
    console.log('[DocsModule] 主题内容渲染完成，事件绑定由主应用处理');
}



// 设置主题数据
function setTopicData(topicData) {
    ModuleState.currentTopicData = topicData;
    console.log('[DocsModule] 主题数据已设置:', topicData);
}

// 获取主题数据
function getTopicData() {
    return ModuleState.currentTopicData;
}

// 重置模块状态（用于重新初始化）
function resetModuleState() {
    ModuleState.currentTopicData = null;
    ModuleState.isInitialized = false;
    ModuleState.initPromise = null;
    console.log('[DocsModule] 模块状态已重置');
}

// 导出模块
export {
    renderTopicContent,
    setTopicData,
    getTopicData,
    resetModuleState,
    ModuleState
};

// 同时保持向后兼容的window对象
window.DocsModule = {
    renderTopicContent,
    setTopicData,
    getTopicData,
    resetModuleState,
    ModuleState
}; 