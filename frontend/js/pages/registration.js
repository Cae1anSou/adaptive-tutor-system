// frontend/js/pages/registration.js
import { saveParticipantId } from '../modules/session.js';
import { initializeConfig } from '../modules/config.js';
import { setupHeaderTitle, navigateTo } from '../modules/navigation.js';
import apiClient from '../api_client.js';

const GENERATED_COURSE_STORAGE_KEY = 'generated_course_plan';

const registrationState = {
    isGenerating: false,
    isCourseReady: false,
    generatedSignature: '',
    participantId: null,
    generatedCourse: null
};

document.addEventListener('DOMContentLoaded', async () => {
    await initializeConfig();
    setupHeaderTitle('/index.html');

    const startButton = document.getElementById('start-button');
    const nicknameInput = document.getElementById('nickname-input');
    const themeSelector = document.getElementById('theme-selector');
    const goalInput = document.getElementById('goal-input');
    const paceSelector = document.getElementById('pace-selector');
    const coursePreview = document.getElementById('course-preview');
    const courseTitle = document.getElementById('course-title');
    const courseSummary = document.getElementById('course-summary');
    const courseOutline = document.getElementById('course-outline');
    const regenerateButton = document.getElementById('regenerate-button');
    const generationStatus = document.getElementById('generation-status');
    const generationTitleText = document.getElementById('generation-title-text');
    const generationProgressFill = document.getElementById('generation-progress-fill');
    const generationProgressText = document.getElementById('generation-progress-text');
    const generationLog = document.getElementById('generation-log');
    const generationSteps = Array.from(document.querySelectorAll('#generation-steps li'));

    resetGenerationUI();

    const handleInputChange = () => {
        if (registrationState.isCourseReady && registrationState.generatedSignature !== getCurrentInputSignature()) {
            clearGeneratedCourse();
            resetGenerationUI();
        }
        checkFormValid();
    };

    nicknameInput?.addEventListener('input', handleInputChange);
    nicknameInput?.addEventListener('blur', validateNickname);
    themeSelector?.addEventListener('change', handleInputChange);
    goalInput?.addEventListener('input', handleInputChange);
    paceSelector?.addEventListener('change', handleInputChange);

    startButton?.addEventListener('click', async () => {
        if (registrationState.isGenerating) return;

        if (registrationState.isCourseReady && registrationState.generatedCourse) {
            sessionStorage.setItem(GENERATED_COURSE_STORAGE_KEY, JSON.stringify(registrationState.generatedCourse));
            navigateTo('/pages/learning_page.html', registrationState.generatedCourse.firstTopicId || '1_1', true);
            return;
        }

        const nickname = nicknameInput?.value.trim() || '';
        const theme = themeSelector?.value || '';
        const goal = goalInput?.value.trim() || '';
        const pace = paceSelector?.value || 'standard';

        if (!nickname) {
            showError('请输入学习昵称');
            nicknameInput?.focus();
            return;
        }

        if (!theme) {
            showError('请选择学习主题');
            themeSelector?.focus();
            return;
        }

        registrationState.isGenerating = true;
        startButton.disabled = true;
        startButton.innerHTML = '<iconify-icon icon="mdi:loading" width="20" height="20" class="spin"></iconify-icon> AI 正在生成课程...';
        showGenerationStatus();

        try {
            const generationDurationMs = 7000 + Math.floor(Math.random() * 4000);
            const generationPromise = runGenerationSimulation({
                durationMs: generationDurationMs,
                generationTitleText,
                generationProgressFill,
                generationProgressText,
                generationLog,
                generationSteps,
                nickname,
                theme
            });

            const sessionPromise = registrationState.participantId
                ? Promise.resolve(registrationState.participantId)
                : ensureSession(nickname, theme);

            const [, participantId] = await Promise.all([generationPromise, sessionPromise]);
            registrationState.participantId = participantId;

            const generatedCourse = generateMockCoursePlan({ nickname, theme, goal, pace });

            registrationState.generatedCourse = generatedCourse;
            registrationState.generatedSignature = getCurrentInputSignature();
            registrationState.isCourseReady = true;

            renderCoursePreview(generatedCourse);

            if (coursePreview) {
                coursePreview.hidden = false;
            }
            if (generationStatus) {
                generationStatus.hidden = true;
            }

            startButton.disabled = false;
            startButton.innerHTML = '<iconify-icon icon="mdi:play" width="20" height="20"></iconify-icon> 开始学习此课程';
        } catch (error) {
            console.error('课程生成流程失败:', error);
            showError(error.message || '课程生成失败，请稍后重试');
            resetGenerationUI();
            checkFormValid();
        } finally {
            registrationState.isGenerating = false;
        }
    });

    regenerateButton?.addEventListener('click', async () => {
        clearGeneratedCourse();
        resetGenerationUI();
        checkFormValid();
        startButton?.click();
    });

    function renderCoursePreview(course) {
        if (courseTitle) {
            courseTitle.textContent = course.title;
        }
        if (courseSummary) {
            courseSummary.textContent = course.summary;
        }
        if (courseOutline) {
            courseOutline.innerHTML = '';
            course.modules.forEach((item) => {
                const li = document.createElement('li');
                li.textContent = `${item.title}：${item.focus}`;
                courseOutline.appendChild(li);
            });
        }
    }

    function resetGenerationUI() {
        if (coursePreview) {
            coursePreview.hidden = true;
        }
        if (generationStatus) {
            generationStatus.hidden = true;
        }
        resetGenerationVisualState();
        if (startButton) {
            startButton.innerHTML = '<iconify-icon icon="mdi:sparkles" width="20" height="20"></iconify-icon> 生成课程';
        }
    }

    function checkFormValid() {
        const nickname = nicknameInput?.value.trim() || '';
        const theme = themeSelector?.value || '';
        const isValid = nickname.length >= 2 && Boolean(theme);
        if (startButton) {
            startButton.disabled = registrationState.isGenerating || !isValid;
        }
    }

    function validateNickname() {
        const nickname = nicknameInput?.value.trim() || '';
        if (nickname && nickname.length < 2) {
            showError('昵称至少需要2个字符');
            return false;
        }
        return true;
    }

    function getCurrentInputSignature() {
        const nickname = nicknameInput?.value.trim() || '';
        const theme = themeSelector?.value || '';
        const goal = goalInput?.value.trim() || '';
        const pace = paceSelector?.value || 'standard';
        return `${nickname}|${theme}|${goal}|${pace}`;
    }

    function clearGeneratedCourse() {
        registrationState.isCourseReady = false;
        registrationState.generatedCourse = null;
        registrationState.generatedSignature = '';
        sessionStorage.removeItem(GENERATED_COURSE_STORAGE_KEY);
    }

    function showGenerationStatus() {
        if (coursePreview) {
            coursePreview.hidden = true;
        }
        if (generationStatus) {
            generationStatus.hidden = false;
        }
        resetGenerationVisualState();
    }

    function resetGenerationVisualState() {
        if (generationTitleText) {
            generationTitleText.textContent = '正在初始化生成引擎...';
        }
        if (generationProgressFill) {
            generationProgressFill.style.width = '0%';
        }
        if (generationProgressText) {
            generationProgressText.textContent = '0%';
        }
        if (generationLog) {
            generationLog.textContent = '';
        }
        generationSteps.forEach((stepElement) => {
            stepElement.classList.remove('active', 'done');
        });
    }

    checkFormValid();
});

