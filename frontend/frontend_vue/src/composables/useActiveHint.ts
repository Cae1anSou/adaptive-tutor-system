import { ref, watch, onMounted, onUnmounted } from 'vue';
import { logBehaviorBehaviorLogPost } from '@/api/behavior';
import { useEventListener } from '@vueuse/core';
import { useUserStore } from '@/stores/user';

// 类型定义
export interface ActiveHintConfig {
    idleThreshold?: number; // 空闲阈值 (ms)
    hintDelayAfterIdle?: number; // 进入空闲后的提示延迟 (ms)
    consecutiveEditThreshold?: number; // 连续编辑触发提示的阈值
}

export interface HintEventDetail {
    type: 'idle' | 'struggle' | 'frustration';
    message: string;
    context?: any;
}

export function useActiveHint(
    editors: {
        html: any; // Ref<string>
        css: any;
        js: any;
    },
    topicId: string,
    onHintTriggered: (detail: HintEventDetail) => void,
    config: ActiveHintConfig = {}
) {
    const userStore = useUserStore();

    // 默认配置
    const {
        idleThreshold = 60000,
        hintDelayAfterIdle = 15000,
        consecutiveEditThreshold = 5,
    } = config;

    // --- 状态变量 ---
    const lastActivityTime = ref(Date.now());
    const idleTimer = ref<any>(null);
    const hintTimer = ref<any>(null);
    const isIdle = ref(false);
    const idleStartTime = ref<number | null>(null);

    // 代码编辑状态监控
    const editStates = {
        html: createEditorState(),
        css: createEditorState(),
        js: createEditorState(),
    };

    function createEditorState() {
        return {
            lastContent: '',
            consecutiveEdits: 0,
            lastMeaningfulEditTime: 0,
            history: [] as any[], // 简单记录历史，用于分析
        };
    }

    // --- 1. 空闲监测 (Idle Monitor) ---

    const resetIdleTimer = () => {
        const now = Date.now();

        // 如果之前是空闲状态，记录空闲结束事件
        if (isIdle.value && idleStartTime.value) {
            logEvent('user_idle', {
                duration_ms: now - idleStartTime.value,
                timestamp_start: new Date(idleStartTime.value).toISOString(),
                timestamp_end: new Date(now).toISOString(),
                was_focused: !document.hidden,
            });
        }

        lastActivityTime.value = now;
        isIdle.value = false;
        idleStartTime.value = null;

        clearTimeout(idleTimer.value);
        clearTimeout(hintTimer.value);

        // 重新开始空闲计时
        idleTimer.value = setTimeout(() => {
            enterIdleState();
        }, idleThreshold);
    };

    const enterIdleState = () => {
        isIdle.value = true;
        idleStartTime.value = Date.now();

        // 进入空闲后，再经过 hintDelayAfterIdle 触发提示
        hintTimer.value = setTimeout(() => {
            triggerIdleHint();
        }, hintDelayAfterIdle);
    };

    const triggerIdleHint = () => {
        // 再次确认是否真的空闲
        if (!isIdle.value) return;

        // 随机提示语
        const messages = [
            '已经有一会儿没有操作了，需要我给点思路吗？请告诉我你的疑惑',
            '卡住了吗？要不要我给几个提示。请告诉你的问题吧',
            '来问问我给你些指导，帮你重新进入状态？',
            '看你有一会儿没操作了，遇到困难可以问问我哦',
            '是有什么不理解的地方吗，告诉我问题，ai助教来助阵！'
        ];
        const message = messages[Math.floor(Math.random() * messages.length)];

        onHintTriggered({
            type: 'idle',
            message
        });

        logEvent('idle_hint_displayed', {
            message,
            idle_ms: Date.now() - (idleStartTime.value || 0)
        });
    };


    // --- 2. 代码挣扎监测 (Code Struggle Monitor) ---
    // 监听三个编辑器的变化

    const handleCodeChange = (type: 'html' | 'css' | 'js', newVal: string) => {
        // 只要有代码输入，就算作活动，重置空闲计时器
        resetIdleTimer();

        const state = editStates[type];
        const oldVal = state.lastContent;

        // 简单判断是否有意义修改 (例如长度变化超过一定阈值，这里简化处理，只要不为空且变化了就算)
        // 实际行为追踪里的逻辑比较复杂，这里做适度简化，核心是捕获“反复修改”

        const isMeaningful = Math.abs(newVal.length - oldVal.length) > 2; // 举例：变化超过2个字符

        if (isMeaningful) {
            state.consecutiveEdits++;
            state.lastMeaningfulEditTime = Date.now();
        } else {
            // 如果只是微小改动，不重置计数，但也不增加？或者根据时间判断断层
            // 这里可以加入防抖逻辑，避免打字过程中的频繁触发
        }

        state.lastContent = newVal;

        // 检查阈值
        if (state.consecutiveEdits >= consecutiveEditThreshold) {
            // 触发挣扎提示
            triggerStruggleHint(type, state.consecutiveEdits);
            // 重置计数，避免一直提示
            state.consecutiveEdits = 0;
        }
    };

    // 生成相应watcher
    watch(editors.html, (val) => handleCodeChange('html', val));
    watch(editors.css, (val) => handleCodeChange('css', val));
    watch(editors.js, (val) => handleCodeChange('js', val));


    const triggerStruggleHint = (editorType: string, count: number) => {
        const editorNames: Record<string, string> = { html: 'HTML', css: 'CSS', js: 'JavaScript' };
        const name = editorNames[editorType] || editorType;

        const message = `我注意到您在 ${name} 代码中反复修改了 ${count} 次, 是不是遇到了什么具体的问题？可以直接告诉我，让我来帮您分析解决～`;

        onHintTriggered({
            type: 'struggle',
            message,
            context: { editorType, count }
        });

        // 记录“问题事件”到后端
        logEvent('coding_problem', {
            editor: editorType,
            consecutive_edits: count,
            severity: 'medium'
        });
    };


    // --- 3. 辅助函数：日志上报 ---
    const logEvent = (eventType: string, eventData: any = {}) => {
        const participantId = userStore.participantId;
        if (!participantId) return;

        const payload = {
            participant_id: participantId,
            event_type: eventType as any, // 强制转换以匹配 Type
            event_data: {
                ...eventData,
                topic_id: topicId // 自动带上当前topic
            },
            timestamp: new Date().toISOString()
        };

        // 调用API发送
        logBehaviorBehaviorLogPost(payload).catch(err => {
            console.warn('[ActiveHint] 行为日志上报失败', err);
        });
    };


    // --- 生命周期 ---
    onMounted(() => {
        // 绑定全局活动监听
        const events = ['mousemove', 'keydown', 'click', 'scroll'];
        events.forEach(evt => useEventListener(window, evt, resetIdleTimer));

        // 初始化计时
        resetIdleTimer();
    });

    onUnmounted(() => {
        clearTimeout(idleTimer.value);
        clearTimeout(hintTimer.value);
    });

    // --- 暴露给外部的方法 ---
    return {
        // 可以在提交失败时调用此方法增加挫败感计数（如果需要的话，目前在 TestPage 维护）
        logEvent
    };
}
