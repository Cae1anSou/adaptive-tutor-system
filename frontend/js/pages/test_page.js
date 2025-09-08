// 导入模块
import { getParticipantId } from '../modules/session.js';
import { marked } from "https://cdn.jsdelivr.net/npm/marked/lib/marked.esm.js";
import { setupHeaderTitle, setupBackButton, getUrlParam, debugUrlParams, getReturnUrl, navigateTo } from '../modules/navigation.js';
import tracker from '../modules/behavior_tracker.js';
import chatModule from '../modules/chat.js';
import websocket from '../modules/websocket_client.js';

// 用于存储WebSocket订阅回调的引用，避免重复订阅
let submissionCallbackRef = null;

// 用于跟踪AI询问次数和提交次数的全局变量
let aiAskCount = 0;
let submissionCount = 0;
let failedSubmissionCount = 0;
let chatResultCallbackRef = null;

// 添加一个标志位，用于跟踪是否已经在本次提交后触发过AI主动询问
let hasTriggeredAssistanceAfterSubmission = false;

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

            // 保存任务数据，供后续使用
            window.currentTaskData = task;
        } else {
            throw new Error(response.message || '获取测试任务失败');
        }
    } catch (error) {
        console.error('初始化页面时出错:', error);
        alert('无法加载测试任务: ' + (error.message || '未知错误'));
    }

    try {
        websocket.connect();
        console.log('[MainApp] WebSocket模块初始化完成');
    }
    catch (error) {
        console.error('[MainApp] WebSocket模块初始化失败:', error);
    }

    // 扩展聊天模块以支持智能提示功能
    extendChatModuleForSmartHints(topicId);

    // 绑定解题思路按钮事件
    bindProblemSolvingHintButton(topicId);
}

// 扩展聊天模块以支持智能提示功能
function extendChatModuleForSmartHints(topicId) {
    if (!chatModule) return;

    // 取消chat.js模块中的默认chat_result订阅
    websocket.unsubscribeAll("chat_result");

    // 重写sendMessage方法
    chatModule.sendMessage = async function (mode, contentId) {
        const message = this.inputElement.value.trim();
        if (!message || this.isLoading) return;

        // 增加AI询问计数
        aiAskCount++;
        console.log(`AI询问次数: ${aiAskCount}`);

        // 清空输入框
        this.inputElement.value = '';

        // 添加用户消息到UI
        this.addMessageToUI('user', message);

        // 设置加载状态
        this.setLoadingState(true);

        try {
            // 获取对话历史
            const conversationHistory = this.getConversationHistory();

            // 构建请求体
            const requestBody = {
                user_message: message,
                conversation_history: conversationHistory,
                code_context: this.getCodeContext(),
                mode: mode,
                content_id: contentId
            };

            // 如果是测试模式，添加测试结果
            if (mode === 'test') {
                const testResults = this._getTestResults();
                if (testResults) {
                    requestBody.test_results = testResults;
                }
            }

            // 使用封装的 apiClient 发送请求
            await window.apiClient.post('/chat/ai/chat2', requestBody);
        } catch (error) {
            console.error('[ChatModule] 发送消息时出错:', error);
            this.addMessageToUI('ai', `抱歉，我无法回答你的问题。错误信息: ${error.message}`);
            // 请求失败（不会有 WebSocket 结果），需要解锁按钮
            this.setLoadingState(false);
        }
    };

    // 监听提交结果，更新提交计数
    const originalSubmissionCallback = submissionCallbackRef;
    submissionCallbackRef = (msg) => {
        // 增加提交计数
        submissionCount++;
        console.log(`提交次数: ${submissionCount}`);

        // 如果提交失败，增加失败计数
        if (!msg.passed) {
            failedSubmissionCount++;
            console.log(`提交失败次数: ${failedSubmissionCount}`);
        }

        // 重置AI主动询问触发标志位
        hasTriggeredAssistanceAfterSubmission = false;

        // 调用原始回调
        if (originalSubmissionCallback) {
            originalSubmissionCallback(msg);
        }

        // 检查是否需要触发智能提示或直接提供答案（提交后检查）
        checkAndTriggerAssistanceAfterAction(topicId, aiAskCount, submissionCount, failedSubmissionCount, null);
    };

    // 重新订阅WebSocket消息
    websocket.unsubscribe("submission_result", originalSubmissionCallback);
    websocket.subscribe("submission_result", submissionCallbackRef);

    // 扩展聊天模块以在AI回答后触发智能提示
    extendChatModuleForAIResponse(topicId, () => ({ aiAskCount, submissionCount, failedSubmissionCount }));

    console.log('[TestPage] 聊天模块已扩展以支持智能提示功能');
}

