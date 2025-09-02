// frontend/js/modules/behavior_tracker.js
/**
 * BehaviorTracker 前端行为追踪模块
 *
 * 目标：
 * - 捕获 TDD-II-07 中规定的关键事件：
 *   code_edit（Monaco 编辑器防抖 2s）、ai_help_request（立即）、test_submission（立即，包含 code）、dom_element_select（立即，iframe 支持）、user_idle（60s）、page_focus_change（visibility）
 * - 组装标准化 payload 并可靠发送到后端 /api/v1/behavior/log
 * - 【已改】统一使用 fetch(..., { keepalive: true, credentials: 'omit' })，彻底不带 Cookie
 *
 * 注意：
 * - 本文件不修改现有 HTML。脚本提供自动初始化尝试（initAuto），但更可靠的方式是：在页面创建 Monaco 编辑器后显式调用 tracker.initEditors(...) 与 tracker.initTestActions(...)
 * - TODO中表示需要我们根据实际项目调整或确认的点（Monaco 编辑器实例的暴露方式等）
 */

import debounce from 'https://cdn.jsdelivr.net/npm/lodash-es@4.17.21/debounce.js';
import { getParticipantId } from './session.js';

class BehaviorTracker {
  constructor() {
    // code_edit 防抖时长（ms）
    this.debounceMs = 2000;
    this.idleTimer = null;
    // ✅ 添加标志位，防止多次绑定焦点与闲置监听器
    this._focusAndIdleBound = false;
    this._enabledEvents = {};
    this._elementClickBound = false;

    this.hintConfig = {
      hintThreshold: 5, // 增加触发提示的连续修改次数阈值到5次
      cooldownPeriod: 60000, // 增加提示冷却时间到60秒
      lastHintTime: 0 // 上次提示时间
    };
    // 智能代码监控配置
    this.codeMonitoringConfig = {
      minChangeThreshold: 15, // 增加最小触发字符数变化到15个字符，避免小修改触发
      meaningfulEditTimeout: 5000, // 增加有意义编辑的超时时间到5秒
      problemDetectionThreshold: 5, // 增加问题检测阈值到5次连续修改，减少误判
      maxHistoryLength: 100 // 最大历史记录长度
    };
    // 代码监控状态
    this.codeMonitorStates = {
      html: this._createEditorState(),
      css: this._createEditorState(),
      js: this._createEditorState()
    };

    this.problemEvents = []; // 记录用户遇到问题的次数
    this.significantEdits = []; // 有意义的重要编辑记录

    // —— page_click 批量相关（必须初始化）——
    this._clickCfg = null;
    this._clickBatch = [];
    this._clickBatchTimer = null;

    // —— Idle 追踪 & 提示 ——
    // 最近一次活动时间、一次空闲会话开始时间
    this.idleThreshold = 4000; // 进入空闲判定阈值（ms）
    this._lastActivityTs = Date.now();
    this._idleStartTs = null;

    // 计时器
    this._idleHintTimer = null;

    // ---- Idle 追踪（真实空闲）----
    this._lastActivityTs = Date.now(); // 最近一次活动时间
    this._idleStartTs = null;          // 本次空闲起点（= 上一次活动时间）
    this._idleMsgIdx = 0;              // 空闲提示轮换索引
    this.idleHintConfig = {
      hintAfterMs: 3000,  // 空闲多久后提示（默认 3s）
      cooldownMs: 18000,  // 提示冷却（默认 3 分钟）TODO：暂时没有用，一次空闲只提醒一次，每次重新空闲都会再提醒。
      lastHintTs: 0,
      messages: [
        '已经有一会儿没有操作了，需要我给点思路吗？请告诉我你的疑惑',
        '卡住了吗？要不要我给几个提示。请告诉你的问题吧',
        '来问问我给你些指导，帮你重新进入状态？',
        '看你有一会儿没操作了，遇到困难可以问问我哦',
        '是有什么不理解的地方吗，告诉我问题，ai助教来助阵！'
      ]
    };
  }

  // 创建编辑器状态对象
  _createEditorState() {
    return {
      lastContent: '',
      lastLength: 0,
      lastMeaningfulEdit: 0,
      isDeleting: false,
      deleteStartTime: 0,
      deleteStartLength: 0,
      consecutiveEdits: 0,// 连续修改次数
      editBuffer: []
    };
  }

  // 触发问题事件（用于UI监听）
  _triggerProblemEvent(problemData) {
    const event = new CustomEvent('codingProblemDetected', {
      detail: problemData
    });
    document.dispatchEvent(event);
  }



