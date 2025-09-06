// knowledgeGraph.js - 主模块（协调其他模块）
import { getParticipantId } from '../modules/session.js';
import { GraphState } from '../modules/graph_data.js';
import { GraphRenderer } from '../modules/graph_renderer.js';
import { buildBackendUrl } from '../modules/config.js';  // 新增导入
import { setupHeaderTitle, trackReferrer, setupBackButton, navigateTo } from '../modules/navigation.js';
import tracker from '../modules/behavior_tracker.js';

tracker.init({
  user_idle: false,
  page_focus_change: false,
  idleThreshold: 60000,           // 测试时可先设成 5000（5s）
});

// 初始化应用
document.addEventListener('DOMContentLoaded', async () => {
  trackReferrer();
  // 设置标题点击跳转到首页
  setupHeaderTitle('/pages/knowledge_graph.html');

  // 设置返回按钮
  setupBackButton();
  try {
    // 获取实验编号并验证
    const participantId = getParticipantId();
    if (!participantId) {
      window.location.href = '/pages/index.html';
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
    // 查看后端返回数据格式
    console.log(graphResult);
    console.log(graphResult.data.nodes);
    console.log(graphResult.data.edges);
    console.log(graphResult.data.dependent_edges);
    // 查看后端返回数据格式
    console.log(progressResult);
    // 处理数据
    const graphData = graphResult.data;
    const learnedNodes = progressResult.data.completed_topics || [];

    // 验证数据格式
    if (!graphData || !graphData.nodes || !graphData.edges) {
      throw new Error('图谱数据格式不正确');
    }

    // 初始化状态管理
    const graphState = new GraphState(graphData, learnedNodes);
    try {
      graphState.initMaps();
    } catch (error) {
      console.error('初始化状态失败:', error);
      throw new Error('初始化知识图谱状态失败');
    }

    // 初始化渲染器
    const graphRenderer = new GraphRenderer('cy', graphState);
    graphRenderer.addElements([...graphData.nodes, ...graphData.edges]);

    // 设置初始布局
    graphRenderer.setFixedChapterPositions();
    graphRenderer.hideAllKnowledgeNodes();
    graphRenderer.updateNodeColors();
    // 添加工具栏功能
    graphRenderer.addToolbarFunctionality();
    // 初始居中
    setTimeout(() => graphRenderer.centerAndZoomGraph(), 100);

    // 窗口点击事件处理
    window.onclick = (event) => {
      const modal = document.getElementById('knowledgeModal');
      if (event.target === modal) modal.style.display = 'none';
    };
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
        handleDoubleClick(node);
      } else {
        clickState.lastId = id;
        clickState.ts = now;
        clickState.timer = setTimeout(() => {
          handleSingleClick(node);
          clickState.timer = null;
          clickState.lastId = null;
        }, DBL_DELAY);
      }
      // 当节点位置变化时，重新调整显示
      setTimeout(() => {
        graphRenderer.centerAndZoomGraph();
      }, 50);
    });
    // 单击处理
    function handleSingleClick(node) {
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
          if (chapterCheckResult.requiresChapterCompletion) {
            if (confirm(`您还未完成前置章节"${chapterCheckResult.requiredChapter}"的测试，需要先完成该章节的最后一个测试才能学习"${label}"。是否现在开始测试前置章节？`)) {
              navigateTo('/pages/test_page.html', chapterCheckResult.lastTestId, true, true);
            }
          } else {
            // 获取前置知识点信息
            const prerequisiteInfo = getPrerequisiteInfo(id);
            if (prerequisiteInfo) {
              if (confirm(`您还未学习前置知识点"${prerequisiteInfo.label}"，需要先完成该知识点的测试才能学习"${label}"。是否现在开始测试前置知识点？`)) {
                navigateTo('/pages/test_page.html', prerequisiteInfo.id, true, true);
              }
            } else {
              if (confirm("您还未学习前置知识点，是否直接开始测试？")) {
                navigateTo('/pages/test_page.html', id, true, true);
              }
            }
          }
        }
      }
    }

    // 双击处理
    function handleDoubleClick(node) {
      const id = node.id();
      const type = node.data('type');

      if (type === 'chapter') {
        if (graphState.isChapterCompleted(id)) {
          if (confirm("您已学过本章节，是否再次进行测试？")) {
            navigateTo('/pages/test_page.html', id, true, true);
          }
        } else if (graphState.currentLearningChapter === id) {
          if (confirm("您还未学完当前章节内容，是否直接开始测试？")) {
            navigateTo('/pages/test_page.html', id, true, true);
          }
        } else {
          if (confirm("您还未解锁前置章节，是否直接开始测试？")) {
            navigateTo('/pages/test_page.html', id, true, true);
          }
        }

        graphState.passChapterTest(id);
        graphRenderer.updateNodeColors();
      }
    }
  } catch (error) {
    console.error('初始化知识图谱失败:', error);
    alert('加载知识图谱失败，请刷新页面重试');
  }

});

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

    // 如果是其他章节的第一个知识点，需要检查前一章节是否完成
    if (section === 1) {
      const previousChapter = chapter - 1;
      const previousChapterId = `chapter${previousChapter}`;

      // 检查前一章节是否已完成
      const completedChapters = JSON.parse(localStorage.getItem('completedChapters') || '[]');
      const isPreviousChapterCompleted = completedChapters.includes(previousChapterId);

      if (!isPreviousChapterCompleted) {
        return {
          requiresChapterCompletion: true,
          requiredChapter: `第${previousChapter}章`,
          lastTestId: `${previousChapter}_3` // 前一章节的最后一个测试
        };
      }
    }

    return { requiresChapterCompletion: false };
  } catch (error) {
    console.error('检查章节前置条件时出错:', error);
    return { requiresChapterCompletion: false };
  }
}