async function ensureSession(nickname, theme) {
    const participantId = generateParticipantId(nickname);
    const result = await apiClient.postWithoutAuth('/session/initiate', {
        participant_id: participantId,
        nickname: nickname,
        theme: theme
    });

    if (result.code !== 200 && result.code !== 201) {
        throw new Error(result.message || '启动失败，请重试');
    }

    const resolvedId = result?.data?.participant_id || participantId;
    saveParticipantId(resolvedId);
    return resolvedId;
}

function generateParticipantId(nickname) {
    const cleanNickname = nickname.replace(/[^\w\u4e00-\u9fa5]/g, '').trim();
    return cleanNickname || `user_${Date.now()}`;
}

function generateMockCoursePlan({ nickname, theme, goal, pace }) {
    const template = getCourseTemplate(theme);

    const paceLabel = {
        light: '轻松节奏',
        standard: '标准节奏',
        intensive: '冲刺节奏'
    }[pace] || '标准节奏';

    const modules = template.modules.map((module, index) => ({
        id: `M${index + 1}`,
        title: module.title,
        focus: module.focus
    }));

    return {
        title: `${nickname}的${template.courseName}`,
        summary: goal
            ? `学习目标：${goal}。本课程采用${paceLabel}，围绕“${template.projectGoal}”逐步展开。`
            : `本课程采用${paceLabel}，将带你从基础语法到页面结构，完成“${template.projectGoal}”实践任务。`,
        modules,
        firstTopicId: '1_1',
        theme,
        pace,
        generatedAt: new Date().toISOString()
    };
}

