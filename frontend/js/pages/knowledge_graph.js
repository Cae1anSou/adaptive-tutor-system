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

    // 显示知识点弹窗 - 使用学习页面的稳定弹窗函数
    function showKnowledgeModal(knowledgeId, nodeLabel) {
      const modal = document.getElementById('knowledgeModal');
      const title = document.getElementById('modalTitle');
      const status = document.getElementById('modalStatus');
      const learnBtn = document.getElementById('learnBtn');
      const testBtn = document.getElementById('testBtn');

      title.textContent = nodeLabel || knowledgeId;

      // 重置按钮状态
      learnBtn.className = 'learn-btn';
      learnBtn.disabled = false;
      learnBtn.textContent = '学习';
      testBtn.className = 'test-btn';
      testBtn.textContent = '测试';

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

    function showKnowledgeModal_2(knowledgeId, previousChapterId, requiredChapter, nodeLabel) {
      const modal = document.getElementById('knowledgeModal');
      const title = document.getElementById('modalTitle');
      const status = document.getElementById('modalStatus');
      const learnBtn = document.getElementById('learnBtn');
      const testBtn = document.getElementById('testBtn');

      title.textContent = nodeLabel || knowledgeId;

      // 重置按钮状态
      learnBtn.className = 'learn-btn';
      learnBtn.disabled = false;
      learnBtn.textContent = '是';
      testBtn.className = 'test-btn';
      testBtn.textContent = '否';

      status.textContent = `您还未完成前置章节"${requiredChapter}"的测试，需要先完成该章节的测试才能学习本知识点。是否现在开始测试前置章节？`;

      learnBtn.onclick = () => {
        localStorage.setItem('jumpLearningTarget', JSON.stringify({
          knowledgeId,
          timestamp: Date.now()
        }));
        const chapterNum = parseInt(previousChapterId.replace('chapter', ''));
        const chapterTestId = `${chapterNum}_end`;
        console.log('[DEBUG] showKnowledgeModal_2 转换:', previousChapterId, '->', chapterTestId);
        navigateTo('/pages/test_page.html', chapterTestId, true, true);
      };

      testBtn.onclick = () => {
        document.getElementById('knowledgeModal').style.display = 'none';
      };

      modal.style.display = 'block';
    }

    function showKnowledgeModal_3(knowledgeId, lastTestId, requiredKnowledge, nodeLabel) {
      const modal = document.getElementById('knowledgeModal');
      const title = document.getElementById('modalTitle');
      const status = document.getElementById('modalStatus');
      const learnBtn = document.getElementById('learnBtn');
      const testBtn = document.getElementById('testBtn');

      title.textContent = nodeLabel || knowledgeId;

      // 重置按钮状态
      learnBtn.className = 'learn-btn';
      learnBtn.disabled = false;
      learnBtn.textContent = '是';
      testBtn.className = 'test-btn';
      testBtn.textContent = '否';

      status.textContent = `您还未学习前置知识点"${requiredKnowledge}"，需要先完成该知识点的测试才能学习本知识点。是否现在开始测试前置知识点？`;

      learnBtn.onclick = () => {
        localStorage.setItem('jumpLearningTarget', JSON.stringify({
          knowledgeId,
          timestamp: Date.now()
        }));
        navigateTo('/pages/test_page.html', lastTestId, true, true);
        modal.style.display = 'none';
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
        navigateTo('/pages/test_page.html', Id, true, true);
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
        navigateTo('/pages/test_page.html', Id, true, true);
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
        navigateTo('/pages/test_page.html', Id, true, true);
    };

    testBtn.onclick = () => {
        document.getElementById('knowledgeModal').style.display = 'none';
    };

    modal.style.display = 'block';
}
    // 处理跳跃学习场景

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
        } else {
          // 使用新的跳跃学习检查逻辑
          const jumpResult = graphState.canJumpToKnowledge(id);
          if (jumpResult.canJump) {// 可以跳跃学习
            showKnowledgeModal(id, label);
          } else {// 不能跳跃学习，显示相应的提示
            if (jumpResult.reason === 'chapter_locked') {
              // 章节未解锁
              showKnowledgeModal_2(id, jumpResult.requiredChapter, jumpResult.requiredChapterName, label);
            } else if (jumpResult.reason === 'previous_knowledge_required' || jumpResult.reason === 'previous_chapter_test_required') {
              // 需要完成前置知识点测试或章节测试
              showKnowledgeModal_3(id, jumpResult.requiredKnowledgeId, jumpResult.requiredKnowledgeName, label);
            } else {
              // 其他情况，使用原有逻辑
              showKnowledgeModal(id, label);
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
  } catch (error) {
    console.error('初始化知识图谱失败:', error);
    alert('加载知识图谱失败，请刷新页面重试');
  }

});