// 扩展聊天模块以在AI回答后触发智能提示
function extendChatModuleForAIResponse(topicId, getCounters) {
    if (!chatModule) return;

    // 如果已经有一个chat_result的回调函数，先取消订阅
    if (chatResultCallbackRef) {
        websocket.unsubscribe("chat_result", chatResultCallbackRef);
    }

    // 定义新的chat_result处理函数
    chatResultCallbackRef = (msg) => {
        console.log("[ChatModule] 收到AI结果:", msg);
        // 展示AI回复
        chatModule.addMessageToUI('ai', msg.ai_response);
        // 收到结果后解除加载状态，解锁"提问"按钮
        chatModule.setLoadingState(false);
        // 双重保证：收到结果时清空输入框（即使发送时已清空）
        if (chatModule.inputElement) {
            chatModule.inputElement.value = '';
        }

        // 在AI回答后检查是否需要触发智能提示
        // 获取当前的计数器值
        const { aiAskCount, submissionCount, failedSubmissionCount } = getCounters();

        // 检查是否需要触发智能提示或直接提供答案（AI回答后检查）
        checkAndTriggerAssistanceAfterAction(topicId, aiAskCount, submissionCount, failedSubmissionCount, chatModule.getConversationHistory());
    };

    // 订阅WebSocket消息
    websocket.subscribe("chat_result", chatResultCallbackRef);
}

// 添加一个新的辅助函数来统一检查触发条件
function checkAndTriggerAssistanceAfterAction(topicId, aiAskCount, submissionCount, failedSubmissionCount, conversationHistory) {
    // 只在有提交行为后才触发检查，并且确保只触发一次
    if (submissionCount > 0 && !hasTriggeredAssistanceAfterSubmission) {
        // 检查AI询问次数条件
        if (aiAskCount >= 4 && aiAskCount % 2 === 0) {
            if (aiAskCount < 10) {
                hasTriggeredAssistanceAfterSubmission = true;
                setTimeout(() => {
                    triggerSmartHint(topicId, conversationHistory || [], aiAskCount, submissionCount, failedSubmissionCount);
                }, 1000);
            }
            // 当用户询问10次及以上且提交4次未通过时，直接给出答案
            else if (aiAskCount >= 10 && failedSubmissionCount >= 4) {
                hasTriggeredAssistanceAfterSubmission = true;
                setTimeout(() => {
                    provideDirectAnswer(topicId);
                }, 1000);
            }
        }
    }
}

// 触发智能提示
async function triggerSmartHint(topicId, conversationHistory, aiAskCount, submissionCount, failedSubmissionCount) {
    try {
        // 构建提示消息
        const hintMessage = `我注意到您已经询问了${aiAskCount}次问题，并且提交了${submissionCount}次代码（其中${failedSubmissionCount}次未通过）。

**您是否需要我为您提供一些针对性的学习建议或解题思路？**

我可以帮您：
1. 分析您代码中的常见问题
2. 提供解题思路和关键知识点
3. 给出一些调试建议

请告诉我您希望了解哪方面的内容，我会尽力帮助您。`;

        // 在聊天框中显示提示
        chatModule.addMessageToUI('ai', hintMessage);

        // 记录行为事件
        tracker.logEvent('smart_hint_triggered', {
            topic_id: topicId,
            ai_ask_count: aiAskCount,
            submission_count: submissionCount,
            failed_submission_count: failedSubmissionCount,
            message: '智能提示已触发'
        });
    } catch (error) {
        console.error('触发智能提示时出错:', error);
    }
}

