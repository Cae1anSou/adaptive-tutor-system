// 导入模块
import { getParticipantId } from '../modules/session.js';
import { marked } from "https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js";
import { setupHeaderTitle, setupBackButton, getUrlParam, debugUrlParams, getReturnUrl, navigateTo } from '../modules/navigation.js';
import tracker from '../modules/behavior_tracker.js';
import chatModule from '../modules/chat.js';
import websocket from '../modules/websocket_client.js';

// 用于存储WebSocket订阅回调的引用，避免重复订阅
let submissionCallbackRef = null;

tracker.init({
    user_idle: true,
    page_click: true,
});
// 初始化函数
async function initializePage() {
    const participantId = getParticipantId();
    if (participantId) {
        const participantElement = document.getElementById('participant_id');
        if (participantElement) {
            participantElement.textContent = participantId;
        }
    }
    // 获取并解密URL参数
     // 获取URL参数（带错误处理）
        const topicData = getUrlParam('topic');
        
        if (topicData && topicData.id) {
            console.log('测试主题ID:', topicData.id, '有效期:', topicData.isValid ? '有效' : '已过期');
                
            // 更新页面标题
            document.getElementById('headerTitle').textContent = `测试 - ${topicData.id}`;
            
            // 即使过期也继续加载内容，但提示用户
            if (!topicData.isValid) {
               console.warn('参数已过期，但仍继续加载内容');
            }
                
            // 加载对应的测试内容
            chatModule.init('test', topicData.id);
        } else {
            console.warn('未找到有效的主题参数，使用默认内容');
            console.log('加载默认测试内容');
        }
    
    let topicId = topicData.id;
    
    // 如果没有topic参数，且查询字符串只有一个值，则使用该值
    if (!topicId) {
        const urlParams = new URLSearchParams(window.location.search);
        // 获取所有参数的键
        const keys = Array.from(urlParams.keys());
        // 如果没有键（如?1_1），则使用整个查询字符串
        if (keys.length === 0 && window.location.search.length > 1) {
            topicId = window.location.search.substring(1); // 去掉开头的'?'
        }
        // 如果有键但键为空字符串（这种情况较少见），则使用第一个值
        else if (keys.length === 1 && keys[0] === '') {
            topicId = urlParams.get('');
        }
    }

    if (!topicId) {
        console.error('未找到Topic ID');
        alert('错误：无效的测试链接。');
        return;
    }

    try {
        // 使用不带认证的get方法获取测试任务数据
        const response = await window.apiClient.getWithoutAuth(`/test-tasks/${topicId}`);
        if (response.code === 200 && response.data) {
            const task = response.data;
            // 更新UI
            updateUIWithTaskData(task);
            // 初始化编辑器
            initializeEditors(task.start_code);

        } else {
            throw new Error(response.message || '获取测试任务失败');
        }
    } catch (error) {
        console.error('初始化页面时出错:', error);
        alert('无法加载测试任务: ' + (error.message || '未知错误'));
    }

    try{
        websocket.connect();
        console.log('[MainApp] WebSocket模块初始化完成');
    }
    catch(error){
        console.error('[MainApp] WebSocket模块初始化失败:', error);
    }
}

// 更新UI
function updateUIWithTaskData(task) {
    const headerTitle = document.querySelector('.header-title');
    const requirementsContent = document.getElementById('test-requirements-content');
    if (headerTitle) {
        headerTitle.textContent = task.title || '编程测试';
    }
    if (requirementsContent) {
        requirementsContent.innerHTML = marked(task.description_md || '');
    }
}

// 初始化Monaco编辑器并设置实时预览
function initializeEditors(startCode) {
    // 设置初始代码
    if (typeof window.setInitialCode === 'function') {
        window.setInitialCode(startCode);
    }

    // 延迟初始化编辑器，确保editor.js中的require已经执行
    setTimeout(() => {
        if (window.monaco && window.editorState) {
            // 更新已经创建的编辑器实例的内容
            if (window.editorState.htmlEditor && window.editorState.htmlEditor.setValue) {
                window.editorState.htmlEditor.setValue(window.editorState.html);
            }
            if (window.editorState.cssEditor && window.editorState.cssEditor.setValue) {
                window.editorState.cssEditor.setValue(window.editorState.css);
            }
            if (window.editorState.jsEditor && window.editorState.jsEditor.setValue) {
                window.editorState.jsEditor.setValue(window.editorState.js);
            }
            // 初始化代码改动监控
            initSmartCodeTracking();
            // 触发预览更新
            if (typeof updateLocalPreview === 'function') {
                updateLocalPreview();
            }
        } else {
            console.error("Monaco Editor 或 editorState 未正确初始化。");
        }
    }, 100);
}

