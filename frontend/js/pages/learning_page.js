
// ==================== 导入模块 ====================
// 导入配置模块
import { AppConfig, buildBackendUrl, initializeConfig } from '../modules/config.js';
<<<<<<< HEAD
import {  setupBackButton, getUrlParam, trackReferrer,navigateTo } from '../modules/navigation.js';
=======
import { MiniKnowledgeGraph } from '../modules/mini_knowledge_graph.js';
import { setupHeaderTitle, setupBackButton, getUrlParam, trackReferrer,navigateTo } from '../modules/navigation.js';
// 导入功能模块
import { 
    renderTopicContent,
    setTopicData,
    getTopicData
} from '../modules/docs_module.js';
>>>>>>> 7520342a0e67a9ac683ad0d15203a418a0d9cf10

import {
    createSelectorBridge,
    initIframeSelector,
    handleStartSelector,
    stopSelector,
    initBridge,
    handleCumulativeToggle,
    handleShowSource,
    handleError
} from '../modules/iframe-selector.js';

// 导入行为追踪器
import tracker from '../modules/behavior_tracker.js';

// 导入聊天模块
import chatModule from '../modules/chat.js';

// 导入API客户端
import '../api_client.js';

console.log('learning_page.js 开始加载...');

// ==================== 变量定义 ====================
let bridge = null;
let allowedElements = {
    cumulative: [],
    current: []
};
let currentTopicId = '1_1'; // 默认主题ID
let selectedElementInfo = null; // 保存当前选中的元素信息

// 模块实例
let knowledgeModule = null;

// 统一的初始化状态管理
const AppState = {
    isInitialized: false,
    isDataLoaded: false,
    initPromise: null
};

const miniGraph = new MiniKnowledgeGraph('containerId', {
  height: 200,
  nodeSize: 20,
  chapterNodeSize: 30,
  fontSize: 10
});

// 应用数据存储，用于管理API数据
const AppDataStore = {
    // API数据缓存
    apiData: {
        topicContent: null,      // 主题内容数据
        allowedElements: null,   // 可选元素数据
        userProgress: null       // 用户进度数据
    },
    
    // 设置数据
    setData(key, data) {
        this.apiData[key] = data;
        console.log(`[AppDataStore] 设置数据 ${key}:`, data);
    },
    
    // 获取数据
    getData(key) {
        const data = this.apiData[key];
        console.log(`[AppDataStore] 获取数据 ${key}:`, data);
        return data;
    },
    
    // 检查数据是否已加载
    isDataLoaded(key) {
        return this.apiData[key] !== null;
    },
    
    // 清空数据
    clearData() {
        this.apiData = {
            topicContent: null,
            allowedElements: null,
            userProgress: null
        };
        console.log('[AppDataStore] 数据已清空');
    }
};

// ==================== 全局初始化 ====================
// iframe加载状态管理
let iframeLoadProcessed = false;

// 为行为追踪器设置participant_id（如果不存在则使用默认值）
if (!window.participantId) {
    window.participantId = 'user123'; // 默认用户ID，实际应用中应该从session获取
}

// 确保localStorage中有participant_id，供api_client.js使用
if (!localStorage.getItem('participant_id')) {
    localStorage.setItem('participant_id', 'user123');
}

// ==================== 主应用初始化 ====================
async function initMainApp() {
    // 防止重复初始化的检查
    if (AppState.isInitialized) {
        console.log('主应用已经初始化过，跳过重复初始化');
        return;
    }
    
    // 如果正在初始化，等待完成
    if (AppState.initPromise) {
        console.log('主应用正在初始化中，等待完成');
        return AppState.initPromise;
    }
    
    // 创建初始化Promise
    AppState.initPromise = (async () => {
        try {
            // 标记为已初始化（立即设置，防止重复执行）
            AppState.isInitialized = true;
            
            console.log('开始初始化主应用...');
            
            // 获取必要的DOM元素
            const { startButton, stopButton, iframe } = getRequiredDOMElements();
            if (!startButton || !stopButton || !iframe) {
                throw new Error('必要的DOM元素未找到');
            }
            
            // 初始化按钮状态
            startButton.disabled = true;
            
            // 获取topicId并更新页面标题
            const topicId = getTopicIdFromURL();
            updatePageTitle(topicId);
            
            try {
                // 加载所有数据
                await loadAllData(topicId);
                
                // 初始化各个模块
                await initializeModules(topicId);
                
                // 初始化UI事件
                initializeUIEvents(iframe);
                
                // 启用按钮
                startButton.disabled = false;
                
                console.log('主应用初始化完成');
                
            } catch (error) {
                console.error('数据加载失败，使用默认配置:', error);
                await handleInitializationFailure(topicId);
                startButton.disabled = false;
            }
            
        } catch (error) {
            console.error('主应用初始化失败:', error);
            // 重置初始化状态，允许重试
            AppState.isInitialized = false;
            AppState.initPromise = null;
            throw error;
        }
    })();
    
    return AppState.initPromise;
}

// 获取必要的DOM元素
function getRequiredDOMElements() {
    const startButton = document.getElementById('startSelector');
    const stopButton = document.getElementById('stopSelector');
    const iframe = document.getElementById('element-selector-iframe');
    
    return { startButton, stopButton, iframe };
}

// 从URL获取topicId
function getTopicIdFromURL() {
    const topicId = getUrlParam('topic') || '1_1'; // 使用默认值
    currentTopicId = topicId.id;
    return topicId.id;
}

// 更新页面标题
function updatePageTitle(topicId) {
    const headerTitle = document.querySelector('.header-title');
    if (headerTitle) {
        headerTitle.textContent = `学习 - ${topicId}`;
    }
}

