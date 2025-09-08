// modules/mini_knowledge_graph.js
import { GraphState, LAYOUT_PARAMS } from './graph_data.js';
import { buildBackendUrl } from './config.js';
import { getParticipantId } from './session.js';
import { getUrlParam, navigateTo } from './navigation.js';

export class MiniKnowledgeGraph {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.options = {
      height: 200,
      nodeSize: 20,
      chapterNodeSize: 30,
      fontSize: 10,
      // 添加新的选项
      enableInteractions: true,
      enableModal: true,
      ...options
    };
    this.cy = null;
    this.graphState = null;
    this.isInitialized = false;
    this.layoutParams = LAYOUT_PARAMS;
    // 存储节点的原始尺寸
    this.originalSizes = new Map();
    // 添加点击状态管理
    this.clickState = { lastId: null, timer: null, ts: 0 };
    this.DBL_DELAY = 280;
  }

  // 初始化简化知识图谱
  async init() {
    try {
      // 检查容器元素是否存在
      const container = document.getElementById(this.containerId);
      if (!container) {
        console.warn(`知识图谱容器元素 #${this.containerId} 不存在`);
        return;
      }

      const participantId = getParticipantId();
      if (!participantId) {
        console.warn('未找到实验编号，无法加载简化知识图谱');
        return;
      }

      // 获取图谱数据和用户进度
      const [graphResponse, progressResponse] = await Promise.all([
        fetch(buildBackendUrl('/knowledge-graph')),
        fetch(buildBackendUrl(`/progress/participants/${participantId}/progress`))
      ]);

      if (!graphResponse.ok || !progressResponse.ok) {
        throw new Error('获取数据失败');
      }

      const [graphResult, progressResult] = await Promise.all([
        graphResponse.json(),
        progressResponse.json()
      ]);

      const graphData = graphResult.data;
      const learnedNodes = progressResult.data.completed_topics || [];

      if (!graphData || !graphData.nodes || !graphData.edges) {
        throw new Error('图谱数据格式不正确');
      }

      // 初始化状态管理
      this.graphState = new GraphState(graphData, learnedNodes);
      this.graphState.initMaps();

      // 设置当前学习节点
      this.setCurrentLearningNode();

      // 创建Cytoscape实例
      this.createCytoscapeInstance();

      // 添加元素
      this.cy.add([...graphData.nodes, ...graphData.edges]);

      // 更新节点状态
      this.updateNodeStates();

      // 设置布局
      this.applyLayout();

      // 添加交互效果
      this.setupInteractions();

      // 启动监听容器状态变化
      this.listenToContainerStateChange();

      // 绑定布局事件监听器
      this.bindLayoutEvents();

      this.isInitialized = true;
      console.log('简化知识图谱初始化完成');

    } catch (error) {
      console.error('初始化简化知识图谱失败:', error);
    }
  }

  // 从URL获取并设置当前学习节点
  setCurrentLearningNode() {
    try {
      // 获取URL中的topic参数
      const topicData = getUrlParam('topic');
      console.log('URL解密结果:', topicData);

      if (topicData && topicData.id) {
        const nodeId = topicData.id;
        console.log('当前学习节点ID:', nodeId);

        // 查找对应的节点
        const node = this.graphState.graphData.nodes.find(n =>
          n.data && n.data.id === nodeId
        );

        if (node) {
          console.log('找到当前学习节点:', node);
          // 如果是章节节点，直接设置为当前学习章节
          if (node.data.type === 'chapter') {
            this.graphState.currentLearningChapter = nodeId;
            console.log('设置当前学习章节:', nodeId);
          }
          // 如果是知识点节点，需要找到其所属章节
          else {
            // 查找父章节
            const parents = this.graphState.parentMap[nodeId] || [];
            console.log('知识点的父节点:', parents);

            // 查找第一个章节类型的父节点
            for (const parentId of parents) {
              const parentNode = this.graphState.graphData.nodes.find(n =>
                n.data && n.data.id === parentId
              );

              if (parentNode && parentNode.data.type === 'chapter') {
                this.graphState.currentLearningChapter = parentId;
                console.log('设置当前学习章节(通过知识点查找):', parentId);
                break;
              }
            }

            // 如果没找到父章节，尝试通过前置关系查找
            if (!this.graphState.currentLearningChapter) {
              const prereqs = this.graphState.prereqMap[nodeId] || [];
              console.log('知识点的前置节点:', prereqs);

              for (const prereqId of prereqs) {
                const prereqNode = this.graphState.graphData.nodes.find(n =>
                  n.data && n.data.id === prereqId
                );

                if (prereqNode && prereqNode.data.type === 'chapter') {
                  this.graphState.currentLearningChapter = prereqId;
                  console.log('设置当前学习章节(通过前置关系查找):', prereqId);
                  break;
                }
              }
            }
          }
        } else {
          console.warn('未找到对应节点:', nodeId);
        }
      } else {
        console.log('URL中未找到有效的topic参数');
      }
    } catch (error) {
      console.error('设置当前学习节点失败:', error);
    }
  }

  // 创建Cytoscape实例
  createCytoscapeInstance() {
    // 检查容器元素是否存在
    const container = document.getElementById(this.containerId);
    if (!container) {
      throw new Error(`知识图谱容器元素 #${this.containerId} 不存在`);
    }

    this.cy = cytoscape({
      container: container,
      style: [
        {
          selector: 'node',
          style: {
            'content': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'color': '#1e293b',
            'background-color': '#f1f5f9',
            'width': 170,
            'height': 170,
            'font-size': '22px',
            'font-family': 'Inter, sans-serif',
            'font-weight': 500,
            'font-weight': 'bold',
            'text-max-width': '100px',
            'shape': 'ellipse',
            'border-width': 2,
            'border-color': '#e2e8f0',
            'overlay-opacity': 0,
            'overlay-color': '#4f46e5',
            'overlay-padding': '10px',
            'transition-property': 'background-color, border-color, width, height',
            'transition-duration': '0.3s',
            'transition-timing-function': 'ease'
          }
        },
        {
          selector: 'node[type="chapter"]',
          style: {
            'shape': 'roundrectangle',
            'font-weight': 'bold',
            'width': 340,
            'height': 120,
            'background-color': '#4f46e5',
            'color': '#1e293b',
            'border-width': 3,
            'border-color': '#3730a3',
            'font-size': '28px'
          }
        },
        {
          selector: 'node.learned',
          style: {
            'background-color': '#10b981',
            'border-color': '#059669'
          }
        },
        {
          selector: 'node.unlocked',
          style: {
            'background-color': '#3b82f6',
            'border-color': '#2563eb'
          }
        },
        {
          selector: 'node.locked',
          style: {
            'background-color': '#9ca3af',
            'border-color': '#6b7280'
          }
        },
        {
          selector: 'node.current',
          style: {
            'background-color': '#f59e0b',
            'border-color': '#d97706'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2.5,  // 调整线宽，使线条看起来更精细
            'line-color': '#2563eb',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#2563eb',
            'curve-style': 'straight',  // 改为直线连接，更简洁
            'taxi-direction': 'auto',  // 自动选择最佳方向
            'taxi-turn': '40%',  // 调整拐角位置
            'edge-distances': 'intersection',  // 从节点边缘开始连线
            'arrow-scale': 2,  // 减小箭头尺寸
            'line-style': 'solid',
            'transition-property': 'line-color, width, target-arrow-color',
            'transition-duration': '0.3s',
            'transition-timing-function': 'ease'
          }
        }
      ],
      layout: { name: 'preset' },
      minZoom: 0.1,
      maxZoom: 1.0,
      wheelSensitivity: 0.2
    });
  }

  // 更新节点状态
  updateNodeStates() {
    // 首先获取当前学习节点ID
    let currentLearningNodeId = null;

    try {
      // 获取URL中的topic参数
      const topicData = getUrlParam('topic');
      if (topicData && topicData.id) {
        currentLearningNodeId = topicData.id;
      }
    } catch (error) {
      console.warn('获取当前学习节点失败:', error);
    }

    this.cy.nodes().forEach(node => {
      const id = node.id();
      const type = node.data('type');

      // 清除所有状态类，确保状态互斥
      node.removeClass('learned');
      node.removeClass('unlocked');
      node.removeClass('locked');
      node.removeClass('current');

      // 当前学习节点优先级最高
      if (id === currentLearningNodeId) {
        node.addClass('current');
        console.log('标记当前学习节点:', id);
      } else if (type === 'chapter') {
        // 当前学习章节优先级次之
        if (this.graphState.currentLearningChapter === id) {
          node.addClass('current');
        } else if (this.graphState.isChapterCompleted(id)) {
          node.addClass('learned');
        } else if (this.graphState.canLearnChapter(id)) {
          node.addClass('unlocked');
        } else {
          node.addClass('locked');
        }
      } else {
        // 如果属于当前学习章节，则标记为当前
        if (this.graphState.currentLearningChapter &&
          this.graphState.collectKnowledgeDescendantsForDisplay(this.graphState.currentLearningChapter).includes(id)) {
          // 只有在没有明确指定当前学习节点时才标记为当前章节的知识点
          if (!currentLearningNodeId) {
            node.addClass('current');
          }
        } else if (this.graphState.learnedNodes.includes(id)) {
          node.addClass('learned');
        } else if (this.graphState.isKnowledgeUnlocked(id)) {
          node.addClass('unlocked');
        } else {
          node.addClass('locked');
        }
      }
    });
  }

  // 应用布局
  applyLayout() {
    // 设置章节固定位置
    this.setFixedChapterPositions();

    // 隐藏所有知识点
    this.hideAllKnowledgeNodes();

    // 居中缩放图谱
    this.centerAndZoomGraph();
  }

  // 添加监听容器状态变化的方法
  listenToContainerStateChange() {
    // 根据用户要求，不再操控原来的容器和知识图谱效果
    // 因为已经在learning_page.js中实现了新的容器逻辑
    console.log('已禁用旧的容器状态监听逻辑，使用新的容器实现');
    return;
  }

  // 等比放大图谱以适应展开的容器
  adjustSizeForExpandedContainer() {
    // 根据用户要求，不再操控原来的容器和知识图谱效果
    console.log('已禁用旧的容器展开逻辑，使用新的容器实现');
    return;
  }

  // 重置图谱大小
  resetSize() {
    // 根据用户要求，不再操控原来的容器和知识图谱效果
    console.log('已禁用旧的容器收起逻辑，使用新的容器实现');
    return;
  }

  // 收起所有章节
  collapseAllChapters() {
    // 根据用户要求，不再操控原来的容器和知识图谱效果
    console.log('已禁用旧的章节收起逻辑，使用新的容器实现');
    return;
  }

  // 展开章节
  expandChapter(chapterId) {
    // 根据用户要求，不再操控原来的容器和知识图谱效果
    console.log('已禁用旧的章节展开逻辑，使用新的容器实现');
    return;
  }

  // 收起章节
  collapseChapter(chapterId) {
    // 根据用户要求，不再操控原来的容器和知识图谱效果
    console.log('已禁用旧的章节收起逻辑，使用新的容器实现');
    return;
  }

  // 自动展开当前学习章节
  expandCurrentChapter() {
    // 根据用户要求，不再操控原来的容器和知识图谱效果
    console.log('已禁用旧的自动展开逻辑，使用新的容器实现');
    return;
  }

  // 设置交互效果
  setupInteractions() {
    // 存储所有节点的原始尺寸
    this.updateOriginalSizes();

    // 节点悬停效果
    this.cy.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      const originalSize = this.originalSizes.get(node.id()) || { width: 120, height: 120 };
      const scaleFactor = node.data('type') === 'chapter' ? 1.15 : 1.1;

      // 使用动画过渡效果
      node.stop().animate({
        style: {
          'background-color': node.data('type') === 'chapter' ? '#3730a3' : '#c7d2fe',
          'color': node.data('type') === 'chapter' ? '#ffffff' : '#1e293b',
          'border-color': '#4f46e5',
          'width': originalSize.width * scaleFactor,
          'height': originalSize.height * scaleFactor
        }
      }, {
        duration: 200
      });
    });

    this.cy.on('mouseout', 'node', (evt) => {
      const node = evt.target;
      // 使用动画恢复原始样式
      node.stop().animate({
        style: {
          'color': '#1e293b'
        }
      }, {
        duration: 150,
        complete: () => {
          this.restoreNodeStyle(node);
        }
      });
    });

    // 边悬停效果
    this.cy.on('mouseover', 'edge', (evt) => {
      const edge = evt.target;
      edge.style({
        'line-color': '#4f46e5',
        'target-arrow-color': '#4f46e5',
        'width': 3.5,
        'curve-style': 'straight',
        'edge-distances': 'intersection'
      });
    });

    this.cy.on('mouseout', 'edge', (evt) => {
      const edge = evt.target;
      edge.style({
        'line-color': '#2563eb',
        'target-arrow-color': '#2563eb',
        'width': 2.5,
        'curve-style': 'straight',
        'edge-distances': 'intersection'
      });
    });

    // 添加节点点击事件处理
    this.cy.on('tap', 'node', (evt) => {
      const node = evt.target;
      const id = node.id();
      const now = Date.now();

      // 如果启用了完整的交互功能
      if (this.options.enableInteractions) {
        if (this.clickState.lastId === id && (now - this.clickState.ts) < this.DBL_DELAY) {
          clearTimeout(this.clickState.timer);
          this.clickState.timer = null;
          this.clickState.lastId = null;
          this.handleDoubleClick(node);
        } else {
          this.clickState.lastId = id;
          this.clickState.ts = now;
          this.clickState.timer = setTimeout(() => {
            this.handleSingleClick(node);
            this.clickState.timer = null;
            this.clickState.lastId = null;
          }, this.DBL_DELAY);
        }
      } else {
        // 只处理章节节点的点击事件（原有逻辑）
        const type = node.data('type');
        if (type === 'chapter') {
          if (this.graphState.expandedSet.has(id)) {
            // 如果章节已展开，则收起
            this.collapseChapter(id);
          } else {
            // 如果章节未展开，则展开
            this.expandChapter(id);
          }
        }
      }
    });
  }

  // 单击处理
  handleSingleClick(node) {
    const id = node.id();
    const type = node.data('type');

    if (type === 'chapter') {
      // 显示知识图谱容器
      this.showKnowledgeGraphContainer();

      // 原有逻辑保持不变
      if (this.graphState.expandedSet.has(id)) {
        this.collapseChapter(id);
      } else {
        this.expandChapter(id);
      }

      if (this.graphState.currentLearningChapter === null && id === 'chapter1' &&
        !this.graphState.learnedNodes.includes(id)) {
        this.graphState.currentLearningChapter = id;
      }

      this.updateNodeStates();
      return;
    }

    if (type === 'knowledge') {
      // 显示知识图谱容器
      this.showKnowledgeGraphContainer();

      const label = node.data('label') || id;
      if (this.options.enableModal) {
        this.showKnowledgeModal(id, label);
      } else {
        // 如果不启用模态框，直接导航到学习页面
        this.navigateTo('/pages/learning_page.html', id);
      }
    }
  }

  // 双击处理
  handleDoubleClick(node) {
    const id = node.id();
    const type = node.data('type');

    if (type === 'chapter') {
      if (this.graphState.isChapterCompleted(id)) {
        if (confirm("您已学过本章节，是否再次进行测试？")) {
          this.navigateTo('/pages/test_page.html', id, true, true);
        }
      } else if (this.graphState.currentLearningChapter === id) {
        if (confirm("您还未学完当前章节内容，是否直接开始测试？")) {
          this.navigateTo('/pages/test_page.html', id, true, true);
        }
      } else {
        if (confirm("您还未解锁前置章节，是否直接开始测试？")) {
          this.navigateTo('/pages/test_page.html', id, true, true);
        }
      }

      this.graphState.passChapterTest(id);
      this.updateNodeStates();
    }
  }

  // 显示知识点弹窗
  showKnowledgeModal(knowledgeId, nodeLabel) {
    // 创建或获取模态框元素
    let modal = document.getElementById('knowledgeModal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'knowledgeModal';
      modal.className = 'modal';
      modal.innerHTML = `
        <div class="modal-content">
          <iconify-icon icon="mdi:book-open" width="32" height="32" style="color: var(--primary-color);"></iconify-icon>
          <h2 id="modalTitle"></h2>
          <p id="modalStatus"></p>
          <div class="modal-actions">
            <button id="learnBtn" class="btn btn-primary">学习</button>
            <button id="testBtn" class="btn btn-primary">测试</button>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }

    const title = document.getElementById('modalTitle');
    const status = document.getElementById('modalStatus');
    const learnBtn = document.getElementById('learnBtn');
    const testBtn = document.getElementById('testBtn');

    title.textContent = nodeLabel || knowledgeId;
    learnBtn.className = 'learn-btn';
    learnBtn.disabled = false;
    learnBtn.textContent = '学习';
    testBtn.className = 'test-btn';

    // 获取当前学习的知识点ID（用于判断跳跃学习场景）
    let currentKnowledgeId = null;
    try {
      const topicData = getUrlParam('topic');
      if (topicData && topicData.id) {
        currentKnowledgeId = topicData.id;
      }
    } catch (error) {
      console.warn('获取当前学习知识点失败:', error);
    }

    if (this.graphState.learnedNodes.includes(knowledgeId)) {
      status.textContent = '您已学过该知识点，是否再次复习或重新测试？';
      learnBtn.textContent = '复习';
      learnBtn.className = 'review-btn';

      learnBtn.onclick = () => {
        this.navigateTo('/pages/learning_page.html', knowledgeId);
      };

      testBtn.onclick = () => {
        this.navigateTo('/pages/test_page.html', knowledgeId, true, true);
      };
    } else if (this.graphState.isKnowledgeUnlocked(knowledgeId)) {
      status.textContent = '您可以开始学习该知识点或直接进行测试';

      learnBtn.onclick = () => {
        this.navigateTo('/pages/learning_page.html', knowledgeId);
      };

      testBtn.onclick = () => {
        this.navigateTo('/pages/test_page.html', knowledgeId, true, true);
      };
    } else {
      // 使用新的跳跃学习检查逻辑
      const jumpResult = this.graphState.canJumpToKnowledge(knowledgeId);
      if (jumpResult.canJump) {
        status.textContent = '您可以开始学习该知识点或直接进行测试';
        learnBtn.onclick = () => {
          this.navigateTo('/pages/learning_page.html', knowledgeId);
        };
        testBtn.onclick = () => {
          this.navigateTo('/pages/test_page.html', knowledgeId, true, true);
        };
      } else {
        // 检查是否是跳跃学习场景
        if (currentKnowledgeId && currentKnowledgeId !== knowledgeId) {
          const scenarioResult = this.graphState.checkJumpLearningScenario(currentKnowledgeId, knowledgeId);
          this.handleJumpLearningScenario(scenarioResult, knowledgeId, nodeLabel, learnBtn, testBtn, status);
        } else {
          // 使用原有的解锁逻辑
          this.handleNormalUnlockScenario(jumpResult, knowledgeId, nodeLabel, learnBtn, testBtn, status);
        }
      }
    }
    modal.style.display = 'block';

    // 添加关闭功能
    const closeModal = (event) => {
      if (event.target === modal) {
        modal.style.display = 'none';
      }
    };
    modal.onclick = closeModal;
  }

  // 处理跳跃学习场景（新增方法）
  handleJumpLearningScenario(scenarioResult, knowledgeId, nodeLabel, learnBtn, testBtn, status) {
    switch (scenarioResult.scenario) {
      case 'direct_access':
        // 情况一：完成了所有前置条件，可以直接进入目标知识点
        status.textContent = '您已完成所有前置条件，可以直接进入该知识点学习';
        learnBtn.onclick = () => {
          this.navigateTo('/pages/learning_page.html', knowledgeId);
        };
        testBtn.onclick = () => {
          this.navigateTo('/pages/test_page.html', knowledgeId, true, true);
        };
        break;

      case 'knowledge_required':
        // 情况二：需要先完成前置知识点测试
        if (scenarioResult.intermediateKnowledge) {
          // 需要先进入中间知识点
          status.textContent = `需要先完成"${this.graphState.getKnowledgeLabel(scenarioResult.requiredTest)}"的测试。您可以选择进入"${this.graphState.getKnowledgeLabel(scenarioResult.intermediateKnowledge)}"学习，或直接测试前置知识点。`;

          learnBtn.textContent = `进入${this.graphState.getKnowledgeLabel(scenarioResult.intermediateKnowledge)}`;
          learnBtn.onclick = () => {
            this.navigateTo('/pages/learning_page.html', scenarioResult.intermediateKnowledge);
          };

          testBtn.textContent = `测试${this.graphState.getKnowledgeLabel(scenarioResult.requiredTest)}`;
          testBtn.onclick = () => {
            this.navigateTo('/pages/test_page.html', scenarioResult.requiredTest, true, true);
          };
        } else {
          // 直接需要前置知识点测试
          status.textContent = `需要先完成"${this.graphState.getKnowledgeLabel(scenarioResult.requiredTest)}"的测试`;
          learnBtn.disabled = true;
          learnBtn.className += ' disabled';
          learnBtn.onclick = () => { };

          testBtn.textContent = `测试${this.graphState.getKnowledgeLabel(scenarioResult.requiredTest)}`;
          testBtn.onclick = () => {
            this.navigateTo('/pages/test_page.html', scenarioResult.requiredTest, true, true);
          };
        }
        break;

      case 'chapter_locked':
        // 情况三：章节未解锁
        status.textContent = scenarioResult.message;
        learnBtn.disabled = true;
        learnBtn.className += ' disabled';
        learnBtn.onclick = () => { };

        testBtn.textContent = `测试第${scenarioResult.requiredTest.split('_')[0]}章`;
        testBtn.onclick = () => {
          this.navigateTo('/pages/test_page.html', scenarioResult.requiredTest, true, true);
        };
        break;

      default:
        // 正常学习进度
        status.textContent = '正常学习进度，您可以开始学习该知识点';
        learnBtn.onclick = () => {
          this.navigateTo('/pages/learning_page.html', knowledgeId);
        };
        testBtn.onclick = () => {
          this.navigateTo('/pages/test_page.html', knowledgeId, true, true);
        };
    }
  }

  // 处理正常解锁场景（新增方法）
  handleNormalUnlockScenario(jumpResult, knowledgeId, nodeLabel, learnBtn, testBtn, status) {
    if (jumpResult.reason === 'chapter_locked') {
      // 章节未解锁 - 使用"是"和"否"按钮
      status.textContent = `您还未完成前置章节"${jumpResult.requiredChapterName}"的测试，需要先完成该章节的测试才能学习本知识点。是否现在开始测试前置章节？`;
      learnBtn.textContent = '是';
      learnBtn.className = 'learn-btn';
      learnBtn.disabled = false;
      testBtn.textContent = '否';
      testBtn.className = 'test-btn';

      learnBtn.onclick = () => {
        // 跳转到前一章节的章节测试
        console.log('[DEBUG] jumpResult.requiredChapter:', jumpResult.requiredChapter);
        const previousChapterNum = parseInt(jumpResult.requiredChapter.replace('chapter', ''));
        const chapterTestId = `${previousChapterNum}_end`;
        console.log('[DEBUG] previousChapterNum:', previousChapterNum);
        console.log('[DEBUG] chapterTestId:', chapterTestId);
        console.log('[DEBUG] 准备跳转到:', `/pages/test_page.html?topic=${chapterTestId}`);

        // 存储跳跃学习目标知识点
        const jumpTarget = {
          knowledgeId: knowledgeId,
          label: nodeLabel,
          timestamp: Date.now()
        };
        localStorage.setItem('jumpLearningTarget', JSON.stringify(jumpTarget));
        console.log('[DEBUG] 存储跳跃学习目标:', jumpTarget);

        this.navigateTo('/pages/test_page.html', chapterTestId, true, true);
      };

      testBtn.onclick = () => {
        document.getElementById('knowledgeModal').style.display = 'none';
      };
    } else if (jumpResult.reason === 'previous_knowledge_required' || jumpResult.reason === 'previous_chapter_test_required') {
      // 需要完成前置知识点测试或章节测试 - 使用"是"和"否"按钮
      const isChapterTest = jumpResult.reason === 'previous_chapter_test_required';
      const testType = isChapterTest ? '章节测试' : '知识点测试';
      status.textContent = `您还未学习前置知识点"${jumpResult.requiredKnowledgeName}"，需要先完成该知识点的测试才能学习本知识点。是否现在开始测试前置知识点？`;
      learnBtn.textContent = '是';
      learnBtn.className = 'learn-btn';
      learnBtn.disabled = false;
      testBtn.textContent = '否';
      testBtn.className = 'test-btn';

      learnBtn.onclick = () => {
        console.log('[DEBUG] jumpResult.reason:', jumpResult.reason);
        console.log('[DEBUG] jumpResult.requiredKnowledgeId:', jumpResult.requiredKnowledgeId);
        console.log('[DEBUG] 准备跳转到:', `/pages/test_page.html?topic=${jumpResult.requiredKnowledgeId}`);

        // 存储跳跃学习目标知识点
        const jumpTarget = {
          knowledgeId: knowledgeId,
          label: nodeLabel,
          timestamp: Date.now()
        };
        localStorage.setItem('jumpLearningTarget', JSON.stringify(jumpTarget));
        console.log('[DEBUG] 存储跳跃学习目标:', jumpTarget);

        this.navigateTo('/pages/test_page.html', jumpResult.requiredKnowledgeId, true, true);
      };

      testBtn.onclick = () => {
        document.getElementById('knowledgeModal').style.display = 'none';
      };
    } else {
      // 其他情况，使用原有逻辑
      status.textContent = '该知识点尚未解锁，您是否要直接开始测试？';
      learnBtn.disabled = true;
      learnBtn.className += ' disabled';
      learnBtn.onclick = () => { };
      testBtn.onclick = () => {
        this.navigateTo('/pages/test_page.html', knowledgeId, true, true);
      };
    }
  }

  // 导航到指定页面
  navigateTo(page, topicId, isTest = false, forceTest = false) {
    // 使用导入的navigateTo函数
    navigateTo(page, topicId, isTest, forceTest);
  }

  // 恢复节点样式到正确状态
  restoreNodeStyle(node) {
    const id = node.id();
    const type = node.data('type');
    const originalSize = this.originalSizes.get(id);

    // 先恢复到原始尺寸
    if (originalSize) {
      node.style({
        'width': originalSize.width,
        'height': originalSize.height
      });
    }

    // 获取当前学习节点ID
    let currentLearningNodeId = null;
    try {
      // 获取URL中的topic参数
      const topicData = getUrlParam('topic');
      if (topicData && topicData.id) {
        currentLearningNodeId = topicData.id;
      }
    } catch (error) {
      console.warn('获取当前学习节点失败:', error);
    }

    // 检查节点是否为当前学习节点，优先处理
    if (id === currentLearningNodeId) {
      // 当前学习节点始终为橙色，无论其他状态如何
      node.style({
        'background-color': '#f59e0b',
        'border-color': '#d97706'
      });
      return; // 直接返回，不再应用其他样式
    }

    // 处理非当前学习状态的节点
    if (type === 'chapter') {
      if (this.graphState.currentLearningChapter === id) {
        node.style({
          'background-color': '#f59e0b',
          'border-color': '#d97706'
        });
      } else if (this.graphState.isChapterCompleted(id)) {
        node.style({
          'background-color': '#10b981',
          'border-color': '#059669'
        });
      } else if (this.graphState.canLearnChapter(id)) {
        node.style({
          'background-color': '#3b82f6',
          'border-color': '#2563eb'
        });
      } else {
        node.style({
          'background-color': '#9ca3af',
          'border-color': '#6b7280'
        });
      }
    } else {
      if (this.graphState.learnedNodes.includes(id)) {
        node.style({
          'background-color': '#10b981',
          'border-color': '#059669'
        });
      } else if (this.graphState.isKnowledgeUnlocked(id)) {
        node.style({
          'background-color': '#3b82f6',
          'border-color': '#2563eb'
        });
      } else {
        node.style({
          'background-color': '#9ca3af',
          'border-color': '#6b7280'
        });
      }
    }
  }

  // 添加更新原始尺寸的方法
  updateOriginalSizes() {
    this.cy.nodes().forEach(node => {
      this.originalSizes.set(node.id(), {
        width: parseFloat(node.style('width')),
        height: parseFloat(node.style('height'))
      });
    });
  }

  // 设置章节固定位置 - 优化布局
  setFixedChapterPositions() {
    const chapterNodes = this.cy.nodes('[type="chapter"]');
    const containerWidth = this.cy.container().clientWidth;

    // 增加间距系数，从2.5增加到4.0，使章节之间间距更大
    const spacingFactor = 4.0;
    const baseSpacing = containerWidth / (chapterNodes.length + 1);
    const actualSpacing = baseSpacing * spacingFactor;

    // 将所有节点放在同一水平线上
    const y = this.layoutParams.TOP_ROW_Y;

    chapterNodes.forEach((node, idx) => {
      // 使用调整后的间距
      const x = (idx + 1) * actualSpacing;

      // 所有节点都使用同一个 y 坐标
      node.position({ x, y });
      node.lock();
      this.graphState.fixedPositions[node.id()] = { x, y };

      // 给每个章节存一个标记，后面知识点布局直接用
      node.data('rowIndex', idx);
    });
  }

  // 隐藏所有知识点
  hideAllKnowledgeNodes() {
    this.cy.nodes().forEach(n => {
      if (n.data('type') === 'knowledge') n.hide();
    });
    // 更新边可见性
    this.updateEdgesVisibility();
  }

  // 确保知识点位置
  ensurePositionsForChapterKnowledge(chapterId) {
    const kids = this.graphState.collectKnowledgeDescendantsForDisplay(chapterId);
    if (!kids || kids.length === 0) return;
    const anySet = kids.some(id => this.graphState.fixedPositions[id]);
    if (anySet) return;

    const chapterNode = this.cy.getElementById(chapterId);
    if (!chapterNode || chapterNode.length === 0) return;

    const chapterPos = chapterNode.position();
    const idx = chapterNode.data('rowIndex') || 0;
    const isTop = idx % 2 === 0;

    // 减小知识点与章节之间的距离，使连线更短
    const baseY = chapterPos.y + this.layoutParams.KNOWLEDGE_ROW_DELTA_Y * 0.6;

    const n = kids.length;
    const maxWidth = this.cy.container().clientWidth * 1;  // 减小横向宽度，使知识点更集中
    const gap = Math.min(this.layoutParams.KNOWLEDGE_GAP_X * 0.8, maxWidth / Math.max(n, 4));  // 减小间距 
    const half = (n - 1) / 2;
    const slopeStep = (this.layoutParams.KNOWLEDGE_HEIGHT_STEP || 25) * 0.7;  // 减小高度步进

    kids.forEach((id, i) => {
      const x = chapterPos.x + (i - half) * gap;
      const y = baseY;

      this.graphState.fixedPositions[id] = { x, y };
    });
  }

  // 更新边可见性
  updateEdgesVisibility() {
    this.cy.edges().forEach(e => {
      const s = e.data('source'), t = e.data('target');
      const sn = this.cy.getElementById(s), tn = this.cy.getElementById(t);
      if (sn && tn && sn.length && tn.length && sn.visible() && tn.visible()) {
        e.style({
          'opacity': 0,
          'curve-style': 'straight',  // 确保使用直线连接
          'edge-distances': 'intersection',  // 从节点边缘开始连线
          'arrow-scale': 2  // 保持一致的箭头尺寸
        });
        e.show();

        // 淡入动画
        e.animate({
          style: {
            'opacity': 1
          }
        }, {
          duration: 300
        });
      } else {
        e.hide();
      }
    });
  }

  bindLayoutEvents() {
    // 窗口大小改变时重新布局
    window.addEventListener('resize', () => {
      this.debounceCenterAndZoom();
    });

    // 节点位置变化时重新调整
    this.cy.on('position', 'node', () => {
      this.debounceCenterAndZoom();
    });
  }

  debounceCenterAndZoom() {
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      /* this.adjustLayoutToAvoidOverlap(); */// 添加自动布局调整功能
      this.centerAndZoomGraph();
    }, 100);
  }

  // 居中缩放图谱
  centerAndZoomGraph() {
    const nodes = this.cy.nodes().filter(node => node.visible());
    if (nodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    nodes.forEach(node => {
      const pos = node.position();
      const width = parseFloat(node.style('width')) || 0;
      const height = parseFloat(node.style('height')) || 0;

      minX = Math.min(minX, pos.x - width / 2);
      maxX = Math.max(maxX, pos.x + width / 2);
      minY = Math.min(minY, pos.y - height / 2);
      maxY = Math.max(maxY, pos.y + height / 2);
    });

    // 减少边距，创建更紧凑的布局
    const margin = 20; // 减少边距
    minX -= margin + 20;
    maxX += margin;
    minY -= margin;
    maxY += margin;

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const width = maxX - minX;
    const height = maxY - minY;

    const container = this.cy.container();
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;

    // 检查是否处于收起状态（高度接近40px）
    const isCollapsed = containerHeight <= 50; // 收起状态高度阈值

    let scale, panX, panY;

    if (isCollapsed) {
      // 使用固定的缩放比例，确保图谱可见
      scale = Math.min(0.3, 1.2) * 0.95; // 收起时使用较小但可见的缩放比例

      // 在收起状态下居中显示
      panX = -centerX * scale + containerWidth / 2;
      panY = -centerY * scale + containerHeight / 2;
    } else {
      // 展开状态下的正常处理
      const scaleX = containerWidth / width;
      const scaleY = containerHeight / height;
      scale = Math.min(scaleX, scaleY, 1.2) * 0.95; // 稍微增加缩放比例

      panX = -centerX * scale + containerWidth / 2;
      panY = -centerY * scale + containerHeight / 2;
    }

    this.cy.animate({
      zoom: scale,
      pan: { x: panX, y: panY },
      duration: 300
    });
  }

  // 刷新图谱数据
  async refresh() {
    this.isInitialized = false;
    if (this.cy) {
      this.cy.destroy();
      this.cy = null;
    }
    await this.init();
  }

  // 销毁实例
  destroy() {
    if (this.cy) {
      this.cy.destroy();
    }
    this.isInitialized = false;
  }

  // 显示知识图谱容器的方法
  showKnowledgeGraphContainer() {
    // 调用全局函数显示知识图谱
    if (typeof window.showKnowledgeGraph === 'function') {
      window.showKnowledgeGraph();
    } else {
      // 如果全局函数不存在，使用原来的逻辑
      console.warn('[MiniKnowledgeGraph] 全局showKnowledgeGraph函数不存在，使用默认逻辑');
      const knowledgeGraphContainer = document.getElementById('knowledge-graph-container');

      // 如果找到了容器元素，则显示它
      if (knowledgeGraphContainer) {
        knowledgeGraphContainer.style.display = 'block';

        // 更新图标状态
        const toggleIcon = document.getElementById('toggleIcon');
        if (toggleIcon) {
          toggleIcon.setAttribute('icon', 'mdi:chevron-up');
          toggleIcon.style.color = '#3730a3'; // 更深的紫色
          toggleIcon.style.opacity = '1';     // 完全不透明
        }
      }
    }
  }

  // 获取前置知识点信息
  getPrerequisiteInfo(knowledgeId) {
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
}

// 默认导出
export default MiniKnowledgeGraph;