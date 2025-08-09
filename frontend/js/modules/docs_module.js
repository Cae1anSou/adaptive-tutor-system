// ==================== 文档模块 ====================
import { AppConfig } from './config.js';

const DIFFICULTY = [
    { key: 'basic', label: '基础介绍', category: 'basic' },
    { key: 'intermediate', label: '语法和基本用法', category: 'basic' },
    { key: 'advanced', label: '实际应用', category: 'advanced' },
    { key: 'expert', label: '深入原理', category: 'advanced' }
];

let docsModuleState = {
    currentTag: null,
    currentLevelIndex: 0,
    contents: {},
    basicTimer: 0,
    advancedTimer: 0,
    basicInterval: null,
    advancedInterval: null
};

// API客户端 - 使用统一的 api_client
import ApiClient, { resolveEndpoint } from '../api_client.js';

// 加载文档内容
async function loadDocumentForTag(tagName) {
    try {
        // 使用 content_service 获取学习内容
        const { getLearningContent } = await import('../services/content_service.js');
        const contentData = await getLearningContent(tagName);
        
        docsModuleState.currentTag = { id: tagName, title: `${tagName} 组件` };
        docsModuleState.currentLevelIndex = 0;
        
        // 将学习内容转换为原来的格式
        docsModuleState.contents = {
            basic: contentData.content || `${tagName} 标签是HTML中常用的元素。`,
            intermediate: contentData.content || `${tagName} 标签的基本语法：<${tagName}>内容</${tagName}>`,
            advanced: contentData.content || `${tagName} 标签可以包含其他HTML元素和文本内容。`,
            expert: contentData.content || `${tagName} 标签支持各种属性，如class、id、style等。`
        };
        
        renderDocContent();
        startTimer();
    } catch (e) {
        // 如果后端API失败，使用默认内容
        console.warn('无法从后端获取内容，使用默认内容:', e.message);
        
        docsModuleState.currentTag = { id: tagName, title: `${tagName} 组件` };
        docsModuleState.currentLevelIndex = 0;
        
        // 生成默认的HTML标签说明
        const defaultContents = {
            basic: `${tagName} 标签是HTML中常用的元素。`,
            intermediate: `${tagName} 标签的基本语法：<${tagName}>内容</${tagName}>`,
            advanced: `${tagName} 标签可以包含其他HTML元素和文本内容。`,
            expert: `${tagName} 标签支持各种属性，如class、id、style等。`
        };
        
        docsModuleState.contents = defaultContents;
        renderDocContent();
        startTimer();
    }
}

// 渲染文档内容
function renderDocContent() {
    const tagTitle = document.getElementById('tag-title');
    const tagContent = document.getElementById('tag-content');
    if (!docsModuleState.currentTag) {
        if (tagTitle) tagTitle.textContent = '请选择组件';
        if (tagContent) tagContent.innerHTML = '';
        return;
    }
    
    const level = DIFFICULTY[docsModuleState.currentLevelIndex];
    let content = docsModuleState.contents[level.key] || `暂无${level.label}内容。`;
    
    if (tagTitle) tagTitle.textContent = `${docsModuleState.currentTag.title}`;
    if (tagContent) {
        tagContent.innerHTML = `
            <div class="level-block">
                <h3>${level.label}</h3>
                <pre class="content-text">${content}</pre>
                <div class="level-btns">
                    <button id="prev-btn" ${docsModuleState.currentLevelIndex===0?'disabled':''}>上一级</button>
                    <button id="next-btn" ${docsModuleState.currentLevelIndex===DIFFICULTY.length-1?'disabled':''}>下一级</button>
                    ${docsModuleState.currentLevelIndex===3 ? '<button id="complete-btn">阅读完毕</button>' : ''}
                </div>
            </div>
        `;
        
        // 绑定按钮事件
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        const completeBtn = document.getElementById('complete-btn');
        
        if (prevBtn) {
            prevBtn.onclick = function() {
                if (docsModuleState.currentLevelIndex > 0) {
                    docsModuleState.currentLevelIndex--;
                    renderDocContent();
                }
            };
        }
        
        if (nextBtn) {
            nextBtn.onclick = function() {
                if (docsModuleState.currentLevelIndex < DIFFICULTY.length-1) {
                    docsModuleState.currentLevelIndex++;
                    renderDocContent();
                }
            };
        }
        
        if (completeBtn) {
            completeBtn.onclick = async function(e) {
                e.preventDefault();
                stopTimer();
                await sendTimeToBackend();
                this.textContent = '您已完成此组件学习';
                this.disabled = true;
            };
        }
    }
    
    startTimer();
    updateTimeDisplay();
}

// 计时器相关函数
function startTimer() {
    stopTimer();
    const level = DIFFICULTY[docsModuleState.currentLevelIndex];
    if (level.category === 'basic') {
        docsModuleState.basicInterval = setInterval(() => {
            docsModuleState.basicTimer++;
            updateTimeDisplay();
        }, 1000);
    } else {
        docsModuleState.advancedInterval = setInterval(() => {
            docsModuleState.advancedTimer++;
            updateTimeDisplay();
        }, 1000);
    }
}

function stopTimer() {
    clearInterval(docsModuleState.basicInterval);
    clearInterval(docsModuleState.advancedInterval);
}

function updateTimeDisplay() {
    const basicTime = document.getElementById('basic-time');
    const advancedTime = document.getElementById('advanced-time');
    if (basicTime) basicTime.textContent = formatTime(docsModuleState.basicTimer);
    if (advancedTime) advancedTime.textContent = formatTime(docsModuleState.advancedTimer);
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

async function sendTimeToBackend() {
    // 只在前端显示，不向后端传输数据
    console.log('学习时间记录（仅前端显示）:', {
        basic_time: docsModuleState.basicTimer,
        advanced_time: docsModuleState.advancedTimer
    });
    
    // 重置本地计时器
    docsModuleState.basicTimer = 0;
    docsModuleState.advancedTimer = 0;
    updateTimeDisplay();
    
    console.log('学习时间已重置');
}

// 错误显示
function showError(msg) {
    let statusDiv = document.getElementById('statusContainer');
    if (!statusDiv) {
        statusDiv = document.createElement('div');
        statusDiv.id = 'statusContainer';
        statusDiv.className = 'status info';
        const tagContent = document.getElementById('tag-content');
        if (tagContent) tagContent.prepend(statusDiv);
    }
    statusDiv.textContent = msg;
    statusDiv.style.display = 'block';
    setTimeout(() => { statusDiv.style.display = 'none'; }, 3000);
}

// 初始化知识点内容
function initKnowledgeContent() {
    const knowledgeContent = document.getElementById('knowledge-content');
    if (!knowledgeContent) return;
    
    knowledgeContent.innerHTML = `
        <div class="card-container">
            <div id="card-content" class="card">
                <h2 id="tag-title" class="card-title">请选择组件</h2>
                <div id="tag-content"></div>
            </div>
        </div>
        <div class="timer-display">
            <div class="timer-item"><span class="timer-label">基础内容：</span><span id="basic-time">00:00</span></div>
            <div class="timer-item"><span class="timer-label">进阶内容：</span><span id="advanced-time">00:00</span></div>
        </div>
    `;
}

// 导出模块
window.DocsModule = {
    loadDocumentForTag,
    renderDocContent,
    startTimer,
    stopTimer,
    updateTimeDisplay,
    sendTimeToBackend,
    showError,
    initKnowledgeContent,
    ApiClient,
    DIFFICULTY,
    docsModuleState
}; 