// 加载所有数据
async function loadAllData(topicId) {
    console.log('[MainApp] 开始加载所有数据...');
    console.log('[MainApp] 当前topicId:', topicId);
    
    // 获取学习内容数据
    const topicContent = await fetchTopicContent(topicId);
    
    // 获取用户进度数据
    const userProgress = await fetchUserProgress();
    
    // 解析可选元素数据
    const elementsData = getAllowedElementsFromData(topicContent, topicId);
    
    // 存储所有数据
    AppDataStore.setData('topicContent', topicContent);
    AppDataStore.setData('userProgress', userProgress);
    AppDataStore.setData('allowedElements', elementsData);
    
    // 设置全局变量
    allowedElements = elementsData;
    
    console.log('[MainApp] 数据加载完成:', { 
        topicContent: topicContent.title,
        elementsCount: elementsData.current.length,
        progress: userProgress?.data?.completed_topics?.length || 0
    });
}

// 获取学习内容数据
async function fetchTopicContent(topicId) {
    const apiUrl = buildBackendUrl(`/learning-content/${topicId}`);
    console.log('[MainApp] 学习内容API请求地址:', apiUrl);
    
    const response = await fetch(apiUrl);
    const data = await response.json();
    
    if (data.code !== 200 || !data.data) {
        throw new Error('学习内容API返回数据格式错误');
    }
    
    return data.data;
}

// 获取用户进度数据
async function fetchUserProgress() {
    // 从localStorage或session获取用户ID
    const userId = localStorage.getItem('participant_id') || 'user123';
    const progressUrl = buildBackendUrl(`/progress/participants/${userId}/progress`);
    console.log('[MainApp] 进度API请求地址:', progressUrl);
    
    try {
        const response = await fetch(progressUrl);
        const data = await response.json();
        return data;
    } catch (error) {
        console.warn('[MainApp] 获取用户进度失败:', error);
        return null;
    }
}

// 初始化各个模块
async function initializeModules(topicId) {
    // 初始化知识点模块
    knowledgeModule = new KnowledgeModule();
    console.log('[MainApp] 知识点模块初始化完成');

    // 初始化简化知识图谱
    try {
        const miniGraph = new MiniKnowledgeGraph('miniGraphContainer', {
        height: 200,
        nodeSize: 20,
        chapterNodeSize: 30,
        fontSize: 10
        });
        await miniGraph.init();
        console.log('[MainApp] 简化知识图谱初始化完成');
    } catch (error) {
        console.error('[MainApp] 简化知识图谱初始化失败:', error);
    }
    
    // 初始化聊天模块
    try {
        chatModule.init('learning', topicId);
        console.log('[MainApp] 聊天模块初始化完成');
        
        // 统一处理AI头像显示（立即执行）
        unifyAIAvatars();
        
        // 设置全局AI头像监控器
        setupAIAvatarObserver();
        
        // 再次延迟执行，确保所有元素都已加载
        setTimeout(() => {
            console.log('[MainApp] 延迟执行AI头像统一处理');
            unifyAIAvatars();
        }, 500);
    } catch (error) {
        console.error('[MainApp] 聊天模块初始化失败:', error);
    }
    
    // 更新页面标题为实际内容标题
    const topicContent = AppDataStore.getData('topicContent');
    if (topicContent?.title) {
        const headerTitle = document.querySelector('.header-title');
        if (headerTitle) {
            headerTitle.textContent = topicContent.title;
            console.log('页面标题已更新为:', topicContent.title);
        }
    }
    
    // 渲染知识点内容
    if (topicContent?.levels) {
        // 获取知识点内容容器
        const knowledgeContent = document.getElementById('knowledge-content');
        if (knowledgeContent) {
            // 清空现有内容
            knowledgeContent.innerHTML = '';
            
            // 为每个level创建一个段落元素
            topicContent.levels.forEach(level => {
                const paragraph = document.createElement('p');
                paragraph.textContent = level.description;
                paragraph.className = 'knowledge-point-description';
                knowledgeContent.appendChild(paragraph);
            });
        }
    }
}

// 初始化UI事件
function initializeUIEvents(iframe) {
    // 初始化iframe事件监听（只绑定一次）
    initIframeEvents(iframe);
    
    // 初始化所有事件监听器
    initEventListeners();
    
    // 初始化iframe选择器
    initIframeSelector();
}

// 处理初始化失败的情况
// async function handleInitializationFailure(topicId) {
//     console.log('[MainApp] 使用默认配置进行初始化...');
    
//     // 设置默认元素
//     allowedElements = {
//         cumulative: ['div', 'span', 'p', 'h1', 'h2', 'h3'],
//         current: ['div', 'span', 'p']
//     };
    
//     // 初始化知识点模块
//     knowledgeModule = new KnowledgeModule();
//     console.log('[MainApp] 知识点模块初始化完成（失败后）');
    
    // 初始化聊天模块 - 已注释
    // try {
    //     chatModule.init('learning', topicId);
    //     console.log('[MainApp] 聊天模块初始化完成（失败后）');
    // } catch (error) {
    //     console.error('[MainApp] 聊天模块初始化失败（失败后）:', error);
    // }
// }

// ==================== 功能模块 ====================

/**
 * 统一处理AI头像显示
 * 确保所有AI头像都使用机器人图标而不是文字
 */