  init(config = {}) {
    this._enabledEvents = config;
    // 允许外部覆盖空闲提示配置
    if (config.idleHintConfig) {
      this.idleHintConfig = { ...this.idleHintConfig, ...config.idleHintConfig };
    }
    if (config.user_idle) this.initIdleAndFocus(config.idleThreshold);
    if (config.code_edit && window.editors) this.initEditors(window.editors);
    if (config.ai_help_request) this.initChat('send-message', '#user-message');
    if (config.test_submission && window.editors) this.initTestActions('run-button', 'submit-button', window.editors, () => window.currentTopicId || null);
    if (config.dom_element_select) this.initDOMSelector('startSelector', 'stopSelector', 'element-selector-iframe');
    // ✅ 挂上 page_click（你之前缺这行，导致完全没监听）
    if (config.page_click) {
      this.initPageClick(config.page_click_options || {});
    }
    // 兼容老开关（如果外部传的是 element_clicks）
    if (!config.page_click && config.element_clicks) {
      this.initPageClick(config.element_click_options || {});
    }
  }

  // -------------------- 核心发送函数 --------------------
  // 使用 window.apiClient.postWithoutAuth 发送请求到后端
  _sendPayload(payload) {
    // 检查 window.apiClient 是否存在
    if (typeof window.apiClient === 'undefined' || typeof window.apiClient.postWithoutAuth !== 'function') {
      console.error('[BehaviorTracker] window.apiClient.postWithoutAuth 不可用');
      return;
    }

    // 使用 apiClient 发送 POST 请求
    window.apiClient.postWithoutAuth('/behavior/log', payload)
      .catch(err => {
        console.warn('[BehaviorTracker] 发送日志失败：', err);
      });
  }

  // 公共上报接口：组装标准 payload 并发送
  logEvent(eventType, eventData = {}) {
    // 获取 participant_id（从 session.js 或 window 取）
    let participant_id = null;
    try {
      if (typeof getParticipantId === 'function') {
        participant_id = getParticipantId();
      }
    } catch (e) {
      // ignore
    }
    // 兜底：如果页面在全局暴露 participantId，也可取之
    if (!participant_id && window && window.participantId) {
      participant_id = window.participantId;
    }
    if (!participant_id) {
      // 如果没有 participant_id，则按 TDD-II-07 的说明不追踪；可选择缓冲但当前选择跳过
      console.warn('[BehaviorTracker] 无 participant_id，跳过事件：', eventType);
      return;
    }

    const payload = {
      participant_id,
      event_type: eventType,
      event_data: eventData,
      timestamp: new Date().toISOString()
    };

    this._sendPayload(payload);
  }

  // -------------------- 智能代码监控核心功能 --------------------
  /**
   * 初始化智能代码改动监控
   */
  initSmartCodeTracking(editors) {
    if (!editors) {
      console.warn('[BehaviorTracker] 无编辑器实例，无法初始化智能代码监控');
      return;
    }

    try {
      // 为每个编辑器设置智能监控
      Object.keys(editors).forEach(editorType => {
        if (editors[editorType] && typeof editors[editorType].onDidChangeModelContent === 'function') {
          editors[editorType].onDidChangeModelContent(() => {
            this._smartRecordCodeChange(editorType, editors[editorType].getValue());
          });
        }
      });

      console.log('[BehaviorTracker] 智能代码监控已初始化');

    } catch (e) {
      console.warn('[BehaviorTracker] 初始化智能代码监控时出错：', e);
    }
  }

  /**
     * 智能记录代码改动
     */
  _smartRecordCodeChange(editorType, currentContent) {
    const state = this.codeMonitorStates[editorType];
    const currentLength = currentContent.length;
    const previousLength = state.lastLength; // 保存变化前的长度
    const lengthChange = currentLength - previousLength;// 基于变化前的长度

    // 更新最后内容
    state.lastContent = currentContent;
    state.lastLength = currentLength;

    const now = Date.now();
    const timeSinceLastEdit = now - state.lastMeaningfulEdit;

    // 判断编辑类型，传递previousLength
    if (lengthChange < 0) {
      this._handleDeletion(editorType, state, now, previousLength);
    } else if (lengthChange > 0) {
      this._handleAddition(editorType, state, lengthChange, currentLength, now, timeSinceLastEdit, previousLength);
    }
    // 注意：当lengthChange == 0时不更新lastMeaningfulEdit，避免格式调整等无实质内容变化的操作被计为活动
  }
  /**
   * 处理删除操作
   */
  _handleDeletion(editorType, state, timestamp, previousLength) {
    if (!state.isDeleting) {
      state.isDeleting = true;
      state.deleteStartTime = timestamp;
      state.deleteStartLength = previousLength; // 使用变化前的长度作为开始长度
    }
  }