// 初始化智能代码监控
// 初始化智能代码监控
function initSmartCodeTracking() {
    if (window.editorState && tracker && typeof tracker.initSmartCodeTracking === 'function') {
        const editors = {
            html: window.editorState.htmlEditor,
            css: window.editorState.cssEditor,
            js: window.editorState.jsEditor
        };
        // 初始化智能监控
        tracker.initSmartCodeTracking(editors);
        console.log('智能代码监控已启动 - 基于事件触发模式');
        // 设置会话结束处理器（页面关闭时提交总结数据）
        if (typeof tracker._initSessionEndHandler === 'function') {
            tracker._initSessionEndHandler();
        }

        // 监听问题提示事件
        document.addEventListener('problemHintNeeded', (event) => {
            const { editor, editCount, message } = event.detail;
            console.log(`收到问题提示: ${message}`);

            // 在AI对话框中显示提示
            showProblemHintInChat(message, editor, editCount);
        });

    } else {
        console.warn('无法初始化智能代码监控：编辑器状态或跟踪器不可用');
    }
}
// 在AI对话框中显示提示消息
// 在AI对话框中显示提示消息（适配现有HTML结构）
// 在AI对话框中显示提示消息（永远追加到底部）
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

    return aiMessage;
}


// 提交逻辑
function setupSubmitLogic() {
    const submitButton = document.getElementById('submit-button');
    if (!submitButton) return;
    submitButton.addEventListener('click', async () => {
        const behaviorAnalysis = tracker.getCodingBehaviorAnalysis();
        console.log('提交时的编程行为分析:', behaviorAnalysis);
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = '批改中...';


        // 创建一个函数来恢复按钮状态
        function restoreButton() {
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }

        try {
            // 使用已解密的topicId而不是直接从URL获取加密参数
            const topicData = getUrlParam('topic');
            const topicId = topicData && topicData.id ? topicData.id : null;

            if (!topicId) throw new Error("主题ID无效。");

            // 提交前的完整行为分析
            const finalBehaviorAnalysis = tracker.getCodingBehaviorAnalysis();
            console.log('最终编程行为分析:', finalBehaviorAnalysis);

            // 立即提交会话总结（确保数据不丢失）
            if (typeof tracker._submitAllData === 'function') {
                tracker._submitAllData();
            }

            console.log('提交测试，主题ID:', topicId);
            const submissionData = {
                topic_id: topicId,
                code: {
                    html: window.editorState.htmlEditor?.getValue() || '',
                    css: window.editorState.cssEditor?.getValue() || '',
                    js: window.editorState.jsEditor?.getValue() || ''
                },
                // 包含编程行为分析数据
                coding_behavior: behaviorAnalysis,
                // 添加元数据
                metadata: {
                    session_start: new Date(finalBehaviorAnalysis.sessionStart || Date.now()).toISOString(),
                    total_edits: finalBehaviorAnalysis.totalSignificantEdits || 0,
                    problem_count: finalBehaviorAnalysis.problemEventsCount || 0
                }
            };
            
            // 提交测试并等待响应
            const result = await window.apiClient.post('/submission/submit-test2', submissionData);

            // 保存订阅回调的引用，以便后续取消订阅
            let submissionCallback = (msg) => {
                console.log("[SubmitModule] 收到最终结果:", msg);
                // 恢复按钮状态
                restoreButton();
                displayTestResult(msg);
                if(msg.passed) {
                    // 获取当前topic参数
                    const topicData = getUrlParam('topic');
                    let currentTopicId = topicData && topicData.id ? topicData.id : null;
                    let nextTopicId = null;
                    let shouldNavigateToLearning = false;
                    
                    if (currentTopicId) {
                        // 检查是否已经是最后一小节(6_3)
                        if (currentTopicId === '6_3') {
                            // 如果已经是6_3，跳转回6_3的学习页面
                            nextTopicId = '6_3';
                            shouldNavigateToLearning = true;
                        } else {
                            // 计算下一小节的topic_id
                            const [chapter, section] = currentTopicId.split('_').map(Number);
                            let nextChapter = chapter;
                            let nextSection = section + 1;
                            
                            // 处理章节边界情况
                            if (nextSection > 3) {
                                nextChapter += 1;
                                nextSection = 1;
                            }
                            
                            // 确保不超过最大章节
                            if (nextChapter <= 6) {
                                nextTopicId = `${nextChapter}_${nextSection}`;
                                shouldNavigateToLearning = true;
                            }
                        }
                    }
                    
                    // 显示提示信息
                    if (shouldNavigateToLearning) {
                        alert(`测试完成！即将跳转到${nextTopicId}学习界面`);
                        // 立即开始倒计时跳转
                        setTimeout(() => { 
                            navigateTo('/pages/learning_page.html', nextTopicId, true); 
                        }, 100);
                    } else {
                        alert("测试完成！即将跳转回到注册页面");
                        // 立即开始倒计时跳转
                        setTimeout(() => { 
                            window.location.href = '/pages/index.html'; 
                        }, 100);
                    }
                } else {
                    tracker.logEvent('test_failed', {
                        topic_id: topicId,
                        edit_count: finalBehaviorAnalysis.totalSignificantEdits,
                        problem_count: finalBehaviorAnalysis.problemEventsCount,
                        failure_reason: result.data.message || '未知原因'
                    });
                    // TODO: 可以考虑直接在这里主动触发AI
                    // 测试未通过，给用户一些鼓励和建议
                    alert("测试未通过，请查看详细结果并继续改进代码。");
                }
                
                // 取消订阅，避免重复触发
                websocket.unsubscribe("submission_result", submissionCallback);
            };
            
            // 先取消之前的订阅（如果有的话），然后再订阅新的回调
            if (submissionCallbackRef) {
                websocket.unsubscribe("submission_result", submissionCallbackRef);
            }
            websocket.subscribe("submission_result", submissionCallback);
            // 保存回调引用以便下次取消订阅
            submissionCallbackRef = submissionCallback;

        } catch (error) {
            console.error('提交测试时出错:', error);
            tracker.logEvent('submission_error', {
                error_message: error.message,
                timestamp: new Date().toISOString()
            });
            // 出错时也恢复按钮状态
            restoreButton();
            alert('提交测试时出错: ' + (error.message || '未知错误'));
        }
    });
}