// 直接提供答案
async function provideDirectAnswer(topicId) {
    try {
        // 调用后端API获取答案
        const response = await window.apiClient.getWithoutAuth(`/test-tasks/${topicId}`);
        if (response.code === 200 && response.data) {
            const task = response.data;
            const answer = task.answer;

            // 构建答案消息
            const answerMessage = `我注意到您在解决这个问题时遇到了一些困难。让我直接为您提供参考答案和解题思路：

**题目要求：**
${task.description_md}

**参考答案：**
\`\`\`html
${answer.html || ''}
\`\`\`

\`\`\`css
${answer.css || ''}
\`\`\`

\`\`\`javascript
${answer.js || ''}
\`\`\`

**建议：**
1. 仔细对比您的代码和参考答案，找出差异
2. 理解每一步的实现原理
3. 尝试独立重新实现一遍

如果您还有其他问题，欢迎继续提问！`;

            // 在聊天框中显示答案
            chatModule.addMessageToUI('ai', answerMessage);

            // 记录行为事件
            tracker.logEvent('direct_answer_provided', {
                topic_id: topicId,
                message: '直接提供答案'
            });
        }
    } catch (error) {
        console.error('提供直接答案时出错:', error);
        // 显示错误提示
        chatModule.addMessageToUI('ai', '抱歉，暂时无法获取参考答案，请稍后再试。');
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

        // 对HTML标签进行智能转义处理
        let rawHtml = smartEscapeHtmlTagsWithRegex(task.description_md);
        // 先将Markdown转换为HTML
        rawHtml = marked(rawHtml || '');
        requirementsContent.innerHTML = rawHtml;
    }
}

