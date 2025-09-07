
// ==================== 导入模块 ====================
// 导入配置模块
import { AppConfig, buildBackendUrl, initializeConfig } from '../modules/config.js';
import { MiniKnowledgeGraph } from '../modules/mini_knowledge_graph.js';
import { setupHeaderTitle, setupBackButton, getUrlParam, trackReferrer, navigateTo } from '../modules/navigation.js';

// 导入知识图谱相关模块
import { GraphState } from '../modules/graph_data.js';
import { GraphRenderer } from '../modules/graph_renderer.js';
import { getParticipantId } from '../modules/session.js';

// 导入功能模块
import {
    renderTopicContent,
    setTopicData,
    getTopicData
} from '../modules/docs_module.js';

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
tracker.init({
    user_idle: true,
    page_click: true,
});

// 导入聊天模块
import chatModule from '../modules/chat.js';

// 导入API客户端
import '../api_client.js';

//导入websocket模块
import websocket from '../modules/websocket_client.js';

console.log('learning_page.js 开始加载...');

// ==================== 变量定义 ====================
let bridge = null;
let allowedElements = {
    cumulative: [],
    current: []
};
let currentTopicId = '1_1'; // 默认主题ID
let selectedElementInfo = null; // 保存当前选中的元素信息

// 知识图谱相关变量
let graphState = null;
let graphRenderer = null;
let knowledgeGraphInitialized = false;

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
    window.participantId = 'user123'; // 默认实验编号，实际应用中应该从session获取
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
                //await handleInitializationFailure(topicId);
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
    const topicData = getUrlParam('topic');
    const topicId = (topicData && topicData.id) ? topicData.id : '1_1'; // 使用默认值
    currentTopicId = topicId;
    return topicId;
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
    // 从localStorage或session获取实验编号
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

    // 初始化简化知识图谱 - 启用完整交互功能
    try {
        const miniGraph = new MiniKnowledgeGraph('miniGraphContainer', {
            height: 200,
            nodeSize: 20,
            chapterNodeSize: 30,
            fontSize: 10,
            enableInteractions: true,  // 启用完整交互
            enableModal: true          // 启用模态框
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

    //初始化websocket模块
    try {
        websocket.connect();
        console.log('[MainApp] WebSocket模块初始化完成');
    }
    catch (error) {
        console.error('[MainApp] WebSocket模块初始化失败:', error);
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
        setTopicData(topicContent);
        renderTopicContent();
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

        chatModule.addMessageToUI = function (sender, content) {
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
        this.activeLevel = null;
        this.levelEnterTime = null;
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

        // 绑定事件监听器
        this.bindEvents();

        // 绑定键盘事件
        this.bindKeyboardEvents();

        console.log('[KnowledgeModule] 知识点模块初始化完成');
    }

    // 绑定事件监听器
    bindEvents() {
        console.log('[KnowledgeModule] 开始绑定事件，找到卡片数量:', this.levelCards.length);

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

    // 处理卡片点击事件
    handleCardClick(clickedCard) {
        const level = parseInt(clickedCard.dataset.level, 10);
        const isExpanded = this.knowledgePanel.classList.contains('expanded');

        if (!isExpanded) {
            // Entering a new level
            if (this.activeLevel !== null && this.activeLevel !== level) {
                this.logLevelLeaveEvent(this.activeLevel);
            }
            this.logLevelEnterEvent(level);
            this.activeLevel = level;
            this.levelEnterTime = Date.now();

            this.levelCards.forEach(card => {
                card.classList.remove('expanded');
                card.classList.add('collapsed');
            });
            clickedCard.classList.remove('collapsed');
            clickedCard.classList.add('expanded');
            this.knowledgePanel.classList.add('expanded');
        } else {
            // Leaving the current level
            if (this.activeLevel !== null) {
                this.logLevelLeaveEvent(this.activeLevel);
                this.activeLevel = null;
                this.levelEnterTime = null;
            }

            this.levelCards.forEach(card => {
                card.classList.remove('expanded');
                card.classList.add('collapsed');
            });
            this.knowledgePanel.classList.remove('expanded');
        }
    }

    // 展开指定等级的卡片
    expandLevel(level) {
        const targetCard = document.querySelector(`.level-card[data-level="${level}"]`);
        if (targetCard) {
            this.handleCardClick(targetCard);
        }
    }

    // 收起所有卡片
    collapseAll() {
        this.levelCards.forEach(card => {
            card.classList.remove('expanded');
            card.classList.add('collapsed');
        });

        if (this.knowledgePanel) {
            this.knowledgePanel.classList.remove('expanded');
        }
    }

    logLevelEnterEvent(level) {
        tracker.logEvent('knowledge_level_access', {
            topic_id: currentTopicId,
            level: level,
            action: 'enter'
        });
    }

    logLevelLeaveEvent(level) {
        const duration = Date.now() - this.levelEnterTime;
        tracker.logEvent('knowledge_level_access', {
            topic_id: currentTopicId,
            level: level,
            action: 'leave',
            duration_ms: duration
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

    // 添加知识图谱展开/收起功能
    const miniGraphToggle = document.getElementById('miniGraphToggle');
    const miniKnowledgeGraph = document.getElementById('miniKnowledgeGraph');
    const toggleIcon = document.getElementById('toggleIcon');

    if (miniGraphToggle && miniKnowledgeGraph && toggleIcon) {
        // 确保图标默认有颜色和可见性
        toggleIcon.style.color = '#4f46e5';
        toggleIcon.style.opacity = '0.8';

        // 获取知识图谱容器元素
        const knowledgeGraphContainer = document.getElementById('knowledge-graph-container');
        const closeGraphButton = document.getElementById('closeGraph');

        miniGraphToggle.addEventListener('click', async () => {
            // 只控制知识图谱容器的显示/隐藏，不改变头部标题栏中简化知识图谱预览的大小
            const isExpanding = knowledgeGraphContainer.style.display === 'none' || knowledgeGraphContainer.style.display === '';

            // 控制知识图谱容器的显示/隐藏
            if (isExpanding) {
                // 显示知识图谱容器并初始化渲染知识图谱
                await showKnowledgeGraph();
            } else {
                // 隐藏知识图谱容器
                if (knowledgeGraphContainer) {
                    knowledgeGraphContainer.style.display = 'none';
                }
            }

            // 更改图标
            if (isExpanding) {
                // 展开时，将图标更改为向上箭头
                toggleIcon.setAttribute('icon', 'mdi:chevron-up');
                toggleIcon.style.color = '#3730a3'; // 更深的紫色
                toggleIcon.style.opacity = '1';     // 完全不透明
            } else {
                // 收起时，将图标更改为向下箭头
                toggleIcon.setAttribute('icon', 'mdi:chevron-down');
                toggleIcon.style.color = '#4f46e5'; // 恢复默认紫色
                toggleIcon.style.opacity = '0.8';   // 恢复默认不透明度
            }
        });

        // 添加关闭知识图谱容器的功能
        if (closeGraphButton) {
            closeGraphButton.addEventListener('click', () => {
                // 隐藏知识图谱容器
                if (knowledgeGraphContainer) {
                    knowledgeGraphContainer.style.display = 'none';
                }

                // 更改图标
                toggleIcon.setAttribute('icon', 'mdi:chevron-down');
                toggleIcon.style.color = '#4f46e5';
                toggleIcon.style.opacity = '0.8';
            });
        }
    }

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
            // 切换按钮状态：隐藏选取元素按钮，显示停止选择按钮
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
            // 切换按钮状态：显示选取元素按钮，隐藏停止选择按钮
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

            // 显示选取元素按钮
            const startButton = document.getElementById('startSelector');
            if (startButton) {
                startButton.style.display = 'flex';
                console.log('清除选择：选取元素按钮已显示');
            }

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
        // tracker.initDOMSelector('startSelector', 'stopSelector', 'element-selector-iframe');

        // 初始化AI聊天行为追踪
        tracker.initChat('send-message', '#user-message', 'learning', currentTopicId);

        // 初始化闲置和焦点检测
        // tracker.initIdleAndFocus();

        console.log('[MainApp] 行为追踪器初始化完成');
    } catch (error) {
        console.error('[MainApp] 行为追踪器初始化失败:', error);
    }
}

// 创建带行为追踪的元素选择处理函数
function createElementSelectedWithTracking() {
    return function (elementInfo, showStatus) {
        console.log('元素选择处理函数被调用，选中的元素信息:', elementInfo);

        // 保存选中的元素信息
        selectedElementInfo = elementInfo;
        console.log('[DEBUG] selectedElementInfo 已更新为:', selectedElementInfo);

        // 自动切换按钮状态
        const startButton = document.getElementById('startSelector');
        const stopButton = document.getElementById('stopSelector');
        const askAIButton = document.getElementById('askAIButton');
        const clearSelectionButton = document.getElementById('clearSelectionButton');

        console.log('获取到的按钮元素:', { startButton, stopButton, askAIButton, clearSelectionButton });

        // 选中元素后，不显示选取元素按钮
        if (startButton && stopButton) {
            startButton.style.display = 'none';
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

// 初始化知识图谱
async function initKnowledgeGraph() {
    // 防止重复初始化
    if (knowledgeGraphInitialized) {
        console.log('[KnowledgeGraph] 知识图谱已经初始化过，跳过重复初始化');
        return;
    }

    try {
        console.log('[KnowledgeGraph] 开始初始化知识图谱...');

        // 获取实验编号并验证
        const participantId = getParticipantId();
        if (!participantId) {
            console.warn('[KnowledgeGraph] 未找到实验编号，无法加载知识图谱');
            return;
        }

        // 并行获取图谱数据和用户进度
        const [graphResponse, progressResponse] = await Promise.all([
            // 请求知识图谱数据
            fetch(buildBackendUrl('/knowledge-graph')),
            fetch(buildBackendUrl(`/progress/participants/${participantId}/progress`))
        ]);

        // 检查响应状态
        if (!graphResponse.ok || !progressResponse.ok) {
            throw new Error('获取数据失败');
        }

        // 解析JSON数据
        const [graphResult, progressResult] = await Promise.all([
            graphResponse.json(),
            progressResponse.json()
        ]);

        // 处理数据
        const graphData = graphResult.data;
        const learnedNodes = progressResult.data.completed_topics || [];

        // 验证数据格式
        if (!graphData || !graphData.nodes || !graphData.edges) {
            throw new Error('图谱数据格式不正确');
        }

        // 初始化状态管理
        graphState = new GraphState(graphData, learnedNodes);
        graphState.initMaps();

        // 设置当前学习章节
        setCurrentLearningChapter(graphState, currentTopicId);

        // 初始化渲染器
        graphRenderer = new GraphRenderer('cy', graphState);
        graphRenderer.addElements([...graphData.nodes, ...graphData.edges]);

        // 设置初始布局
        graphRenderer.setFixedChapterPositions();
        graphRenderer.hideAllKnowledgeNodes();
        graphRenderer.updateNodeColors();

        // 添加工具栏功能
        graphRenderer.addToolbarFunctionality();

        // 添加节点点击事件处理
        setupGraphEventListeners();

        // 标记为已初始化
        knowledgeGraphInitialized = true;

        console.log('[KnowledgeGraph] 知识图谱初始化完成');

        // 初始居中
        setTimeout(() => {
            if (graphRenderer) {
                graphRenderer.centerAndZoomGraph();
            }
        }, 100);

        // 窗口点击事件处理
        window.onclick = (event) => {
            const modal = document.getElementById('knowledgeModal');
            if (event.target === modal) modal.style.display = 'none';
        };

    } catch (error) {
        console.error('[KnowledgeGraph] 初始化知识图谱失败:', error);
    }
}

// 设置知识图谱节点点击事件监听器
function setupGraphEventListeners() {
    if (!graphRenderer || !graphRenderer.cy) {
        console.warn('[KnowledgeGraph] 图渲染器未初始化，无法设置事件监听器');
        return;
    }

    // 单击/双击处理
    const clickState = { lastId: null, timer: null, ts: 0 };
    const DBL_DELAY = 280;

    graphRenderer.cy.on('tap', 'node', (evt) => {
        const node = evt.target;
        const id = node.id();
        const now = Date.now();

        if (clickState.lastId === id && (now - clickState.ts) < DBL_DELAY) {
            clearTimeout(clickState.timer);
            clickState.timer = null;
            clickState.lastId = null;
            handleGraphDoubleClick(node);
        } else {
            clickState.lastId = id;
            clickState.ts = now;
            clickState.timer = setTimeout(() => {
                handleGraphSingleClick(node);
                clickState.timer = null;
                clickState.lastId = null;
            }, DBL_DELAY);
        }
    });
}

// 知识图谱节点单击处理
function handleGraphSingleClick(node) {
    if (!graphState || !graphRenderer) {
        console.warn('[KnowledgeGraph] 知识图谱未初始化，无法处理点击事件');
        return;
    }

    const id = node.id();
    const type = node.data('type');

    if (type === 'chapter') {
        if (graphState.expandedSet.has(id)) {
            graphRenderer.collapseChapter(id);
        } else {
            graphRenderer.expandChapter(id);
        }

        if (graphState.currentLearningChapter === null && id === 'chapter1' &&
            !graphState.learnedNodes.includes(id)) {
            graphState.currentLearningChapter = id;
        }

        graphRenderer.updateNodeColors();
        return;
    }

    if (type === 'knowledge') {
        const label = node.data('label') || id;
        if (graphState.learnedNodes.includes(id)) {// 已学知识点
            showKnowledgeModal(id, label);
        } else if (graphState.isKnowledgeUnlocked(id)) {// 可学知识点
            showKnowledgeModal(id, label);
        } else {// 未解锁知识点
            // 检查是否是跨章节的学习需求
            const chapterCheckResult = checkChapterPrerequisite(id);
            const previousChapterId = chapterCheckResult.requiredChapterId;// 前置章节ID
            if (chapterCheckResult.requiresChapterCompletion) {// 前置章节未解锁
                console.log(`前置章节: ${previousChapterId}`);
                showKnowledgeModal_2(id,previousChapterId,chapterCheckResult.requiredChapter, label);// 提示前置章节的弹窗-未满足章节测试条件则提示测试前置章节最后一个知识点测试的弹窗
            } else {
                // 获取前置知识点信息
                const prerequisiteInfo = getPrerequisiteInfo(id);
                showKnowledgeModal_3(id,prerequisiteInfo.id,prerequisiteInfo.label, label);// 提示前置知识点的弹窗
            }
        }
    }
}

// 知识图谱节点双击处理
function handleGraphDoubleClick(node) {
    if (!graphState || !graphRenderer) {
        console.warn('[KnowledgeGraph] 知识图谱未初始化，无法处理双击事件');
        return;
    }

    const id = node.id();
    const type = node.data('type');

    if (type === 'chapter') {
        if (graphState.isChapterCompleted(id)) {
            showChapterModal(id);//已学过本章节
        } else if (graphState.currentLearningChapter === id) {
            showChapterModal_2(id);//未学完章节
        } else {
            showChapterModal_3(id);//未解锁章节
        }

        graphState.passChapterTest(id);
        graphRenderer.updateNodeColors();
    }

}

// 显示知识图谱容器并渲染知识图谱
async function showKnowledgeGraph() {
    const knowledgeGraphContainer = document.getElementById('knowledge-graph-container');
    if (!knowledgeGraphContainer) {
        console.warn('[KnowledgeGraph] 未找到知识图谱容器元素');
        return;
    }

    // 显示容器
    knowledgeGraphContainer.style.display = 'block';

    // 如果知识图谱还未初始化，则初始化它
    if (!knowledgeGraphInitialized) {
        await initKnowledgeGraph();
    }

    // 如果知识图谱已初始化，确保它正确显示
    if (knowledgeGraphInitialized && graphRenderer) {
        // 确保图谱正确居中显示
        setTimeout(() => {
            graphRenderer.centerAndZoomGraph();
        }, 100);
    }
}

// 将 showKnowledgeGraph 函数设置为全局函数，供其他模块调用
window.showKnowledgeGraph = showKnowledgeGraph;

// ==================== user_idle智能监控 ====================

document.addEventListener('problemHintNeeded', (event) => {
    const { editor, editCount, message } = event.detail;
    console.log(`收到问题提示: ${message}`);

    // 在AI对话框中显示提示
    showProblemHintInChat(message, editor, editCount);
});

// 在AI对话框中显示提示消息
function showProblemHintInChat(message, editorType, editCount) {
    const chatMessages = document.getElementById('ai-chat-messages');
    if (!chatMessages) {
        console.warn('未找到AI聊天消息容器');
        return;
    }

    // 创建AI消息元素
    const aiMessage = document.createElement('div');
    aiMessage.className = 'ai-message';
    aiMessage.innerHTML = `
      <div class="ai-avatar">
        <iconify-icon icon="mdi:robot" width="20" height="20"></iconify-icon>
      </div>
      <div class="ai-content">
        <div class="markdown-content">
            <p>${message}</p>
          </div>
        </div>
      </div>
    `;



    // ✅ ceq关键：永远追加到末尾（保持时间顺序）
    chatMessages.appendChild(aiMessage);

    // 平滑滚动到底部
    // （如果容器用了 column-reverse，请把样式改回正常方向，否则仍会“上新增”）
    if (typeof chatMessages.scrollTo === 'function') {
        chatMessages.scrollTo({ top: chatMessages.scrollHeight, behavior: 'smooth' });
    } else {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 创建并返回AI消息元素
    return aiMessage;
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
window.showElementInfo = function () {
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
    try {
        trackReferrer();
        // 设置标题点击跳转到知识图谱页面
        // setupHeaderTitle('/pages/knowledge_graph.html');
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
    chatModule.sendMessage = async function (mode, contentId) {
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
            const data = await window.apiClient.post('/chat/ai/chat2', requestBody);

            // if (data.code === 200 && data.data && typeof data.data.ai_response === 'string') {
            //     // 添加AI回复到UI
            //     this.addMessageToUI('ai', data.data.ai_response);
            // } else {
            //     throw new Error(data.message || 'AI回复内容为空或格式不正确');
            // }
        } catch (error) {
            console.error('[ChatModule] 发送消息时出错:', error);
            this.addMessageToUI('ai', `抱歉，我无法回答你的问题。错误信息: ${error.message}`);
            // 请求失败（不会有 WebSocket 结果），需要解锁按钮
            this.setLoadingState(false);
        }
    };

    console.log('[Learning] 聊天模块已扩展以支持元素上下文');
}

// 在文件末尾添加新函数
// 设置当前学习章节
function setCurrentLearningChapter(graphState, topicId) {
    try {
        if (topicId) {
            // 查找对应的节点
            const node = graphState.graphData.nodes.find(n =>
                n.data && n.data.id === topicId
            );

            if (node) {
                // 如果是章节节点，直接设置为当前学习章节
                if (node.data.type === 'chapter') {
                    graphState.currentLearningChapter = topicId;
                    console.log('[KnowledgeGraph] 设置当前学习章节:', topicId);
                }
                // 如果是知识点节点，需要找到其所属章节
                else {
                    // 查找父章节
                    const parents = graphState.parentMap[topicId] || [];

                    // 查找第一个章节类型的父节点
                    for (const parentId of parents) {
                        const parentNode = graphState.graphData.nodes.find(n =>
                            n.data && n.data.id === parentId
                        );

                        if (parentNode && parentNode.data.type === 'chapter') {
                            graphState.currentLearningChapter = parentId;
                            console.log('[KnowledgeGraph] 设置当前学习章节(通过知识点查找):', parentId);
                            break;
                        }
                    }

                    // 如果没找到父章节，尝试通过前置关系查找
                    if (!graphState.currentLearningChapter) {
                        const prereqs = graphState.prereqMap[topicId] || [];

                        for (const prereqId of prereqs) {
                            const prereqNode = graphState.graphData.nodes.find(n =>
                                n.data && n.data.id === prereqId
                            );

                            if (prereqNode && prereqNode.data.type === 'chapter') {
                                graphState.currentLearningChapter = prereqId;
                                console.log('[KnowledgeGraph] 设置当前学习章节(通过前置关系查找):', prereqId);
                                break;
                            }
                        }
                    }
                }
            } else {
                console.warn('[KnowledgeGraph] 未找到对应节点:', topicId);
            }
        }
    } catch (error) {
        console.error('[KnowledgeGraph] 设置当前学习章节失败:', error);
    }
}

// 显示知识点弹窗
function showKnowledgeModal(knowledgeId, nodeLabel) {
    const modal = document.getElementById('knowledgeModal');
    const title = document.getElementById('modalTitle');
    const status = document.getElementById('modalStatus');
    const learnBtn = document.getElementById('learnBtn');
    const testBtn = document.getElementById('testBtn');

    title.textContent = nodeLabel || knowledgeId;
    learnBtn.className = 'learn-btn';
    learnBtn.disabled = false;
    learnBtn.textContent = '学习';
    testBtn.className = 'test-btn';

    if (graphState.learnedNodes.includes(knowledgeId)) {
        status.textContent = '您已学过该知识点，是否再次复习或重新测试？';
        learnBtn.textContent = '复习';
        learnBtn.className = 'review-btn';

        learnBtn.onclick = () => {
            navigateTo('/pages/learning_page.html', knowledgeId);
        };

        testBtn.onclick = () => {
            navigateTo('/pages/test_page.html', knowledgeId, true, true);
        };
    } else if (graphState.isKnowledgeUnlocked(knowledgeId)) {
        status.textContent = '您可以开始学习该知识点或直接进行测试';
        testBtn.textContent = '测试';
        testBtn.className = 'review-btn';

        learnBtn.onclick = () => {
            navigateTo('/pages/learning_page.html', knowledgeId);
        };

        testBtn.onclick = () => {
            navigateTo('/pages/test_page.html', knowledgeId, true, true);
        };
    } else {
        status.textContent = '该知识点尚未解锁，您是否要直接开始测试？';
        learnBtn.disabled = true;
        learnBtn.className += ' disabled';

        learnBtn.onclick = () => { };
        testBtn.onclick = () => {
            navigateTo('/pages/test_page.html', knowledgeId, true, true);
        };
    }
    modal.style.display = 'block';
}
function showKnowledgeModal_2(knowledgeId,previousChapterId,requiredChapter, nodeLabel) {
    const modal = document.getElementById('knowledgeModal');
    const title = document.getElementById('modalTitle');
    const status = document.getElementById('modalStatus');
    const learnBtn = document.getElementById('learnBtn');
    const testBtn = document.getElementById('testBtn');

    title.textContent = nodeLabel || knowledgeId;// 使用传入的nodeLabel或knowledgeId
    learnBtn.className = 'learn-btn';
    learnBtn.disabled = false;
    learnBtn.textContent = '是';
    testBtn.textContent = '否';
    testBtn.className = 'test-btn';
                    
    status.textContent = `您还未完成前置章节"${requiredChapter}"的测试，需要先完成该章节的测试才能学习本知识点。是否现在开始测试前置章节？`;

    learnBtn.onclick = () => {
        ('/pages/test_page.html', previousChapterId, true, true);
     };

    testBtn.onclick = () => {
        document.getElementById('knowledgeModal').style.display = 'none';
    };
    
    modal.style.display = 'block';
}
function showKnowledgeModal_3(knowledgeId,lastTestId,requiredKnowledge, nodeLabel) {
    const modal = document.getElementById('knowledgeModal');
    const title = document.getElementById('modalTitle');
    const status = document.getElementById('modalStatus');
    const learnBtn = document.getElementById('learnBtn');
    const testBtn = document.getElementById('testBtn');

    title.textContent = nodeLabel || knowledgeId;// 使用传入的nodeLabel或knowledgeId
    learnBtn.className = 'learn-btn';
    learnBtn.disabled = false;
    learnBtn.textContent = '是';
    testBtn.textContent = '否';
    testBtn.className = 'test-btn';
                    
    status.textContent = `您还未学习前置知识点"${requiredKnowledge}"，需要先完成该知识点的测试才能学习本知识点。是否现在开始测试前置知识点？`;

    learnBtn.onclick = () => {
        navigateTo('/pages/test_page.html',lastTestId, true, true);

     };

    testBtn.onclick = () => {
        document.getElementById('knowledgeModal').style.display = 'none';
    };
    
    modal.style.display = 'block';
}
function showChapterModal(Id) {
    const modal = document.getElementById('knowledgeModal');
    const title = document.getElementById('modalTitle');
    const status = document.getElementById('modalStatus');
    const learnBtn = document.getElementById('learnBtn');
    const testBtn = document.getElementById('testBtn');

    // 只显示章节号，去掉"_end"后缀
    const chapterNumber = Id.split('_')[0];
    title.textContent = `第${chapterNumber}章`
    learnBtn.className = 'learn-btn';
    learnBtn.disabled = false;
    learnBtn.textContent = '是';
    testBtn.textContent = '否';
    testBtn.className = 'test-btn';
                    
    status.textContent = `您已学过本章节，是否再次进行测试？`;

    learnBtn.onclick = () => {
        ('/pages/test_page.html', Id, true, true);
     };

    testBtn.onclick = () => {
        document.getElementById('knowledgeModal').style.display = 'none';
    };
    
    modal.style.display = 'block';
}
function showChapterModal_2(Id) {
    const modal = document.getElementById('knowledgeModal');
    const title = document.getElementById('modalTitle');
    const status = document.getElementById('modalStatus');
    const learnBtn = document.getElementById('learnBtn');
    const testBtn = document.getElementById('testBtn');

    // 只显示章节号，去掉"_end"后缀
    const chapterNumber = Id.split('_')[0];
    title.textContent = `第${chapterNumber}章`;
    learnBtn.className = 'learn-btn';
    learnBtn.disabled = false;
    learnBtn.textContent = '是';
    testBtn.textContent = '否';
    testBtn.className = 'test-btn';
                    
    status.textContent = `您还未学完当前章节内容，是否直接开始测试？`;

    learnBtn.onclick = () => {
        ('/pages/test_page.html', Id, true, true);
     };

    testBtn.onclick = () => {
        document.getElementById('knowledgeModal').style.display = 'none';
    };
    
    modal.style.display = 'block';
}
function showChapterModal_3(Id) {
    const modal = document.getElementById('knowledgeModal');
    const title = document.getElementById('modalTitle');
    const status = document.getElementById('modalStatus');
    const learnBtn = document.getElementById('learnBtn');
    const testBtn = document.getElementById('testBtn');

    // 只显示章节号，去掉"_end"后缀
    const chapterNumber = Id.split('_')[0];
    title.textContent = `第${chapterNumber}章`;
    learnBtn.className = 'learn-btn';
    learnBtn.disabled = false;
    learnBtn.textContent = '是';
    testBtn.textContent = '否';
    testBtn.className = 'test-btn';
                    
    status.textContent = `您还未解锁前置章节，是否直接开始测试？`;

    learnBtn.onclick = () => {
        ('/pages/test_page.html', Id, true, true);
     };

    testBtn.onclick = () => {
        document.getElementById('knowledgeModal').style.display = 'none';
    };
    
    modal.style.display = 'block';
}
// 获取前置知识点信息
function getPrerequisiteInfo(knowledgeId) {
    try {
        // 根据知识图谱的依赖关系获取前置知识点
        const prerequisiteMap = {
            '1_2': { id: '1_1', label: '使用h元素和p元素体验标题与段落' },
            '1_3': { id: '1_2', label: '应用文本格式(加粗、斜体)' },
            '2_2': { id: '2_1', label: '使用盒子元素进行内容划分' },
            '2_3': { id: '2_2', label: '创建有序列表' },
            '3_2': { id: '3_1', label: '文本框与按钮的使用' },
            '3_3': { id: '3_2', label: '复选框与单选框' },
            '4_2': { id: '4_1', label: '设置颜色与字体' },
            '4_3': { id: '4_2', label: '理解盒模型' },
            '5_2': { id: '5_1', label: '插入与管理图片' },
            '5_3': { id: '5_2', label: '引入音频文件' },
            '6_2': { id: '6_1', label: '按钮点击事件' },
            '6_3': { id: '6_2', label: '获取用户输入' }
        };

        return prerequisiteMap[knowledgeId] || null;
    } catch (error) {
        console.error('获取前置知识点信息时出错:', error);
        return null;
    }
}

// 检查章节前置条件
function checkChapterPrerequisite(knowledgeId) {
    try {
        const [chapter, section] = knowledgeId.split('_').map(Number);

        // 如果是第一章的第一个知识点，不需要前置条件
        if (chapter === 1 && section === 1) {
            return { requiresChapterCompletion: false };
        }

        // 如果是第一章的其他知识点，检查章节内前置条件
        if (chapter === 1) {
            return { requiresChapterCompletion: false };
        }

        // 检查章节间的前置条件
        const completedChapters = JSON.parse(localStorage.getItem('completedChapters') || '[]');
        
        // 查找最早的未完成章节
        for (let i = 1; i < chapter; i++) {
            const checkChapterId = `chapter${i}`;
            if (!completedChapters.includes(checkChapterId)) {
                return {
                    requiresChapterCompletion: true,
                    requiredChapter: `第${i}章`,
                    requiredChapterId: `${i}_end`,
                    lastTestId: `${i}_3` // 该章节的最后一个测试
                };
            }
        }

        // 如果当前章节不是第一章且所有前置章节都已完成
        return { requiresChapterCompletion: false };
    } catch (error) {
        console.error('检查章节前置条件时出错:', error);
        return { requiresChapterCompletion: false };
    }
}