function unifyAIAvatars() {
    console.log('[MainApp] 开始统一处理AI和用户头像显示');
    
    // 处理AI头像
    const aiAvatars = document.querySelectorAll('.ai-avatar');
    console.log(`[MainApp] 找到 ${aiAvatars.length} 个AI头像元素`);
    
    let aiReplacedCount = 0;
    aiAvatars.forEach((avatar, index) => {
        // 检查是否已经包含iconify-icon
        const existingIcon = avatar.querySelector('iconify-icon');
        if (existingIcon) {
            console.log(`[MainApp] AI头像 ${index + 1} 已经使用图标，跳过`);
            return;
        }
        
        // 检查是否包含"AI"文字
        if (avatar.textContent.trim() === 'AI') {
            console.log(`[MainApp] 替换AI头像 ${index + 1} 的文字为机器人图标`);
            avatar.innerHTML = '<iconify-icon icon="mdi:robot" width="20" height="20"></iconify-icon>';
            aiReplacedCount++;
        }
    });
    
    // 处理用户头像
    const userAvatars = document.querySelectorAll('.user-avatar');
    console.log(`[MainApp] 找到 ${userAvatars.length} 个用户头像元素`);
    
    let userReplacedCount = 0;
    userAvatars.forEach((avatar, index) => {
        // 检查是否已经包含iconify-icon
        const existingIcon = avatar.querySelector('iconify-icon');
        if (existingIcon) {
            console.log(`[MainApp] 用户头像 ${index + 1} 已经使用图标，跳过`);
            return;
        }
        
        // 检查是否包含"你"文字
        if (avatar.textContent.trim() === '你') {
            console.log(`[MainApp] 替换用户头像 ${index + 1} 的文字为用户图标`);
            avatar.innerHTML = '<iconify-icon icon="mdi:account" width="20" height="20"></iconify-icon>';
            userReplacedCount++;
        }
    });
    
    console.log(`[MainApp] 共替换了 ${aiReplacedCount} 个AI头像和 ${userReplacedCount} 个用户头像`);
    
    // 重写chatModule的addMessageToUI方法以确保新消息也使用图标
    if (chatModule && typeof chatModule.addMessageToUI === 'function') {
        const originalAddMessageToUI = chatModule.addMessageToUI.bind(chatModule);
        
        chatModule.addMessageToUI = function(sender, content) {
            // 调用原始方法
            originalAddMessageToUI(sender, content);
            
            // 处理新生成的头像
            setTimeout(() => {
                if (sender === 'ai') {
                    // 处理AI头像
                    const newAiAvatars = document.querySelectorAll('.ai-avatar');
                    newAiAvatars.forEach(avatar => {
                        if (avatar.textContent.trim() === 'AI' && !avatar.querySelector('iconify-icon')) {
                            console.log('[MainApp] 替换新生成的AI头像为机器人图标');
                            avatar.innerHTML = '<iconify-icon icon="mdi:robot" width="20" height="20"></iconify-icon>';
                        }
                    });
                } else if (sender === 'user') {
                    // 处理用户头像
                    const newUserAvatars = document.querySelectorAll('.user-avatar');
                    newUserAvatars.forEach(avatar => {
                        if (avatar.textContent.trim() === '你' && !avatar.querySelector('iconify-icon')) {
                            console.log('[MainApp] 替换新生成的用户头像为用户图标');
                            avatar.innerHTML = '<iconify-icon icon="mdi:account" width="20" height="20"></iconify-icon>';
                        }
                    });
                }
            }, 0);
        };
        
        console.log('[MainApp] 已重写chatModule.addMessageToUI方法以确保头像一致性');
    } else {
        console.warn('[MainApp] chatModule不可用，无法重写addMessageToUI方法');
    }
    
    console.log('[MainApp] AI和用户头像统一处理完成');
}

/**
 * 全局头像监控器
 * 监控DOM变化，自动处理新添加的AI和用户头像
 */
function setupAIAvatarObserver() {
    console.log('[MainApp] 设置全局头像监控器（AI+用户）');
    
    // 创建MutationObserver来监控DOM变化
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // 检查新添加的节点是否包含AI头像
                        let aiAvatars = node.querySelectorAll ? Array.from(node.querySelectorAll('.ai-avatar')) : [];
                        if (node.classList && node.classList.contains('ai-avatar')) {
                            aiAvatars.push(node);
                        }
                        
                        // 检查新添加的节点是否包含用户头像
                        let userAvatars = node.querySelectorAll ? Array.from(node.querySelectorAll('.user-avatar')) : [];
                        if (node.classList && node.classList.contains('user-avatar')) {
                            userAvatars.push(node);
                        }
                        
                        // 处理AI头像
                        aiAvatars.forEach(avatar => {
                            if (avatar.textContent.trim() === 'AI' && !avatar.querySelector('iconify-icon')) {
                                console.log('[MainApp] 监控器检测到新的AI头像，自动替换为机器人图标');
                                avatar.innerHTML = '<iconify-icon icon="mdi:robot" width="20" height="20"></iconify-icon>';
                            }
                        });
                        
                        // 处理用户头像
                        userAvatars.forEach(avatar => {
                            if (avatar.textContent.trim() === '你' && !avatar.querySelector('iconify-icon')) {
                                console.log('[MainApp] 监控器检测到新的用户头像，自动替换为用户图标');
                                avatar.innerHTML = '<iconify-icon icon="mdi:account" width="20" height="20"></iconify-icon>';
                            }
                        });
                    }
                });
            }
        });
    });
    
    // 开始监控整个文档的子节点变化
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    console.log('[MainApp] 全局头像监控器已启动（AI+用户）');
}

// 知识点管理模块
class KnowledgeModule {
    constructor(options = {}) {
        this.levelCards = [];
        this.knowledgePanel = null;
        this.options = {
            ...options
        };
        
        this.init();
    }
    