// 智能转义HTML标签函数 - 基于正则表达式
function smartEscapeHtmlTagsWithRegex(html) {
    // 定义代码块的正则表达式
    const codeBlockRegex = /(```[\s\S]*?```)/g;

    // 提取所有代码块
    const codeBlocks = [];
    let match;
    while ((match = codeBlockRegex.exec(html)) !== null) {
        codeBlocks.push(match[0]);
    }

    // 将代码块替换为占位符
    let htmlWithPlaceholders = html;
    codeBlocks.forEach((block, index) => {
        const placeholder = `__CODE_BLOCK_${index}__`;
        htmlWithPlaceholders = htmlWithPlaceholders.replace(block, placeholder);
    });

    // 定义不需要转义的HTML标签的正则表达式（如Markdown标题）
    const regexForNoEscape = /^(#{1,3})\s+/gm;

    // 将HTML字符串按行分割
    const lines = htmlWithPlaceholders.split('\n');

    // 处理每一行
    const processedLines = lines.map(line => {
        // 检查当前行是否包含不需要转义的标签
        if (regexForNoEscape.test(line)) {
            // 不需要转义，直接返回原行
            return line;
        } else {
            // 需要转义，处理HTML标签
            return line.replace(/</g, '<').replace(/>/g, '>');
        }
    });

    // 将处理后的行重新组合成HTML字符串
    let processedHtml = processedLines.join('\n');

    // 将占位符还原为原始代码块
    codeBlocks.forEach((block, index) => {
        const placeholder = `__CODE_BLOCK_${index}__`;
        processedHtml = processedHtml.replace(placeholder, block);
    });

    return processedHtml;
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
        <div class="message-content">
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
                if (msg.passed) {
                    // 获取当前topic参数
                    const topicData = getUrlParam('topic');
                    let currentTopicId = topicData && topicData.id ? topicData.id : null;

                    if (currentTopicId) {
                        // 标记当前知识点为已学习
                        markKnowledgeAsLearned(currentTopicId);

                        // 检查是否是章节的最后一个测试
                        const isLastTestInChapter = isLastTestInCurrentChapter(currentTopicId);

                        if (isLastTestInChapter) {
                            // 完成章节测试，标记章节为已完成
                            const currentChapter = getChapterFromTopicId(currentTopicId);
                            markChapterAsCompleted(currentChapter);

                            // 获取下一个章节的第一个知识点
                            const nextChapterFirstKnowledge = getNextChapterFirstKnowledge(currentChapter);

                            if (nextChapterFirstKnowledge) {
                                // 显示章节完成弹窗
                                showChapterCompletionModal(currentChapter, nextChapterFirstKnowledge);
                            } else {
                                // 没有下一个章节，显示完成信息
                                alert("恭喜！您已完成所有章节！");
                                setTimeout(() => {
                                    window.location.href = '/pages/index.html';
                                }, 100);
                            }
                        } else {
                            // 获取下一个知识点信息
                            const nextKnowledgeInfo = getNextKnowledgeInfo(currentTopicId);

                            if (nextKnowledgeInfo) {
                                // 显示完成测试的弹窗
                                showTestCompletionModal(currentTopicId, nextKnowledgeInfo);
                            } else {
                                // 没有下一个知识点，显示完成信息
                                alert("恭喜！您已完成所有测试！");
                                setTimeout(() => {
                                    window.location.href = '/pages/index.html';
                                }, 100);
                            }
                        }
                    } else {
                        alert("测试完成！");
                        setTimeout(() => {
                            // 返回到当前topicId对应的学习页面
                            if (topicId) {
                                navigateTo('/pages/learning_page.html', topicId, true);
                            } else {
                                window.location.href = '/pages/knowledge_graph.html';
                            }
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

            // 增加提交计数
            submissionCount++;
            console.log(`提交次数: ${submissionCount}`);
            // 检查是否需要触发智能提示或直接提供答案（提交后检查）
            checkAndTriggerAssistanceAfterAction(topicId, aiAskCount, submissionCount, failedSubmissionCount, null);

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
        // 对details中的HTML标签进行转义处理，确保它们作为文本显示
        const escapedDetails = result.details.map(detail => {
            return detail.replace(/</g, '&lt;').replace(/>/g, '&gt;');
        });
        content += `<h5>详细信息:</h5><ul>${escapedDetails.map(d => `<li>${d}</li>`).join('')}</ul>`;
    }

    testResultsContent.innerHTML = content;
    testResultsContent.className = result.passed ? 'test-result-passed' : 'test-result-failed';

    // 显示"询问AI"按钮（仅在测试失败时显示）
    const askAIContainer = document.getElementById('ask-ai-container');
    if (askAIContainer) {
        askAIContainer.style.display = result.passed ? 'none' : 'block';

        // 绑定"询问AI"按钮事件
        if (!result.passed) {
            bindAskAIButton(result);
        }
    }
}

// 绑定"询问AI"按钮事件
function bindAskAIButton(testResult) {
    const askAIButton = document.getElementById('ask-ai-btn');
    if (askAIButton) {
        // 清除之前的事件监听器
        const newAskAIButton = askAIButton.cloneNode(true);
        askAIButton.parentNode.replaceChild(newAskAIButton, askAIButton);

        newAskAIButton.addEventListener('click', () => {
            // 触发询问AI功能
            triggerAskAI(testResult);
        });
    }
}

// 触发询问AI功能
async function triggerAskAI(testResult) {
    try {
        // 获取当前任务数据
        const task = window.currentTaskData;
        if (!task) {
            console.error('无法获取当前任务数据');
            return;
        }

        // 构建提示消息
        const askAIMessage = `您好！我注意到您的代码测试未通过。我可以帮您分析测试结果中的错误原因。
        
**测试结果:**
${testResult.message || '无具体信息'}

**详细信息:**
${(testResult.details || []).join('\n') || '无详细信息'}

您希望我详细解释哪个检查点的错误原因呢？请告诉我您的具体问题，我会针对性地为您解答！`;

        // 在聊天框中显示提示
        chatModule.addMessageToUI('ai', askAIMessage);

        // 记录行为事件
        const topicData = getUrlParam('topic');
        const topicId = topicData && topicData.id ? topicData.id : null;
        if (topicId) {
            tracker.logEvent('ask_ai_requested', {
                topic_id: topicId,
                message: '用户请求AI解释测试错误'
            });
        }
    } catch (error) {
        console.error('触发询问AI功能时出错:', error);
    }
}

// 主程序入口
document.addEventListener('DOMContentLoaded', function () {
    // 设置标题和返回按钮
    setupHeaderTitle('/pages/learning_page.html');
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

// 标记知识点为已学习
function markKnowledgeAsLearned(knowledgeId) {
    try {
        // 从localStorage获取已学习的知识点列表
        let learnedNodes = JSON.parse(localStorage.getItem('learnedNodes') || '[]');

        // 如果还没有学习过这个知识点，添加到列表中
        if (!learnedNodes.includes(knowledgeId)) {
            learnedNodes.push(knowledgeId);
            localStorage.setItem('learnedNodes', JSON.stringify(learnedNodes));
            console.log(`知识点 ${knowledgeId} 已标记为已学习`);
        }
    } catch (error) {
        console.error('标记知识点为已学习时出错:', error);
    }
}

// 获取下一个知识点信息
function getNextKnowledgeInfo(currentTopicId) {
    try {
        // 解析当前知识点ID
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
            const nextTopicId = `${nextChapter}_${nextSection}`;

            // 从知识图谱数据中获取下一个知识点的标题
            const nextKnowledgeLabel = getKnowledgeLabel(nextTopicId);

            if (nextKnowledgeLabel) {
                return {
                    id: nextTopicId,
                    label: nextKnowledgeLabel
                };
            }
        }

        return null;
    } catch (error) {
        console.error('获取下一个知识点信息时出错:', error);
        return null;
    }
}

// 从知识图谱数据中获取知识点的标题
function getKnowledgeLabel(knowledgeId) {
    try {
        // 这里应该从实际的知识图谱数据中获取
        // 为了简化，我们使用一个映射表
        const knowledgeLabels = {
            '1_1': '使用h元素和p元素体验标题与段落',
            '1_2': '应用文本格式(加粗、斜体)',
            '1_3': '构建页面头部结构',
            '2_1': '使用盒子元素进行内容划分',
            '2_2': '创建有序列表',
            '2_3': '创建无序列表',
            '3_1': '文本框与按钮的使用',
            '3_2': '复选框与单选框',
            '3_3': '表单提交机制',
            '4_1': '设置颜色与字体',
            '4_2': '理解盒模型',
            '4_3': '使用 Flex 进行布局',
            '5_1': '插入与管理图片',
            '5_2': '引入音频文件',
            '5_3': '嵌入视频内容',
            '6_1': '按钮点击事件',
            '6_2': '获取用户输入',
            '6_3': '修改页面元素（DOM 操作）'
        };

        return knowledgeLabels[knowledgeId] || knowledgeId;
    } catch (error) {
        console.error('获取知识点标题时出错:', error);
        return knowledgeId;
    }
}

// 显示测试完成弹窗
function showTestCompletionModal(currentTopicId, nextKnowledgeInfo) {
    // 创建弹窗HTML
    const modalHtml = `
        <div id="testCompletionModal" class="modal" style="display: block;">
            <div class="modal-content">
                <div class="modal-header">
                    <iconify-icon icon="mdi:check-circle" width="32" height="32" style="color: #4CAF50;"></iconify-icon>
                    <h2>测试完成！</h2>
                </div>
                <div class="modal-body">
                    <p>您已完成测试，现在可以开始学习"${nextKnowledgeInfo.label}"</p>
                </div>
                <div class="modal-actions">
                    <button id="returnToGraphBtn" class="btn btn-secondary">返回</button>
                    <button id="continueLearningBtn" class="btn btn-primary">确认</button>
                </div>
            </div>
        </div>
    `;

    // 移除已存在的弹窗
    const existingModal = document.getElementById('testCompletionModal');
    if (existingModal) {
        existingModal.remove();
    }

    // 添加新弹窗到页面
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // 绑定事件
    const modal = document.getElementById('testCompletionModal');
    const returnBtn = document.getElementById('returnToGraphBtn');
    const continueBtn = document.getElementById('continueLearningBtn');

    // 返回按钮 - 返回到当前topicId的学习页面
    returnBtn.addEventListener('click', () => {
        modal.remove();
        // 返回到当前topicId对应的学习页面
        navigateTo('/pages/learning_page.html', currentTopicId, true);
    });

    // 确认按钮 - 跳转到下一个学习页面
    continueBtn.addEventListener('click', () => {
        modal.remove();
        navigateTo('/pages/learning_page.html', nextKnowledgeInfo.id, true);
    });

    // 点击背景关闭弹窗
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
            // 返回到当前topicId对应的学习页面
            navigateTo('/pages/learning_page.html', currentTopicId, true);
        }
    });
}

// 检查是否是当前章节的最后一个测试
function isLastTestInCurrentChapter(topicId) {
    try {
        const [chapter, section] = topicId.split('_').map(Number);
        return section === 3; // 每个章节有3个测试，第3个是最后一个
    } catch (error) {
        console.error('检查是否是章节最后一个测试时出错:', error);
        return false;
    }
}

// 从知识点ID获取章节ID
function getChapterFromTopicId(topicId) {
    try {
        const [chapter] = topicId.split('_').map(Number);
        return `chapter${chapter}`;
    } catch (error) {
        console.error('获取章节ID时出错:', error);
        return null;
    }
}

// 标记章节为已完成
function markChapterAsCompleted(chapterId) {
    try {
        // 从localStorage获取已完成的章节
        const completedChapters = JSON.parse(localStorage.getItem('completedChapters') || '[]');

        if (!completedChapters.includes(chapterId)) {
            completedChapters.push(chapterId);
            localStorage.setItem('completedChapters', JSON.stringify(completedChapters));
            console.log(`章节 ${chapterId} 已标记为完成`);
        }
    } catch (error) {
        console.error('标记章节完成时出错:', error);
    }
}

// 获取下一个章节的第一个知识点
function getNextChapterFirstKnowledge(currentChapter) {
    try {
        const currentChapterNum = parseInt(currentChapter.replace('chapter', ''));
        const nextChapterNum = currentChapterNum + 1;

        // 确保不超过最大章节数
        if (nextChapterNum <= 6) {
            const nextChapterFirstTopicId = `${nextChapterNum}_1`;
            const nextChapterFirstLabel = getKnowledgeLabel(nextChapterFirstTopicId);

            if (nextChapterFirstLabel) {
                return {
                    id: nextChapterFirstTopicId,
                    label: nextChapterFirstLabel,
                    chapter: `chapter${nextChapterNum}`
                };
            }
        }

        return null;
    } catch (error) {
        console.error('获取下一个章节第一个知识点时出错:', error);
        return null;
    }
}

// 显示章节完成弹窗
function showChapterCompletionModal(completedChapter, nextChapterFirstKnowledge) {
    // 创建弹窗HTML
    const modalHtml = `
        <div id="chapterCompletionModal" class="modal" style="display: block;">
            <div class="modal-content">
                <div class="modal-header">
                    <iconify-icon icon="mdi:trophy" width="32" height="32" style="color: #FFD700;"></iconify-icon>
                    <h2>章节完成！</h2>
                </div>
                <div class="modal-body">
                    <p>您已完成测试，现在可以开始学习"${nextChapterFirstKnowledge.label}"</p>
                </div>
                <div class="modal-actions">
                    <button id="returnToGraphBtn" class="btn btn-secondary">返回</button>
                    <button id="continueLearningBtn" class="btn btn-primary">确认</button>
                </div>
            </div>
        </div>
    `;

    // 移除已存在的弹窗
    const existingModal = document.getElementById('chapterCompletionModal');
    if (existingModal) {
        existingModal.remove();
    }

    // 添加新弹窗到页面
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // 绑定事件
    const modal = document.getElementById('chapterCompletionModal');
    const returnBtn = document.getElementById('returnToGraphBtn');
    const continueBtn = document.getElementById('continueLearningBtn');

    // 返回按钮 - 返回到当前topicId的学习页面
    returnBtn.addEventListener('click', () => {
        modal.remove();
        // 获取当前topicId
        const topicData = getUrlParam('topic');
        const currentTopicId = topicData && topicData.id ? topicData.id : null;
        if (currentTopicId) {
            navigateTo('/pages/learning_page.html', currentTopicId, true);
        } else {
            window.location.href = '/pages/index.html';
        }
    });

    // 确认按钮 - 跳转到下一个章节的第一个学习页面
    continueBtn.addEventListener('click', () => {
        modal.remove();
        navigateTo('/pages/learning_page.html', nextChapterFirstKnowledge.id, true);
    });

    // 点击背景关闭弹窗
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
            // 获取当前topicId
            const topicData = getUrlParam('topic');
            const currentTopicId = topicData && topicData.id ? topicData.id : null;
            if (currentTopicId) {
                navigateTo('/pages/learning_page.html', currentTopicId, true);
            } else {
                window.location.href = '/pages/index.html';
            }
        }
    });
}