  /**
   * 处理增加操作
   */
  _handleAddition(editorType, state, lengthChange, currentLength, timestamp, timeSinceLastEdit, previousLength) {
    if (state.isDeleting) {
      // 之前是删除状态，现在是增加 → 完成一个修改周期
      state.consecutiveEdits++;
      state.lastMeaningfulEdit = timestamp;
      this._completeEditCycle(editorType, state, timestamp, currentLength, previousLength); // 传递previousLength
    } else if (lengthChange >= this.codeMonitoringConfig.minChangeThreshold &&
      timeSinceLastEdit > this.codeMonitoringConfig.meaningfulEditTimeout) {
      // 有意义的正向编辑
      state.consecutiveEdits++;
      state.lastMeaningfulEdit = timestamp;
      this._recordMeaningfulEdit(editorType, 'addition', lengthChange, currentLength, timestamp);
    } else if (lengthChange > 0) {
      // 即使不是有意义的编辑，也要更新活动时间以表明用户仍在编辑
      // 但不增加连续编辑计数
      state.lastMeaningfulEdit = timestamp;
    }
  }

  /**
   * 完成编辑周期（删除后重新编写）
   */
  _completeEditCycle(editorType, state, timestamp, finalLength, deleteEndLength) {
    const deleteDuration = timestamp - state.deleteStartTime;
    
    // 使用正确的基准值计算
    const deletedChars = state.deleteStartLength - deleteEndLength; // 删除的字符数
    const addedChars = finalLength - deleteEndLength; // 新增的字符数
    const totalModifiedChars = deletedChars + addedChars; // 总共修改的字符数
    const netChange = finalLength - state.deleteStartLength; // 净变化

    // 只有当总修改字符数超过阈值时才认为是重要修改
    if (totalModifiedChars >= this.codeMonitoringConfig.minChangeThreshold) {
      const editRecord = {
        editor: editorType,
        edit_type: 'edit_cycle',
        duration: deleteDuration,
        deleted_chars: deletedChars,
        added_chars: addedChars,
        total_modified: totalModifiedChars,
        netChange: netChange,
        consecutive_edits: state.consecutiveEdits,
        timestamp: timestamp,
        submitted: false
      };

      this.significantEdits.push(editRecord);

      if (this.significantEdits.length > this.codeMonitoringConfig.maxHistoryLength) {
        this.significantEdits.shift();
      }

      this._logSignificantEdit(editRecord);

      console.log(`[${editorType}] 完成修改周期: 删除${deletedChars}字符, 新增${addedChars}字符, 总共修改${totalModifiedChars}字符, 净变化: ${netChange}字符`);
      
      // 只有当连续编辑次数超过阈值并且净变化不为0时才记录问题事件
      if (state.consecutiveEdits >= this.codeMonitoringConfig.problemDetectionThreshold && Math.abs(netChange) > 5) {
        this._recordProblemEvent(editorType, state.consecutiveEdits, timestamp);
      }
      
      const unsubmittedEdits = this.significantEdits.filter(edit => !edit.submitted);
      if (unsubmittedEdits.length >= 5 ||
        (state.consecutiveEdits >= this.codeMonitoringConfig.problemDetectionThreshold && Math.abs(netChange) > 5)) {
        this._submitSignificantEdits();
      }
    }

    state.isDeleting = false;
    state.deleteStartTime = 0;
    state.deleteStartLength = 0;
  }

  // 批量提交重要编辑
  // 触发条件：积累5个重要编辑或遇到问题时
  // 冷却周期：无固定冷却，基于数量阈值
  // 提交策略：批量提交
  _submitSignificantEdits() {
    const unsubmittedEdits = this.significantEdits.filter(edit => !edit.submitted);
    if (unsubmittedEdits.length === 0) return;
    
    const editsToSubmit = unsubmittedEdits.slice(-5); 
    editsToSubmit.forEach(edit => edit.submitted = true);

    // 只有当有足够多的重要编辑或遇到问题时才提交
    if (editsToSubmit.length >= 3) {
      this.logEvent('significant_edits', {
        batch_id: Date.now().toString(),
        count: editsToSubmit.length,
        edits: editsToSubmit.map(edit => ({
          editor: edit.editor,
          edit_type: edit.edit_type,
          deleted_chars: edit.deleted_chars,
          added_chars: edit.added_chars,
          total_modified: edit.total_modified,
          duration_ms: edit.duration,
          consecutive_edits: edit.consecutive_edits,
          timestamp: new Date(edit.timestamp).toISOString()
        })),
      });

      console.log(`批量提交 ${editsToSubmit.length} 个新重要编辑事件`);
    }
    
    this.significantEdits = this.significantEdits.filter(edit => 
      !edit.submitted || Date.now() - edit.timestamp < 300000
    );
  }
  // 在页面卸载或会话结束时提交所有数据
  // 触发条件：页面关闭/卸载时
  // 冷却周期：仅会话结束时触发一次
  // 提交策略：完整数据提交
  _initSessionEndHandler() {
    window.addEventListener('beforeunload', () => {
      this._submitAllData();
    });
  }