// 显示测试结果
function displayTestResult(result) {
    const testResultsContent = document.getElementById('test-results-content');
    if (!testResultsContent) {
        console.warn("未找到 'test-results-content' 元素。");
        const message = `${result.passed ? '✅ 通过' : '❌ 失败'}: ${result.message}\n\n详情:\n${(result.details || []).join('\n')}`;
        alert(message);
        return;
    }

    let content = `<h4>${result.passed ? '✅ 恭喜！通过测试！' : '❌ 未通过测试'}</h4><p>${result.message || ''}</p>`;
    if (result.details && result.details.length > 0) {
        content += `<h5>详细信息:</h5><ul>${result.details.map(d => `<li>${d}</li>`).join('')}</ul>`;
    }

    testResultsContent.innerHTML = content;
    testResultsContent.className = result.passed ? 'test-result-passed' : 'test-result-failed';
}

// 主程序入口
document.addEventListener('DOMContentLoaded', function () {
    // 设置标题和返回按钮
    setupHeaderTitle('/pages/knowledge_graph.html');
    // 设置返回按钮
    setupBackButton();
    // 调试信息
    debugUrlParams();
    require(['vs/editor/editor.main'], function () {
        initializePage();
        setupSubmitLogic();

        // 初始化AI聊天功能
        // 获取并解密URL参数
        const returnUrl = getReturnUrl();
        console.log('返回URL:', returnUrl);
        const contentId = getUrlParam('topic');
        if (contentId && contentId.id) {
            // 使用新的聊天模块初始化
            chatModule.init('test', contentId);
        }
    });
});