    // 初始化知识点模块
    init() {
        console.log('[KnowledgeModule] 开始初始化知识点模块');
        
        // 获取知识点面板和卡片元素
        this.knowledgePanel = document.querySelector('.knowledge-panel');
        this.levelCards = document.querySelectorAll('.level-card');
        
        console.log('[KnowledgeModule] 找到知识点面板:', this.knowledgePanel);
        console.log('[KnowledgeModule] 找到卡片数量:', this.levelCards.length);
        
        if (!this.knowledgePanel) {
            console.error('[KnowledgeModule] 知识点面板元素未找到');
            return;
        }
        
        if (this.levelCards.length === 0) {
            console.warn('[KnowledgeModule] 未找到知识点卡片');
            return;
        }
        
        // 直接显示所有卡片内容，不需要交互
        this.showAllCardContents();
        
        console.log('[KnowledgeModule] 知识点模块初始化完成');
    }
    
    // 显示所有卡片的内容
    showAllCardContents() {
        console.log('[KnowledgeModule] 直接显示所有卡片内容');
        
<<<<<<< HEAD
        this.levelCards.forEach((card, index) => {
            console.log(`[KnowledgeModule] 为卡片 ${index + 1} (level ${card.dataset.level}) 绑定点击事件`);
            
            card.addEventListener('click', (event) => {
                console.log(`[KnowledgeModule] 卡片 ${index + 1} 被点击了！`);
                event.preventDefault();
                event.stopPropagation();
                this.handleCardClick(card);
            });
        });
        
        console.log('[KnowledgeModule] 事件绑定完成');
    }
    
    // 绑定键盘事件
    bindKeyboardEvents() {
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                const isExpanded = this.knowledgePanel.classList.contains('expanded');
                if (isExpanded) {
                    console.log('[KnowledgeModule] 检测到ESC键，退出展开模式');
                    // 收起所有卡片
                    this.levelCards.forEach(card => {
                        card.classList.remove('expanded');
                        card.classList.add('collapsed');
                    });
                    // 收起知识点面板
                    this.knowledgePanel.classList.remove('expanded');
                }
            }
        });
    }
    
}

// ==================== 事件处理函数 ====================

// iframe事件初始化
function initIframeEvents(iframe) {
    // 只绑定一次
    if (iframe.hasAttribute('data-load-event-bound')) {
        return;
    }
    
    iframe.setAttribute('data-load-event-bound', 'true');
    
    iframe.addEventListener('load', function () {
        // 防止重复处理iframe加载事件
        if (iframeLoadProcessed) {
            console.log('iframe加载事件已处理过，跳过重复处理');
            return;
        }
        
        // 标记为已处理（立即设置，防止重复执行）
        iframeLoadProcessed = true;
        
        console.log('预览框架已加载:', iframe.src);
        showStatus('info', '预览页面已加载，选择器已就绪');
        
        // 初始化桥接
        setTimeout(() => {
            bridge = initBridge(createSelectorBridge, 
                createElementSelectedWithTracking(), 
                (error) => handleError(error, showStatus, () => stopSelector(bridge))
            );
            // 初始化行为追踪器
            initBehaviorTracker();
        }, 100);
    });
    
    // 检查iframe是否已经加载完成
    if (iframe.contentDocument && iframe.contentDocument.readyState === 'complete') {
        iframeLoadProcessed = true;
        setTimeout(() => {
            bridge = initBridge(createSelectorBridge, 
                createElementSelectedWithTracking(), 
                (error) => handleError(error, showStatus, () => stopSelector(bridge))
            );
            // 初始化行为追踪器
            initBehaviorTracker();
        }, 100);
    }
}