  _submitAllData() {
    if (this.significantEdits.length > 0) {
      this.logEvent('coding_session_summary', {
        total_edits: this.significantEdits.length,
        problem_events: this.problemEvents.length,
        significant_edits: this.significantEdits,
        timestamp: new Date().toISOString()
      });
    }
  }
  /**
   * 记录有意义的编辑
   */
  // 触发条件：单次增加操作 ≥10字符 + 超时3秒
  _recordMeaningfulEdit(editorType, editType, changeAmount, currentLength, timestamp) {
    const editRecord = {
      type: editType,
      editor: editorType,
      timestamp: timestamp,
      changeAmount: changeAmount,// 本次修改的字符数
      currentLength: currentLength,//  修改后的代码长度
      submitted: false // 添加提交标记
    };

    this.significantEdits.push(editRecord);

    // 保持记录数量
    if (this.significantEdits.length > this.codeMonitoringConfig.maxHistoryLength) {
      this.significantEdits.shift();
    }

    console.log(`[${editorType}] 有意义编辑: ${changeAmount}字符`);
  }

  /**
   * 记录问题事件
   */
  _recordProblemEvent(editorType, consecutiveEdits, timestamp) {
    const problemEvent = {
      editor: editorType,
      timestamp: timestamp,
      consecutiveEdits: consecutiveEdits,
      severity: this._calculateProblemSeverity(consecutiveEdits)
    };

    this.problemEvents.push(problemEvent);

    // 只有当连续编辑次数超过提示阈值时才触发问题提示
    if (consecutiveEdits >= this.hintConfig.hintThreshold) {
      this._triggerProblemHint(editorType, consecutiveEdits, timestamp);
    }
    // 立即提交问题事件
    this._submitProblemEvent(problemEvent);
  }
  // 新增问题提示触发方法
  _triggerProblemHint(editorType, editCount, timestamp) {
    // 检查冷却时间
    const now = Date.now();
    if (now - this.hintConfig.lastHintTime < this.hintConfig.cooldownPeriod) {
      return; // 还在冷却中，不触发提示
    }

    // 更新最后提示时间
    this.hintConfig.lastHintTime = now;

    // 触发自定义事件
    const eventDetail = {
      editor: editorType,
      editCount: editCount,
      timestamp: timestamp,
      message: this._generateHintMessage(editorType, editCount)
    };

    const event = new CustomEvent('problemHintNeeded', {
      detail: eventDetail
    });
    document.dispatchEvent(event);

    console.log(`触发问题提示: ${editorType} 编辑器, ${editCount} 次修改`);
  }
  // 生成提示消息

  _generateHintMessage(editorType, editCount) {
    const editorNames = {
      html: 'HTML',
      css: 'CSS',
      js: 'JavaScript'
    };

    const messages = [
      `我注意到您在${editorNames[editorType]}代码中反复修改了${editCount}次,是不是遇到了什么具体的问题？可以直接告诉我，让我来帮您分析解决～`,
      `我注意到${editorNames[editorType]}部分有些反复修改，这是在尝试实现什么功能吗？告诉我您的想法，我可以给您一些实现建议或最佳实践！`,
      `您对${editorNames[editorType]}的这${editCount}处修改我都看到了，是不是在调试某个效果？告诉我目标是什么，我帮您看看怎么实现更简单～`,
      `代码反复调整说明您在认真思考呢！如果卡在了${editorNames[editorType]}部分，不妨告诉我：您想实现什么？遇到了什么报错？或者哪里觉得不对劲？`,
      `我发现${editorNames[editorType]}代码还在优化中，需要我帮您看看吗？比如：\n• 语法检查\n• 逻辑优化\n• 效果实现\n告诉我具体需求吧！`,
      `您对${editorNames[editorType]}的细致调整很用心呢～如果遇到了瓶颈，可以这样问我：\n"如何实现XX功能？"\n"为什么这里报错？"\n"有没有更好的写法？"`,
      `看到您在${editorNames[editorType]}上花了不少心思！如果有什么不确定的地方，比如：\n• 这样写对不对？\n• 有没有更优雅的方式？\n• 为什么效果出不来？\n随时问我哦～`,
    ];

    return messages[Math.floor(Math.random() * messages.length)];
  }
  // 专门的问题事件提交方法
  // 触发条件：连续编辑 ≥3次
  // 冷却周期：无冷却，实时触发
  // 提交策略：立即提交
  _submitProblemEvent(problemEvent) {
    this.logEvent('coding_problem', {
      editor: problemEvent.editor,
      consecutive_edits: problemEvent.consecutiveEdits,
      severity: problemEvent.severity,// 区分严重程度
      timestamp: new Date(problemEvent.timestamp).toISOString()
    });

    console.warn(`实时提交问题事件: ${problemEvent.editor} 编辑器, ${problemEvent.consecutiveEdits} 次连续编辑`);
  }

  /**
   * 计算问题严重程度
   */
  _calculateProblemSeverity(consecutiveEdits) {//问题严重程度：低(3-4次)、中(5-7次)、高(≥8次)三个等级
    if (consecutiveEdits >= 10) return 'high';
    if (consecutiveEdits >= 5) return 'medium';
    return 'low';
  }