async function runGenerationSimulation({
    durationMs,
    generationTitleText,
    generationProgressFill,
    generationProgressText,
    generationLog,
    generationSteps,
    nickname,
    theme
}) {
    const themeLabelMap = {
        pets: '萌宠乐园',
        shopping: '时尚购物',
        music: '影音娱乐'
    };
    const themeLabel = themeLabelMap[theme] || '通用主题';

    const stepConfigs = [
        {
            title: '正在收集学习者画像...',
            logs: [
                `已识别昵称特征：${nickname}`,
                `已读取主题偏好：${themeLabel}`,
                '正在构建学习者起点画像'
            ]
        },
        {
            title: '正在分析学习目标与节奏...',
            logs: [
                '正在匹配学习目标关键词',
                '正在估算认知负荷与学习时长',
                '已生成节奏与难度初稿'
            ]
        },
        {
            title: '正在匹配知识图谱节点...',
            logs: [
                '正在检索可用知识节点',
                '已关联核心知识点与先修关系',
                '正在优化章节依赖路径'
            ]
        },
        {
            title: '正在编排课程结构...',
            logs: [
                '正在生成模块结构与任务顺序',
                '正在注入示例驱动练习点',
                '已完成模块草案拼装'
            ]
        },
        {
            title: '正在校验课程质量...',
            logs: [
                '正在检测难度跃迁是否平滑',
                '正在执行课程完整性检查',
                '正在生成最终可学习版本'
            ]
        }
    ];

    const minTick = 200;
    const maxTick = 340;
    const stepCount = stepConfigs.length;
    const stepDuration = Math.max(900, Math.floor(durationMs / stepCount));
    const startedAt = Date.now();
    let currentProgress = 0;

    for (let stepIndex = 0; stepIndex < stepCount; stepIndex++) {
        const stepConfig = stepConfigs[stepIndex];
        markGenerationSteps(generationSteps, stepIndex);

        if (generationTitleText) {
            generationTitleText.textContent = stepConfig.title;
        }

        let logCursor = 0;
        const stepStart = Date.now();

        while (Date.now() - stepStart < stepDuration) {
            const elapsed = Date.now() - startedAt;
            const targetProgress = Math.min(97, Math.floor((elapsed / durationMs) * 100));
            currentProgress = Math.max(currentProgress, targetProgress);

            if (generationProgressFill) {
                generationProgressFill.style.width = `${currentProgress}%`;
            }
            if (generationProgressText) {
                generationProgressText.textContent = `${currentProgress}%`;
            }

            if (generationLog && stepConfig.logs.length > 0) {
                generationLog.textContent = stepConfig.logs[logCursor % stepConfig.logs.length];
                logCursor += 1;
            }

            const tick = minTick + Math.floor(Math.random() * (maxTick - minTick + 1));
            await wait(tick);
        }
    }

    markGenerationSteps(generationSteps, stepCount);
    if (generationProgressFill) {
        generationProgressFill.style.width = '100%';
    }
    if (generationProgressText) {
        generationProgressText.textContent = '100%';
    }
    if (generationTitleText) {
        generationTitleText.textContent = '课程生成完成，正在准备学习入口...';
    }
    if (generationLog) {
        generationLog.textContent = '课程方案生成成功，已完成可学习版本封装。';
    }
    await wait(520);
}