// 事件监听器初始化
function initEventListeners() {
    const startButton = document.getElementById('startSelector');
    const stopButton = document.getElementById('stopSelector');
    const cumulativeToggle = document.getElementById('cumulativeToggle');
    const showSourceBtn = document.getElementById('showSourceBtn');
    const tabKnowledge = document.getElementById('tab-knowledge');
    const tabCode = document.getElementById('tab-code');
    const knowledgeContent = document.getElementById('knowledge-content');
    const codeContent = document.getElementById('code-content');
    const askAIButton = document.getElementById('askAIButton');
    const clearSelectionButton = document.getElementById('clearSelectionButton');

    // 初始化按钮状态：确保询问AI按钮默认隐藏
    if (askAIButton) {
        askAIButton.style.display = 'none';
        askAIButton.style.visibility = 'hidden';
        askAIButton.classList.remove('show');
        console.log('初始化：询问AI按钮已隐藏');
    }

    // 启动选择器
    if (startButton) {
        startButton.addEventListener('click', () => {
            handleStartSelector(allowedElements, bridge, showStatus);
            // 切换按钮状态
            if (startButton && stopButton) {
                startButton.style.display = 'none';
                stopButton.style.display = 'flex';
            }
        });
    }

    // 停止选择器
    if (stopButton) {
        stopButton.addEventListener('click', () => {
            stopSelector(bridge);
            // 切换按钮状态
            if (startButton && stopButton) {
                startButton.style.display = 'flex';
                stopButton.style.display = 'none';
            }
            // 注意：不隐藏AI询问按钮，让它保持显示状态
            // AI按钮的显示状态基于是否有选中的元素（selectedElementInfo），而不是选择器状态
            // 只有点击“清除选择”按钮时才会隐藏AI按钮
        });
    }
    
    // AI询问按钮
    if (askAIButton) {
        askAIButton.addEventListener('click', () => {
            askAIAboutElement();
        });
    }
    
    // 清除选择按钮
    if (clearSelectionButton) {
        clearSelectionButton.addEventListener('click', () => {
            // 清除选中的元素信息
            selectedElementInfo = null;
            
            // 隐藏AI询问按钮（重置为默认隐藏状态）
            if (askAIButton) {
                askAIButton.classList.remove('show');
                askAIButton.style.display = 'none';
                askAIButton.style.visibility = 'hidden';
                console.log('清除选择：询问AI按钮已隐藏');
            }
            
            // 隐藏清除选择按钮
            clearSelectionButton.style.display = 'none';
            clearSelectionButton.style.visibility = 'hidden';
            
            // 清空代码面板
            const codeContent = document.getElementById('code-content');
            if (codeContent) {
                codeContent.innerHTML = '<h2>选中元素代码</h2><pre id="selectedElementCode"></pre>';
            }
        });
    }
    
    // 初始化开关事件监听器
    if (cumulativeToggle) {
        cumulativeToggle.addEventListener('change', () => handleCumulativeToggle(allowedElements, showStatus, bridge));
        
        // 设置开关的初始状态信息显示
        const isInitiallyChecked = cumulativeToggle.checked;
        console.log('[MainApp] 开关初始状态:', isInitiallyChecked);
    }

    // Tab切换
    if (tabKnowledge && tabCode) {
        tabKnowledge.addEventListener('click', () => {
            if (knowledgeContent) knowledgeContent.style.display = '';
            if (codeContent) codeContent.style.display = 'none';
            tabKnowledge.classList.add('active');
            tabCode.classList.remove('active');
        });

        tabCode.addEventListener('click', () => {
            if (knowledgeContent) knowledgeContent.style.display = 'none';
            if (codeContent) codeContent.style.display = '';
            tabCode.classList.add('active');
            tabKnowledge.classList.remove('active');
        });
    }

    // 返回源代码按钮
    if (showSourceBtn) {
        showSourceBtn.addEventListener('click', handleShowSource);
    }

    // 开始测试按钮
    const startTestButton = document.getElementById('start-test-button');
    if (startTestButton) {
        startTestButton.addEventListener('click', () => {
            // 获取当前主题ID
            const topicId = getTopicIdFromURL();
            // 跳转到测试页面并传递topicId参数
            const testPageUrl = `../pages/test_page.html?topic=${topicId}`;
            console.log('[MainApp] 跳转到测试页面:', testPageUrl);
            navigateTo('/pages/test_page.html', topicId, true, true);
        });
    }
}

// 行为追踪器初始化
function initBehaviorTracker() {
    try {
        console.log('[MainApp] 开始初始化行为追踪器...');
        
        // 初始化元素选择器行为追踪
        tracker.initDOMSelector('startSelector', 'stopSelector', 'element-selector-iframe');
        
        // 初始化AI聊天行为追踪
        tracker.initChat('send-message', '#user-message', 'learning', currentTopicId);
        
        // 初始化闲置和焦点检测
        tracker.initIdleAndFocus();
        
        console.log('[MainApp] 行为追踪器初始化完成');
    } catch (error) {
        console.error('[MainApp] 行为追踪器初始化失败:', error);
    }
}

// 创建带行为追踪的元素选择处理函数
function createElementSelectedWithTracking() {
    return function(elementInfo, showStatus) {
        console.log('元素选择处理函数被调用，选中的元素信息:', elementInfo);
        
        // 保存选中的元素信息
        selectedElementInfo = elementInfo;
        console.log('[DEBUG] selectedElementInfo 已更新为:', selectedElementInfo);
        
        // 自动切换按钮状态
        const startButton = document.getElementById('startSelector');
        const stopButton = document.getElementById('stopSelector');
        const askAIButton = document.getElementById('askAIButton');
        const clearSelectionButton = document.getElementById('clearSelectionButton');
        
        console.log('获取到的按钮元素:', {startButton, stopButton, askAIButton, clearSelectionButton});
        
        if (startButton && stopButton) {
            startButton.style.display = 'flex';
            stopButton.style.display = 'none';
        }
        
        // 显示AI询问按钮（只有在选中元素后才显示）
        if (askAIButton) {
            console.log('元素已选中，准备显示AI询问按钮');
            askAIButton.classList.add('show');
            // 强制设置样式
            askAIButton.style.display = 'flex';
            askAIButton.style.opacity = '1';
            askAIButton.style.transform = 'translateY(0)';
            // 确保按钮可见
            askAIButton.style.visibility = 'visible';
            console.log('AI询问按钮显示完成，当前类名:', askAIButton.className);
        }
        
        // 显示清除选择按钮
        if (clearSelectionButton) {
            console.log('显示清除选择按钮');
            clearSelectionButton.style.display = 'flex';
            // 确保按钮可见
            clearSelectionButton.style.visibility = 'visible';
        }
        
        // 获取选中元素的源代码并显示到代码面板
        displaySelectedElementCode(elementInfo);
        
        // 自动切换到代码标签页
        switchToCodeTab();
        
        // 记录到行为追踪器
        try {
            tracker.logEvent('dom_element_select', {
                tagName: elementInfo.tagName,
                selector: elementInfo.selector,
                id: elementInfo.id,
                className: elementInfo.className,
                position: elementInfo.bounds,
                topicId: currentTopicId
            });
        } catch (error) {
            console.warn('[MainApp] 行为追踪记录失败:', error);
        }
    };
}

// ==================== 数据处理函数 ====================