  /**
   * 输出重要编辑日志
   */
  // 触发条件：完成"删除→重新编写"完整周期 + 净变化≥10字符
  _logSignificantEdit(editRecord) {
    const time = new Date(editRecord.timestamp).toLocaleTimeString();
    console.log(
      `%c修改周期%c [${time}] %c${editRecord.editor.toUpperCase()}%c: 删除${editRecord.deleted_chars}字符 → 新增${editRecord.added_chars}字符, 总共修改${editRecord.total_modified}字符, 历时 ${editRecord.duration}ms, 连续 ${editRecord.consecutive_edits}次编辑`,
      'background: #4dabf7; color: white; padding: 2px 4px; border-radius: 3px;',
      'color: #666;',
      'color: #339af0; font-weight: bold;',
      'color: default;'
    );
  }

  /**
   * 获取代码行为分析
   */
  getCodingBehaviorAnalysis() {
    const now = Date.now();
    const sessionDuration = Math.round((now - (this.significantEdits[0]?.timestamp || now)) / 1000);

    // 计算各种统计数据
    const totalSignificantEdits = this.significantEdits.length;
    const problemEventsCount = this.problemEvents.length;

    const editsByType = this.significantEdits.reduce((acc, edit) => {
      acc[edit.type] = (acc[edit.type] || 0) + 1;
      return acc;
    }, {});

    const editsByEditor = this.significantEdits.reduce((acc, edit) => {
      acc[edit.editor] = (acc[edit.editor] || 0) + 1;
      return acc;
    }, {});

    // 计算平均编辑规模
    const editCycles = this.significantEdits.filter(e => e.type === 'edit_cycle');
    const avgEditSize = editCycles.length > 0 ?
      Math.round(editCycles.reduce((sum, e) => sum + Math.abs(e.netChange), 0) / editCycles.length) : 0;

    return {
      sessionDuration,//  会话持续时间
      totalSignificantEdits,//  重要编辑总数
      problemEventsCount,//  问题事件总数
      editsByType,  //  按编辑类型分类的编辑数
      editsByEditor,//  按编辑器分类的编辑数
      avgEditSize,//  平均编辑规模（字符数）
      recentProblems: this.problemEvents.slice(-5),// 最近5个问题事件
      recentEdits: this.significantEdits.slice(-10)// 最近10个重要编辑
    };
  }

  /**
   * 重置监控状态
   */
  resetCodeMonitoring() {
    this.codeMonitorStates = {
      html: this._createEditorState(),
      css: this._createEditorState(),
      js: this._createEditorState()
    };
    this.problemEvents = [];
    this.significantEdits = [];
    console.log('[BehaviorTracker] 代码监控状态已重置');
  }


  //后端处理
  // // -------------------- AI 求助（聊天） --------------------
  // // sendButtonId: 提问按钮 id；inputSelector: 文本输入选择器
  // // mode: 模式 ('learning' 或 'test')；contentId: 内容ID
  // initChat(sendButtonId, inputSelector, mode = 'learning', contentId = null) {
  //   const btn = document.getElementById(sendButtonId);
  //   const input = document.querySelector(inputSelector);
  //   if (!btn || !input) return;

  //   const sendMessage = () => {
  //     const message = input.value || '';
  //     if (!message.trim()) return;
  //     this.logEvent('ai_help_request', {
  //       message: message.substring(0, 2000),
  //       mode: mode,
  //       content_id: contentId
  //     });
  //   };

  //   btn.addEventListener('click', sendMessage);

  //   // 支持 Enter 提交
  //   input.addEventListener('keydown', (e) => {
  //     if (e.key === 'Enter' && !e.shiftKey) {
  //       e.preventDefault();
  //       sendMessage();
  //     }
  //   });
  // }

  // // -------------------- 测试/提交（包含 code） --------------------
  // // runBtnId / submitBtnId: 按钮 id；editors: 同 initEditors；topicIdGetter: 可选函数返回 topic_id
  // initTestActions(runBtnId, submitBtnId, editors, topicIdGetter) {
  //   const gatherCode = () => {
  //     const code = {};
  //     if (editors?.html && typeof editors.html.getValue === 'function') code.html = editors.html.getValue();
  //     if (editors?.css && typeof editors.css.getValue === 'function') code.css = editors.css.getValue();
  //     if (editors?.js && typeof editors.js.getValue === 'function') code.js = editors.js.getValue();
  //     return code;
  //   };

  //   const runBtn = document.getElementById(runBtnId);
  //   const subBtn = document.getElementById(submitBtnId);

  //   if (runBtn) {
  //     runBtn.addEventListener('click', () => {
  //       this.logEvent('test_submission', {
  //         action: 'run',
  //         topic_id: (typeof topicIdGetter === 'function' ? topicIdGetter() : window.currentTopicId) || null,
  //         code: gatherCode()
  //       });
  //     });
  //   }