// 绑定解题思路按钮事件
function bindProblemSolvingHintButton(topicId) {
    const hintButton = document.getElementById('problem-solving-hint-btn');
    if (hintButton) {
        hintButton.addEventListener('click', () => {
            // 触发解题思路提示
            triggerProblemSolvingHint(topicId);
        });
    }
}

// 触发解题思路提示
async function triggerProblemSolvingHint(topicId) {
    try {
        // 获取当前任务数据
        const task = window.currentTaskData;
        if (!task) {
            console.error('无法获取当前任务数据');
            return;
        }

        // 获取对话历史
        const conversationHistory = chatModule.getConversationHistory();

        // 构建提示消息
        const hintMessage = `您好！我注意到您点击了"给点灵感"按钮。我可以为您提供一些关于这道题的解题思路和关键知识点。

**题目要求：**
${task.description_md || '暂无描述'}

**您希望我提供哪方面的帮助？**
1. 整体解题思路分析
2. 关键知识点讲解
3. 代码实现要点
4. 常见错误及调试建议

请告诉我您的需求，我会针对性地为您解答！`;

        // 在聊天框中显示提示
        chatModule.addMessageToUI('ai', hintMessage);

        // 记录行为事件
        tracker.logEvent('problem_solving_hint_requested', {
            topic_id: topicId,
            message: '用户请求解题思路'
        });
    } catch (error) {
        console.error('触发解题思路提示时出错:', error);
    }
}