// 从API数据中提取可选元素
function getAllowedElementsFromData(data, topicId) {
    console.log(`[MainApp] 开始解析数据，目标章节: ${topicId}`);
    console.log(`[MainApp] 数据中是否包含 sc_all:`, !!data.sc_all);
    console.log(`[MainApp] 数据中是否包含 allowedElements:`, !!data.allowedElements);
    
    if (data.sc_all && Array.isArray(data.sc_all)) {
        console.log(`[MainApp] 找到 sc_all 数组，长度: ${data.sc_all.length}`);
        console.log(`[MainApp] sc_all 内容:`, data.sc_all);
        
        const cumulativeElements = getCumulativeAllowedElements(data.sc_all, topicId);
        const currentElements = getCurrentChapterElements(data.sc_all, topicId);
        
        console.log(`[MainApp] 累积元素:`, cumulativeElements);
        console.log(`[MainApp] 当前章节元素:`, currentElements);
        
        return {
            cumulative: cumulativeElements,
            current: currentElements
        };
    }
    
    // 如果直接包含 allowedElements
    if (data.allowedElements) {
        console.log(`[MainApp] 使用直接包含的 allowedElements:`, data.allowedElements);
        return {
            cumulative: data.allowedElements,
            current: data.allowedElements
        };
    }
    
    console.warn(`[MainApp] 未找到有效的元素数据，返回空数组`);
    return {
        cumulative: [],
        current: []
    };
}

// 获取累积的可选元素
function getCumulativeAllowedElements(scAll, targetTopicId) {
    const allowedElements = new Set();
    
    // 遍历所有章节
    for (const chapter of scAll) {
        const chapterTopicId = chapter.topic_id;
        const selectElements = chapter.select_element || [];
        
        // 将当前章节的可选元素添加到集合中
        selectElements.forEach(element => allowedElements.add(element));
        
        // 如果找到目标章节，停止累加
        if (chapterTopicId === targetTopicId) {
            break;
        }
    }
    
    return Array.from(allowedElements);
}

// 获取当前章节的元素
function getCurrentChapterElements(scAll, targetTopicId) {
    // 找到当前章节
    const currentChapter = scAll.find(chapter => chapter.topic_id === targetTopicId);
    
    if (currentChapter && currentChapter.select_element) {
        return currentChapter.select_element;
    }
    
    return [];
}