  //   if (subBtn) {
  //     subBtn.addEventListener('click', () => {
  //       this.logEvent('test_submission', {
  //         action: 'submit',
  //         topic_id: (typeof topicIdGetter === 'function' ? topicIdGetter() : window.currentTopicId) || null,
  //         code: gatherCode()
  //       });
  //     });
  //   }
  // }

  // ---------- user_idle（升级版） ----------
  /**
   * 进入空闲：到达 idleThreshold，仅"标记空闲开始"（不立即上报）
   * 恢复活动：上报真实空闲（timestamp_start/end + duration_ms）
   * 空闲提示：空闲达到 hintAfterMs → 触发一次主动提示（轮换文案 + 冷却）
   */
  // 先进入空闲，再提示：hintAfterMs 被视为"从进入空闲起再等多久提示"
  // 若你仍传老参数（hintAfterMs 表示"总时间"），我们做兼容：effectiveDelay = max(0, hintAfterMs - idleMs)
  initIdleAndFocus(idleMs = this.idleThreshold) {
    if (this._focusAndIdleBound) return;
    this._focusAndIdleBound = true;

    // 覆盖提示配置
    if (this._enabledEvents?.idleHintConfig) {
      this.idleHintConfig = { ...this.idleHintConfig, ...this._enabledEvents.idleHintConfig };
    }

    const computeHintDelay = () => {
      // 1) 新语义：如果提供了 delayAfterIdleMs，则直接使用
      if (typeof this.idleHintConfig.delayAfterIdleMs === 'number') {
        return Math.max(0, this.idleHintConfig.delayAfterIdleMs);
      }
      // 2) 兼容旧语义：hintAfterMs 表示"从上次活动开始到提示的总时间"
      //    => 从进入空闲起再等 (hintAfterMs - idleMs)，不足 0 则 0
      const total = typeof this.idleHintConfig.hintAfterMs === 'number'
        ? this.idleHintConfig.hintAfterMs : idleMs;
      return Math.max(0, total - idleMs);
    };

    const scheduleIdleAndHint = () => {
      clearTimeout(this.idleTimer);
      clearTimeout(this._idleHintTimer);

      // 记录最近一次活动时刻
      this._lastActivityTs = Date.now();

      // 到达 idle 阈值 → 进入空闲；此刻才启动"提示倒计时"
      this.idleTimer = setTimeout(() => {
        if (this._idleStartTs == null) {
          this._idleStartTs = this._lastActivityTs; // 空闲起点=上次活动时间
        }
        // 现在才开始提示计时
        const delay = computeHintDelay();
        this._idleHintTimer = setTimeout(() => {
          // 仍处于空闲才提示
          if (this._idleStartTs != null) this._maybeShowIdleHint();
        }, delay);
      }, idleMs);
    };

    const onActivity = (src = 'activity') => {
      const now = Date.now();

      // 若正处于空闲 → 此时上报真实空闲区间
      if (this._idleStartTs != null) {
        const duration = now - this._idleStartTs;
        this.logEvent('user_idle', {
          duration_ms: duration,
          timestamp_start: new Date(this._idleStartTs).toISOString(),
          timestamp_end: new Date(now).toISOString(),
          was_focused: !document.hidden,
          page_url: window.location.pathname,
          trigger_source: src
        });
        this._idleStartTs = null;
      }

      // 重置一切计时
      this._lastActivityTs = now;
      scheduleIdleAndHint();
    };

    // —— 捕获"活动"更稳：keydown 用捕获阶段，补充 input/composition 事件 —— 
    const activityEvents = [
      ['mousemove', { passive: true }],
      ['scroll', { passive: true }],
      ['click', { passive: true }],
      ['pointerdown', { passive: true }],
      ['touchstart', { passive: true }],
      ['keydown', { capture: true }],        // 捕获阶段拿到键盘事件
      ['input', { capture: true }],        // 编辑器输入
      ['compositionstart', { capture: true }],
      ['compositionupdate', { capture: true }],
      ['compositionend', { capture: true }],
    ];
    activityEvents.forEach(([evt, opt]) => {
      document.addEventListener(evt, () => onActivity(evt), opt);
    });

    // 标签页回到前台也算活动
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) onActivity('visibility');
    });

    // 兜底：离开页面时若正处于空闲，补交一条
    window.addEventListener('pagehide', () => {
      if (this._idleStartTs != null) {
        const now = Date.now();
        const duration = now - this._idleStartTs;
        this.logEvent('user_idle', {
          duration_ms: duration,
          timestamp_start: new Date(this._idleStartTs).toISOString(),
          timestamp_end: new Date(now).toISOString(),
          was_focused: !document.hidden,
          page_url: window.location.pathname,
          trigger_source: 'pagehide'
        });
        this._idleStartTs = null;
      }
    });

    // 启动初始计时
    scheduleIdleAndHint();
  }
  /**
 * 空闲提示（进入空闲后等待 delay 再提示）
 * - 冷却保护（cooldownMs）
 * - 轮换文案（messages[]）
 * - 复用 problemHintNeeded 事件展示在聊天 UI
 */
  _maybeShowIdleHint() {
    const now = Date.now();

    // 冷却中则不提示
    const last = this.idleHintConfig?.lastHintTs || 0;
    const cooldown = this.idleHintConfig?.cooldownMs || 0;
    if (now - last < cooldown) return;

    // 检查代码编辑器活动情况
    // 如果用户最近有代码编辑活动，则不触发空闲提示
    const lastEditorActivity = this._getLastEditorActivityTime();
    const editorIdleThreshold = 10000; // 代码编辑器空闲阈值设为10秒
    if (lastEditorActivity && (now - lastEditorActivity) < editorIdleThreshold) {
      // 用户在编辑器中仍然活跃，重置空闲计时器
      this._resetIdleTimer();
      return;
    }

    const msgs = (this.idleHintConfig && this.idleHintConfig.messages) || [];
    if (!msgs.length) return;

    // 轮换一条文案
    const idx = this._idleMsgIdx % msgs.length;
    const message = msgs[idx];
    this._idleMsgIdx = idx + 1;

    // 标记本次提示时间
    this.idleHintConfig.lastHintTs = now;

    // 已空闲时长（到提示时刻）
    const idleStart = (this._idleStartTs ?? this._lastActivityTs) || now;
    const idleSoFar = Math.max(0, now - idleStart);

    // 复用你现有的 UI 事件（chat 那边已监听 problemHintNeeded）
    document.dispatchEvent(new CustomEvent('problemHintNeeded', {
      detail: { editor: 'idle', editCount: 0, timestamp: now, message }
    }));

    // 行为日志：记录提示本身（可用于 AB 评估）
    this.logEvent('idle_hint_displayed', {
      message,
      idle_ms: idleSoFar,
      page_url: window.location.pathname,
      timestamp: new Date().toISOString()
    });

    // 调试输出
    console.log(`[IdleHint] ${message}（已空闲 ${Math.round(idleSoFar / 1000)}s）`);
  }

  /**
   * 获取最后一次代码编辑活动的时间
   * @returns {number|null} 最后一次编辑活动的时间戳，如果没有则返回null
   */
  _getLastEditorActivityTime() {
    // 检查代码监控状态中最新的活动时间
    let latestActivityTime = null;
    
    // 遍历所有编辑器状态
    Object.values(this.codeMonitorStates).forEach(state => {
      if (state.lastMeaningfulEdit && 
          (!latestActivityTime || state.lastMeaningfulEdit > latestActivityTime)) {
        latestActivityTime = state.lastMeaningfulEdit;
      }
    });
    
    // 同时检查significantEdits数组中的最新编辑
    if (this.significantEdits.length > 0) {
      const lastEdit = this.significantEdits[this.significantEdits.length - 1];
      if (lastEdit.timestamp && 
          (!latestActivityTime || lastEdit.timestamp > latestActivityTime)) {
        latestActivityTime = lastEdit.timestamp;
      }
    }
    
    return latestActivityTime;
  }

  /**
   * 重置空闲计时器
   */
  _resetIdleTimer() {
    // 清除现有的空闲计时器
    clearTimeout(this.idleTimer);
    clearTimeout(this._idleHintTimer);
    
    // 重置空闲状态
    this._idleStartTs = null;
    
    // 重新启动计时器
    const scheduleIdleAndHint = () => {
      // 记录最近一次活动时刻
      this._lastActivityTs = Date.now();
      
      // 重新启动空闲检测计时器
      this.idleTimer = setTimeout(() => {
        if (this._idleStartTs == null) {
          this._idleStartTs = this._lastActivityTs;
        }
        // 重新启动提示计时器
        this._idleHintTimer = setTimeout(() => {
          if (this._idleStartTs != null) this._maybeShowIdleHint();
        }, 3000); // 3秒后再次检查
      }, this.idleThreshold);
    };
    
    scheduleIdleAndHint();
  }

  // -------------------- page_click：统一批量 + 归一化坐标 --------------------
  initPageClick(options = {}) {
    const defaults = {
      batch: true,
      flushInterval: 1200,
      maxBatchSize: 50,
      includeTextMaxLen: 120
    };
    this._clickCfg = { ...defaults, ...options };

    const handler = (e) => {
      if (e.button !== 0) return; // 仅统计左键
      const t = (typeof e.composedPath === 'function' && e.composedPath()[0]) || e.target;
      if (!t || !(t instanceof Element)) return;

      const rec = this._buildClickRecord(t, e, this._clickCfg.includeTextMaxLen);
      if (this._clickCfg.batch) this._enqueueClick(rec);
      else this._sendClickBatch([rec]);
    };

    document.addEventListener('click', handler, { capture: true });

    const flushOnLeave = () => this._flushClickBatch(true);
    window.addEventListener('pagehide', flushOnLeave);
    window.addEventListener('beforeunload', flushOnLeave);
    document.addEventListener('visibilitychange', () => { if (document.hidden) this._flushClickBatch(true); });

    console.debug('[BehaviorTracker] page_click initialized', this._clickCfg);
  }

  _clamp01(v) { return Math.max(0, Math.min(1, v)); }

  _buildClickRecord(target, e, maxLen) {
    const rect = target.getBoundingClientRect ? target.getBoundingClientRect() : null;
    const w = rect?.width || 1, h = rect?.height || 1;

    const x_norm = this._clamp01((e.clientX - (rect?.left ?? 0)) / w);
    const y_norm = this._clamp01((e.clientY - (rect?.top ?? 0)) / h);

    const vp_x_norm = this._clamp01(e.clientX / (window.innerWidth || 1));
    const vp_y_norm = this._clamp01(e.clientY / (window.innerHeight || 1));

    const tag = (target.tagName || '').toLowerCase();
    const selector = this._generateCssSelector(target);

    const interactive = this._isInteractive(target);
    const content = interactive ? this._getInteractiveContent(target, maxLen) : null;

    return {
      t: new Date().toISOString(),
      tag,
      selector,
      interactive,
      x_norm, y_norm,
      vp_x_norm, vp_y_norm,
      rect_wh: { w: Math.round(w), h: Math.round(h) },
      page: { vw: window.innerWidth, vh: window.innerHeight, dpr: window.devicePixelRatio || 1, sx: window.scrollX, sy: window.scrollY },
      content,
      content_len: content ? content.length : 0,
    };
  }

  _isInteractive(el) {
    if (!el || !(el instanceof Element)) return false;
    const tag = el.tagName ? el.tagName.toLowerCase() : '';
    if (['button', 'input', 'select', 'textarea', 'label'].includes(tag)) return true;
    if (el.hasAttribute?.('contenteditable')) return true;
    if (el.getAttribute?.('role') === 'button') return true;
    if (el.matches?.('a[href], [tabindex]:not([tabindex="-1"])')) return true;
    return false;
  }

  _getInteractiveContent(el, maxLen = 120) {
    try {
      const tag = el.tagName?.toLowerCase() || '';
      if (tag === 'input' && (el.type === 'password' || el.type === 'file')) return null;
      let text = (tag === 'input' || tag === 'textarea') ? (el.value ?? '') : (el.textContent ?? '');
      text = text.trim().replace(/\s+/g, ' ');
      if (text.length > maxLen) text = text.slice(0, maxLen);
      return text || null;
    } catch { return null; }
  }

  _enqueueClick(rec) {
    this._clickBatch.push(rec);
    const cfg = this._clickCfg;

    if (this._clickBatch.length >= cfg.maxBatchSize) { this._flushClickBatch(); return; }

    // 只在没有计时器时启动；避免持续点击导致永远不 flush
    if (!this._clickBatchTimer) {
      this._clickBatchTimer = setTimeout(() => this._flushClickBatch(), cfg.flushInterval);
    }
  }

  _flushClickBatch(isFinal = false) {
    if (!this._clickBatch.length) return;
    const items = this._clickBatch.splice(0, this._clickBatch.length);
    clearTimeout(this._clickBatchTimer);
    this._clickBatchTimer = null;
    this._sendClickBatch(items, isFinal);
  }

  _sendClickBatch(items, isFinal = false) {
    this.logEvent('page_click', {
      page_url: window.location.pathname,
      count: items.length,
      items,
      final: !!isFinal
    });
  }

  // -------------------- 辅助：生成 CSS Selector --------------------
  _generateCssSelector(el) {
    if (!el) return '';
    const parts = [];
    while (el && el.nodeType === Node.ELEMENT_NODE) {
      let part = el.nodeName.toLowerCase();
      if (el.id) {
        part += `#${el.id}`;
        parts.unshift(part);
        break;
      } else {
        let i = 1;
        let sib = el;
        while ((sib = sib.previousElementSibling) != null) {
          if (sib.nodeName.toLowerCase() === part) i++;
        }
        if (i > 1) part += `:nth-of-type(${i})`;
      }
      parts.unshift(part);
      el = el.parentElement;
    }
    return parts.join(' > ');
  }

  initAuto() {
    document.addEventListener('DOMContentLoaded', () => {
      const monacoContainer = document.getElementById('monaco-editor');
      if (monacoContainer && window.monaco && window.editors) {
        try {
          const editors = window.editors || {};
          this.initEditors(editors);
        } catch (e) {
          console.warn('[BehaviorTracker] 编辑器自动初始化失败', e);
        }
        return;
      }
    });
  }
}

const tracker = new BehaviorTracker();
export default tracker;

try { tracker.initAuto(); } catch (err) {
  console.warn('[BehaviorTracker] initAuto error', err);
}