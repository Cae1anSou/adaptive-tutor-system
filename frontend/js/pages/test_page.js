import {createLivePreview} from '../modules/live_preview.js'; // 假设该模块已存在
import {getLocalParticipantId} from '../services/session_service.js'; // 导入会话管理模块

// ... 在获取到数据并设置好编辑器后 ...
// TODO: cxz 需要获取HTML中的DOM
const editors = {html: htmlEditor, css: cssEditor, js: jsEditor};
const iframe = document.getElementById('preview-iframe');
const livePreviewManager = createLivePreview(editors, iframe);

// 触发一次初始渲染
// TODO: cxz 需要实现这个逻辑
livePreviewManager.triggerUpdate();

const submitButton = document.getElementById('submit-button');
const topicId = new URLSearchParams(window.location.search).get('topic');

const participant_id = getLocalParticipantId(); // 从localStorage获取用户ID

submitButton.addEventListener('click', async () => {
    submitButton.disabled = true;
    submitButton.textContent = '批改中...';

    // 准备请求体
    const submissionData = {
        participant_id: participant_id, // 用户ID，从session模块获取
        topic_id: topicId,
        code: {
            html: htmlEditor.getValue(),
            css: cssEditor.getValue(),
            js: jsEditor.getValue()
        }
    };


    try {
        // 调用封装好的API客户端
        const result = await window.apiClient.post('/submit-test', submissionData);

        if (result.code === 200) {
            const testResult = result.data;
            // TODO: cxz 通过一个美观的模态框或alert显示结果
            displayTestResult(testResult);

            // TODO: 如果通过，可以自动更新本地进度并跳转
            if (testResult.passed) {
                // TODO: cxz (可选) 更新本地状态，然后跳转回知识图谱
                alert("测试完成！即将跳转回到知识图谱界面")

                setTimeout(() => {
                    window.location.href = '/knowledge_graph.html';
                }, 3000);
            }
        } else {
            throw new Error(result.message);
        }

    } catch (error) {
        // TODO: cxz  ... 错误处理 ...
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = '提交';
    }
});

function displayTestResult(result) {
    // TODO: cxz 这里到时候需要获取HTML中的对话框的元素
    let message = result.passed ? '✅ 恭喜！所有测试点都通过了！' : '❌ 很遗憾，部分测试点未通过。';
    if (result.details && result.details.length > 0) {
        message += '\n\n详细信息:\n' + result.details.join('\n');
    }
    alert(message); // 在实际项目中会用一个漂亮的模态框代替
}