function markGenerationSteps(stepElements, activeStepIndex) {
    stepElements.forEach((stepElement, index) => {
        stepElement.classList.remove('active', 'done');
        if (index < activeStepIndex) {
            stepElement.classList.add('done');
        } else if (index === activeStepIndex) {
            stepElement.classList.add('active');
        }
    });
}

function getCourseTemplate(theme) {
    const templates = {
        pets: {
            courseName: '萌宠乐园网页创作课',
            projectGoal: '宠物领养展示页',
            modules: [
                { title: '模块 1 · 页面结构搭建', focus: '掌握常见 HTML 结构标签与语义布局' },
                { title: '模块 2 · 宠物信息卡片', focus: '用列表与容器组织宠物档案内容' },
                { title: '模块 3 · 表格与对比展示', focus: '用表格展示宠物特征和领养条件' },
                { title: '模块 4 · 页面优化与实战', focus: '完成可演示的宠物主题网页作品' }
            ]
        },
        shopping: {
            courseName: '时尚购物网页创作课',
            projectGoal: '商品橱窗展示页',
            modules: [
                { title: '模块 1 · 商城页面骨架', focus: '构建导航、主区和商品分区结构' },
                { title: '模块 2 · 商品卡片排版', focus: '用块级元素组织商品信息与文案' },
                { title: '模块 3 · 价格参数表格', focus: '用表格展示价格与规格对比' },
                { title: '模块 4 · 页面优化与实战', focus: '完成可演示的购物主题网页作品' }
            ]
        },
        music: {
            courseName: '影音娱乐网页创作课',
            projectGoal: '音乐推荐展示页',
            modules: [
                { title: '模块 1 · 页面内容分区', focus: '掌握音乐网站常见页面结构组织' },
                { title: '模块 2 · 专辑与歌单卡片', focus: '构建专辑、歌单和简介信息块' },
                { title: '模块 3 · 榜单表格呈现', focus: '使用表格展示歌曲排行和评分' },
                { title: '模块 4 · 页面优化与实战', focus: '完成可演示的音乐主题网页作品' }
            ]
        }
    };
    return templates[theme] || templates.pets;
}

function wait(ms) {
    return new Promise((resolve) => {
        window.setTimeout(resolve, ms);
    });
}

function showError(message) {
    alert('❌ ' + message);
}

window.addEventListener('pageshow', () => {
    const startButton = document.getElementById('start-button');
    const coursePreview = document.getElementById('course-preview');
    const generationStatus = document.getElementById('generation-status');
    if (!startButton) return;

    if (coursePreview) {
        coursePreview.hidden = true;
    }
    if (generationStatus) {
        generationStatus.hidden = true;
    }

    registrationState.isGenerating = false;
    registrationState.isCourseReady = false;
    registrationState.generatedCourse = null;
    registrationState.generatedSignature = '';
    sessionStorage.removeItem(GENERATED_COURSE_STORAGE_KEY);

    startButton.innerHTML = '<iconify-icon icon="mdi:sparkles" width="20" height="20"></iconify-icon> 生成课程';

    const nicknameInput = document.getElementById('nickname-input');
    const themeSelector = document.getElementById('theme-selector');
    const nickname = nicknameInput?.value.trim() || '';
    const theme = themeSelector?.value || '';
    startButton.disabled = nickname.length < 2 || !theme;
});