// 显示选中元素的源代码
function displaySelectedElementCode(elementInfo) {
    const codeContent = document.getElementById('code-content');
    
    if (!codeContent) {
        console.warn('无法获取代码面板');
        return;
    }
    
    try {
        // 直接使用elementInfo中的outerHTML，这是从iframe中获取的真实HTML代码
        let elementHTML = elementInfo.outerHTML || '';
        
        // 如果没有outerHTML，尝试使用其他方式
        if (!elementHTML) {
            // 构建基本的HTML结构
            elementHTML = `<${elementInfo.tagName}`;
            
            // 添加ID
            if (elementInfo.id) {
                elementHTML += ` id="${elementInfo.id}"`;
            }
            
            // 添加类名
            if (elementInfo.className) {
                elementHTML += ` class="${elementInfo.className}"`;
            }
            
            // 添加文本内容
            if (elementInfo.textContent) {
                elementHTML += `>${elementInfo.textContent}</${elementInfo.tagName}>`;
            } else {
                elementHTML += `></${elementInfo.tagName}>`;
            }
        }
        
        // 格式化HTML代码
        const formattedHTML = formatHTML(elementHTML);
        
        // 显示到代码面板
        codeContent.innerHTML = `
            <div class="code-header">
                <h4>选中的元素代码</h4>
                <div class="element-info">
                    <span class="tag-name" title="<${elementInfo.tagName}>">&lt;${elementInfo.tagName}&gt;</span>
                    ${elementInfo.id ? `<span class="element-id" title="ID: ${elementInfo.id}">#${elementInfo.id}</span>` : ''}
                    ${elementInfo.className ? generateClassSpans(elementInfo.className) : ''}
                </div>
            </div>
            <pre class="code-block"><code class="language-html">${formattedHTML}</code></pre>
        `;
        
        console.log('元素代码已显示到代码面板:', formattedHTML);
        
    } catch (error) {
        console.error('显示元素代码时出错:', error);
        codeContent.innerHTML = `
            <div class="code-header">
                <h4>错误</h4>
            </div>
            <pre class="code-block"><code class="language-text">无法获取元素代码: ${error.message}</code></pre>
        `;
    }
}

// 生成class标签的HTML
function generateClassSpans(className) {
    if (!className) return '';
    
    // 将class字符串分割为数组，过滤空值
    const classes = className.split(' ').filter(cls => cls.trim());
    
    // 最多显示3个class，防止界面过于拥挤
    const maxClasses = 3;
    const displayClasses = classes.slice(0, maxClasses);
    
    let result = displayClasses.map(cls => 
        `<span class="element-class" title="Class: ${cls}">.${cls}</span>`
    ).join('');
    
    // 如果还有更多的class，显示省略号
    if (classes.length > maxClasses) {
        const remainingCount = classes.length - maxClasses;
        result += `<span class="element-class element-class-more" title="还有 ${remainingCount} 个类名: ${classes.slice(maxClasses).join(', ')}">+${remainingCount}</span>`;
    }
    
    return result;
}

// 切换到代码标签页
function switchToCodeTab() {
    const tabKnowledge = document.getElementById('tab-knowledge');
    const tabCode = document.getElementById('tab-code');
    const knowledgeContent = document.getElementById('knowledge-content');
    const codeContent = document.getElementById('code-content');
    
    if (tabKnowledge && tabCode && knowledgeContent && codeContent) {
        // 隐藏知识点内容，显示代码内容
        knowledgeContent.style.display = 'none';
        codeContent.style.display = '';
        
        // 更新标签页状态
        tabKnowledge.classList.remove('active');
        tabCode.classList.add('active');
        
        console.log('已自动切换到代码标签页');
    }
}

// 格式化HTML代码
function formatHTML(html) {
    if (!html) return '';
    
    // 转义HTML特殊字符，防止XSS
    const escapeHtml = (text) => {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };
    
    // 简单的HTML格式化
    let formatted = html
        .replace(/></g, '>\n<')  // 在标签之间添加换行
        .replace(/\n\s*\n/g, '\n')  // 移除多余的空行
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .join('\n');
    
    // 转义HTML内容
    return escapeHtml(formatted);
}

// ==================== 调试工具函数 ====================

// 显示当前保存的元素信息（调试用）
window.showElementInfo = function() {
    console.log('==== 当前保存的元素信息 ====');
    console.log('selectedElementInfo:', selectedElementInfo);
    console.log('window.pendingElementContext:', window.pendingElementContext);
    
    if (selectedElementInfo) {
        console.log('\n=== 详细元素信息 ===');
        console.log('标签名 (tagName):', selectedElementInfo.tagName);
        console.log('元素ID (id):', selectedElementInfo.id || '(无)');
        console.log('类名 (className):', selectedElementInfo.className || '(无)');
        console.log('类列表 (classList):', selectedElementInfo.classList || '(无)');
        console.log('文本内容 (textContent):', selectedElementInfo.textContent || '(无)');
        console.log('外部HTML (outerHTML):', selectedElementInfo.outerHTML || '(无)');
        console.log('选择器 (selector):', selectedElementInfo.selector || '(无)');
        console.log('位置信息 (bounds):', selectedElementInfo.bounds || '(无)');
        console.log('样式信息 (styles):', selectedElementInfo.styles || '(无)');
        console.log('页面URL (pageURL):', selectedElementInfo.pageURL || '(无)');
        
        // 如果有更多字段，也显示出来
        const knownFields = ['tagName', 'id', 'className', 'classList', 'textContent', 'outerHTML', 'selector', 'bounds', 'styles', 'pageURL'];
        const additionalFields = Object.keys(selectedElementInfo).filter(key => !knownFields.includes(key));
        if (additionalFields.length > 0) {
            console.log('\n=== 其他字段 ===');
            additionalFields.forEach(field => {
                console.log(`${field}:`, selectedElementInfo[field]);
            });
        }
    } else {
        console.log('当前没有选中任何元素');
    }
    
    console.log('========================');
};

// ==================== 工具函数 ====================

// 显示状态信息
function showStatus(type, message) {
    // 不再显示任何状态信息
    return;
}

// 询问AI关于选中元素的功能
function askAIAboutElement() {
    if (!selectedElementInfo) {
        console.warn('请先选择一个元素');
        return;
    }
    
    console.log('[DEBUG] askAIAboutElement 被调用，当前 selectedElementInfo:', selectedElementInfo);
    
    // 构建包含元素详细信息的上下文
    const elementDetails = [
        `关于我选中的 <${selectedElementInfo.tagName.toLowerCase()}> 元素：`,
        selectedElementInfo.id ? `- ID: #${selectedElementInfo.id}` : null,
        selectedElementInfo.className ? `- 类名: ${selectedElementInfo.className}` : null,
        selectedElementInfo.textContent ? `- 文本内容: "${selectedElementInfo.textContent.substring(0, 100)}${selectedElementInfo.textContent.length > 100 ? '...' : ''}"` : null,
        selectedElementInfo.outerHTML ? `- HTML代码:\n\`\`\`html\n${selectedElementInfo.outerHTML}\n\`\`\`` : null
    ].filter(Boolean).join('\n');
    
    // 构建AI主动询问的消息（使用Markdown格式以便正确渲染）
    const tagNameDisplay = `\`<${selectedElementInfo.tagName.toLowerCase()}>\``;
    const aiInitialMessage = `我看到您选中了一个 ${tagNameDisplay} 元素${selectedElementInfo.id ? ` (ID: \`#${selectedElementInfo.id}\`)` : ''}。

**您想要了解这个HTML元素的功能和用法吗？** 我可以为您详细介绍它的作用、属性和使用场景。

💡 *提示：请在下方输入您想了解的内容，例如"这个元素有什么作用？"或"如何使用这个元素？"*`;
    
    console.log('构建的AI消息:', aiInitialMessage);
    
    // 将格式化后的元素信息保存为待发送的用户消息
    window.pendingElementContext = {
        message: elementDetails,
        originalElementInfo: {
            tagName: selectedElementInfo.tagName,
            id: selectedElementInfo.id,
            className: selectedElementInfo.className,
            outerHTML: selectedElementInfo.outerHTML,
            textContent: selectedElementInfo.textContent
        }
    };
    
    console.log('[DEBUG] window.pendingElementContext 已设置为:', window.pendingElementContext);
    
    // 发送消息到AI
    if (chatModule) {
        // 切换到AI聊天标签页（如果存在）
        const tabChat = document.getElementById('tab-chat');
        if (tabChat) {
            tabChat.click();
        }
        
        // AI主动发送询问消息
        chatModule.addMessageToUI('ai', aiInitialMessage);
    } else {
        console.error('AI聊天模块未初始化');
    }
}

// ==================== 自动初始化 ====================
// 页面加载完成后自动初始化主应用
document.addEventListener('DOMContentLoaded', async () => {

        const sidebarSection = document.getElementById('sidebarSection');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const navMenu = document.getElementById('navMenu');
    // 获取用户ID并验证
    const participantId = getParticipantId();
    if (!participantId) {
      window.location.href = '/pages/index.html';
      return;
    }
// 切换侧边栏状态
            if (sidebarToggle) {
                sidebarToggle.addEventListener('click', function() {
                    if (sidebarSection) {
                        sidebarSection.classList.toggle('expanded');
                        
                        // 更新触发按钮图标
                        const icon = sidebarToggle.querySelector('iconify-icon');
                        if (sidebarSection.classList.contains('expanded')) {
                            icon.setAttribute('icon', 'mdi:chevron-left');
                        } else {
                            icon.setAttribute('icon', 'mdi:chevron-right');
                        }
                    }
                });
            }

    // 处理导航菜单点击
            if (navMenu) {
                navMenu.addEventListener('click', function(e) {
                    const link = e.target.closest('.nav-link');
                    if (!link) return;
                    
                    // 阻止默认行为
                    e.preventDefault();
                    
                    const parentItem = link.parentElement;
                    
                    // 如果是有子菜单的项，切换子菜单
                    if (parentItem.classList.contains('has-children')) {
                        e.stopPropagation();
                        parentItem.classList.toggle('open');
                        
                        const submenu = parentItem.querySelector('.nav-submenu');
                        if (submenu) {
                            submenu.classList.toggle('open');
                        }
                        
                        // 关闭其他展开的子菜单
                        const allOpenItems = navMenu.querySelectorAll('.nav-item.has-children.open');
                        allOpenItems.forEach(item => {
                            if (item !== parentItem) {
                                item.classList.remove('open');
                                const otherSubmenu = item.querySelector('.nav-submenu');
                                if (otherSubmenu) {
                                    otherSubmenu.classList.remove('open');
                                }
                            }
                        });
                    } 
                    // 如果是叶子节点，跳转到对应知识点
                    else if (link.dataset.topic) {
                        const topicId = link.dataset.topic;
                        
                        // 移除所有active类
                        const activeLinks = navMenu.querySelectorAll('.nav-link.active');
                        activeLinks.forEach(activeLink => {
                            activeLink.classList.remove('active');
                        });
                        
                        // 添加active类到当前链接
                        link.classList.add('active');
                        
                        // 跳转到测试页面并传递topicId参数
                        const testPageUrl = `../pages/learning_page.html?topic=${topicId}`;
                        console.log('[MainApp] 跳转到学习页面:', testPageUrl);
                        navigateTo('/pages/learning_page.html', topicId);
                    }
                });
            }
    try {
        trackReferrer();
        // 设置标题点击跳转到知识图谱页面
        setupHeaderTitle('/pages/knowledge_graph.html');
        // 设置返回按钮（固定返回知识图谱）
        setupBackButton();
        // 先初始化配置
        console.log('[MainApp] 开始初始化配置...');
        await initializeConfig();
        console.log('[MainApp] 配置初始化完成:', AppConfig);
        
        // 然后初始化主应用
        initMainApp();
        
        // 扩展聊天模块以支持元素上下文
        extendChatModuleForElementContext();
    } catch (error) {
        console.error('[MainApp] 配置初始化失败:', error);
        // 即使配置失败，也尝试初始化主应用
        initMainApp();
        extendChatModuleForElementContext();
    }
});

// 扩展聊天模块以支持元素上下文
function extendChatModuleForElementContext() {
    if (!chatModule) return;
    
    // 保存原始的sendMessage方法
    const originalSendMessage = chatModule.sendMessage.bind(chatModule);
    
    // 重写sendMessage方法
    chatModule.sendMessage = async function(mode, contentId) {
        const message = this.inputElement.value.trim();
        if (!message || this.isLoading) return;
        
        // 清空输入框
        this.inputElement.value = '';
        
        // 添加用户消息到UI
        this.addMessageToUI('user', message);
        
        // 设置加载状态
        this.setLoadingState(true);
        
        try {
            // 构建请求体
            let finalUserMessage = message;
            
            // 如果存在待处理的元素上下文，将元素信息和用户消息结合
            if (window.pendingElementContext && window.pendingElementContext.message) {
                console.log('[DEBUG] 检测到待处理的元素上下文，将结合用户消息和元素信息');
                console.log('用户消息:', message);
                console.log('元素上下文信息:', window.pendingElementContext.message);
                
                // 将用户消息和元素信息结合起来
                finalUserMessage = `${window.pendingElementContext.message}

用户问题: ${message}`;
                
                // 用户回应后清除上下文（避免后续消息继续携带）
                window.pendingElementContext = null;
                console.log('[DEBUG] window.pendingElementContext 已清除');
            }
            
            const requestBody = {
                user_message: finalUserMessage,
                conversation_history: this.getConversationHistory(),
                code_context: this.getCodeContext(),
                mode: mode,
                content_id: contentId
            };
            
            console.log('[DEBUG] 最终请求体:', JSON.stringify(requestBody, null, 2));
            
            // 如果是测试模式，添加测试结果
            if (mode === 'test') {
                const testResults = this._getTestResults();
                if (testResults) {
                    requestBody.test_results = testResults;
                }
            }
            
            // 使用封装的 apiClient 发送请求
            const data = await window.apiClient.post('/chat/ai/chat', requestBody);
            
            if (data.code === 200 && data.data && typeof data.data.ai_response === 'string') {
                // 添加AI回复到UI
                this.addMessageToUI('ai', data.data.ai_response);
            } else {
                throw new Error(data.message || 'AI回复内容为空或格式不正确');
            }
        } catch (error) {
            console.error('[ChatModule] 发送消息时出错:', error);
            this.addMessageToUI('ai', `抱歉，我无法回答你的问题。错误信息: ${error.message}`);
        } finally {
            // 取消加载状态
            this.setLoadingState(false);
        }
    };
    
    console.log('[Learning] 聊天模块已扩展以支持元素上下文');
} 