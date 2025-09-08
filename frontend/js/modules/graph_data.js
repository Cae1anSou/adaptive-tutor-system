// graphData.js - 数据与状态管理

// 布局参数
export const LAYOUT_PARAMS = {
  TOP_ROW_Y: 150,// 顶部行的Y位置
  ROW_DELTA_Y: 180,//  底部行的Y间隔
  KNOWLEDGE_TOP_ROW_Y: 120,// 知识点顶部行的Y位置
  KNOWLEDGE_ROW_DELTA_Y: 380,// 知识点底部行的Y间隔
  KNOWLEDGE_GAP_X: 220,// 知识点间的水平间距
  KNOWLEDGE_HEIGHT_STEP: 80 // 知识点高度步进值
};

// 状态管理类
export class GraphState {
  constructor(graphData, learnedNodes = []) {
    // 验证传入的图数据格式
    if (!this.validateGraphData(graphData)) {
      console.warn('传入的图谱数据格式不正确，使用默认结构');
      graphData = { nodes: [], edges: [], dependent_edges: [] };
    }
    // 深度克隆传入的数据以避免引用问题
    this.graphData = graphData ? {
      nodes: [...(graphData.nodes || [])],
      edges: [...(graphData.edges || [])],
      dependent_edges: [...(graphData.dependent_edges || [])]
    } : { nodes: [], edges: [], dependent_edges: [] };

    // 确保learnedNodes是数组
    this.learnedNodes = Array.isArray(learnedNodes) ? [...learnedNodes] : [];

    // 初始化其他状态
    this.chaptersPassed = new Set();
    this.expandedSet = new Set();
    this.currentLearningChapter = null;
    this.fixedPositions = {};

    // 初始化映射关系
    this.displayMap = {};
    this.depMap = {};
    this.prereqMap = {};
    this.parentMap = {};
  }

  // 初始化映射
  initMaps() {
    // 深度检查graphData结构
    if (!this.graphData || typeof this.graphData !== 'object') {
      console.error('graphData 未正确初始化', this.graphData);
      return;
    }

    // 确保必要属性存在，提供默认值
    this.graphData.edges = this.graphData.edges || [];
    this.graphData.dependent_edges = this.graphData.dependent_edges || [];
    this.graphData.nodes = this.graphData.nodes || [];

    // 确保learnedNodes是数组
    this.learnedNodes = Array.isArray(this.learnedNodes) ? this.learnedNodes : [];

    try {
      // 构建显示映射 - 添加额外的安全检查
      if (Array.isArray(this.graphData.edges)) {
        this.graphData.edges.forEach(e => {
          if (e && e.data) {
            const s = e.data.source, t = e.data.target;
            if (s && t) {
              this.displayMap[s] = this.displayMap[s] || [];
              this.displayMap[s].push(t);
            }
          }
        });
      }

      // 构建依赖映射
      if (Array.isArray(this.graphData.dependent_edges)) {
        this.graphData.dependent_edges.forEach(e => {
          if (e && e.data) {
            const s = e.data.source, t = e.data.target;
            if (s && t) {
              this.depMap[s] = this.depMap[s] || [];
              this.depMap[s].push(t);
            }
          }
        });
      }

      // 构建前置映射
      if (Array.isArray(this.graphData.dependent_edges)) {
        this.graphData.dependent_edges.forEach(e => {
          if (e && e.data) {
            const s = e.data.source, t = e.data.target;
            if (s && t) {
              this.prereqMap[t] = this.prereqMap[t] || [];
              this.prereqMap[t].push(s);
            }
          }
        });
      }

      // 构建父映射
      if (Array.isArray(this.graphData.edges)) {
        this.graphData.edges.forEach(e => {
          if (e && e.data) {
            const s = e.data.source, t = e.data.target;
            if (s && t) {
              this.parentMap[t] = this.parentMap[t] || [];
              this.parentMap[t].push(s);
            }
          }
        });
      }
    } catch (error) {
      console.error('初始化映射失败:', error);
      throw new Error('图谱数据格式不正确');
    }
  }

  // 验证图数据结构
  validateGraphData(data) {
    if (!data) return false;
    if (!Array.isArray(data.nodes)) return false;
    if (!Array.isArray(data.edges)) return false;

    // 检查edges基本结构
    const edgesValid = data.edges.every(edge =>
      edge && edge.data && edge.data.source && edge.data.target
    );

    // 检查nodes基本结构
    const nodesValid = data.nodes.every(node =>
      node && node.data && node.data.id
    );

    return edgesValid && nodesValid;
  }
  // 更新学习状态
  updateLearnedNodes(newLearnedNodes) {
    this.learnedNodes = newLearnedNodes;
  }

  // 节点类型判断
  isKnowledge(id) {
    return id.startsWith('text_') || id.startsWith('structure_') ||
      id.startsWith('form_') || id.startsWith('style_') ||
      id.startsWith('media_') || id.startsWith('js_');
  }

  // 收集知识点后代
  collectKnowledgeDescendantsForDisplay(rootId) {
    const out = [];
    const visited = new Set();

    const dfs = (u) => {
      (this.displayMap[u] || []).forEach(v => {
        if (visited.has(v)) return;
        visited.add(v);

        const node = this.graphData.nodes.find(n => n.data && n.data.id === v);
        const type = node && node.data && node.data.type ? node.data.type : '';

        if (type === 'chapter') {
          return; // 跳过章节节点
        } else {
          out.push(v);
        }
        dfs(v);
      });
    };

    dfs(rootId);
    return out;
  }

  // 知识点解锁判断（使用与canJumpToKnowledge相同的逻辑）
  isKnowledgeUnlocked(knowledgeId) {
    // 同步localStorage中的已学习知识点
    this.syncLearnedNodesFromStorage();

    // 使用与canJumpToKnowledge相同的逻辑
    const jumpResult = this.canJumpToKnowledge(knowledgeId);
    return jumpResult.canJump;
  }

  // 检查知识点是否可以跳跃学习（新规则：章节测试解锁下一章节，知识点间需要内部解锁）
  canJumpToKnowledge(knowledgeId) {
    // 同步localStorage中的已学习知识点
    this.syncLearnedNodesFromStorage();

    // 解析知识点ID，获取章节和序号
    const [chapter, section] = knowledgeId.split('_').map(Number);

    // 如果是第一章第一个知识点，直接可以学习
    if (chapter === 1 && section === 1) {
      return { canJump: true, reason: 'first_knowledge' };
    }

    // 检查章节是否解锁（章节测试解锁下一章节）
    const chapterId = `chapter${chapter}`;
    if (!this.canLearnChapter(chapterId)) {
      return {
        canJump: false,
        reason: 'chapter_locked',
        requiredChapter: `chapter${chapter - 1}`,
        requiredChapterName: `第${chapter - 1}章`
      };
    }

    // 检查知识点前置条件（知识点间需要内部解锁）
    if (section > 1) {
      // 检查同章节的前一个知识点
      const previousKnowledgeId = `${chapter}_${section - 1}`;
      if (!this.learnedNodes.includes(previousKnowledgeId)) {
        return {
          canJump: false,
          reason: 'previous_knowledge_required',
          requiredKnowledgeId: previousKnowledgeId,
          requiredKnowledgeName: this.getKnowledgeLabel(previousKnowledgeId)
        };
      }
    } else if (chapter > 1) {
      // 检查前一章节的章节测试
      const previousChapterTestId = `${chapter - 1}_end`; // 章节测试ID格式：{章节号}_end
      if (!this.learnedNodes.includes(previousChapterTestId)) {
        return {
          canJump: false,
          reason: 'previous_chapter_test_required',
          requiredKnowledgeId: previousChapterTestId,
          requiredKnowledgeName: `第${chapter - 1}章章节测试`
        };
      }
    }

    return { canJump: true, reason: 'unlocked' };
  }

  // 检查跳跃学习场景的具体情况（新增方法）
  checkJumpLearningScenario(fromKnowledgeId, toKnowledgeId) {
    // 同步localStorage中的已学习知识点
    this.syncLearnedNodesFromStorage();

    // 解析知识点ID
    const [fromChapter, fromSection] = fromKnowledgeId.split('_').map(Number);
    const [toChapter, toSection] = toKnowledgeId.split('_').map(Number);

    // 检查是否是跨章节跳跃
    if (toChapter > fromChapter) {
      // 检查目标章节是否解锁
      const targetChapterId = `chapter${toChapter}`;
      if (!this.canLearnChapter(targetChapterId)) {
        return {
          scenario: 'chapter_locked',
          message: `第${toChapter}章尚未解锁，需要先完成第${toChapter - 1}章的章节测试`,
          requiredTest: `${toChapter - 1}_end`
        };
      }

      // 检查目标知识点是否需要前置知识点测试
      if (toSection > 1) {
        const previousKnowledgeId = `${toChapter}_${toSection - 1}`;
        if (!this.learnedNodes.includes(previousKnowledgeId)) {
          return {
            scenario: 'knowledge_required',
            message: `需要先完成"${this.getKnowledgeLabel(previousKnowledgeId)}"的测试`,
            requiredTest: previousKnowledgeId,
            intermediateKnowledge: `${toChapter}_1` // 需要先进入该章节的第一个知识点
          };
        }
      }

      // 情况一：完成了所有前置条件，可以直接进入目标知识点
      return {
        scenario: 'direct_access',
        message: '可以直接进入目标知识点学习',
        targetKnowledge: toKnowledgeId
      };
    }

    // 同章节内的跳跃
    if (toChapter === fromChapter && toSection > fromSection + 1) {
      // 检查是否需要前置知识点测试
      const previousKnowledgeId = `${toChapter}_${toSection - 1}`;
      if (!this.learnedNodes.includes(previousKnowledgeId)) {
        return {
          scenario: 'knowledge_required',
          message: `需要先完成"${this.getKnowledgeLabel(previousKnowledgeId)}"的测试`,
          requiredTest: previousKnowledgeId
        };
      }
    }

    return {
      scenario: 'normal_progression',
      message: '正常学习进度'
    };
  }

  // 获取知识点标签（辅助方法）
  getKnowledgeLabel(knowledgeId) {
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
  }

  // 章节学习判断
  canLearnChapter(chapterId) {
    const idx = parseInt(chapterId.replace('chapter', ''));
    if (idx === 1) return true;
    return this.isChapterCompleted(`chapter${idx - 1}`);
  }

  // 章节完成判断
  isChapterCompleted(chapterId) {
    // 首先检查localStorage中的已完成章节
    try {
      const completedChapters = JSON.parse(localStorage.getItem('completedChapters') || '[]');
      if (completedChapters.includes(chapterId)) {
        return true;
      }
    } catch (error) {
      console.error('读取已完成章节时出错:', error);
    }

    // 然后检查原有的逻辑
    const ks = this.collectKnowledgeDescendantsForDep(chapterId);
    if (ks.length === 0) return false;
    const allLearned = ks.every(id => this.learnedNodes.includes(id));
    return allLearned && this.chaptersPassed.has(chapterId);
  }

  // 收集依赖知识点
  collectKnowledgeDescendantsForDep(rootId) {
    const out = new Set();
    const visited = new Set();
    const queue = [rootId];

    while (queue.length > 0) {
      const currentId = queue.shift();
      if (visited.has(currentId)) continue;
      visited.add(currentId);

      (this.depMap[currentId] || []).forEach(cid => {
        const node = this.graphData.nodes.find(n => n.data && n.data.id === cid);
        const type = node && node.data && node.data.type ? node.data.type : '';

        if (type !== 'chapter') {
          out.add(cid);
          queue.push(cid);
        }
      });
    }
    return Array.from(out);
  }

  // 章节测试通过
  passChapterTest(chapterId) {
    const ks = this.collectKnowledgeDescendantsForDep(chapterId);
    const allLearned = ks.length > 0 && ks.every(id => this.learnedNodes.includes(id));

    if (!allLearned) {
      console.log("该章节仍有知识点未学完");
      return false;
    }

    this.chaptersPassed.add(chapterId);
    if (this.currentLearningChapter === chapterId) {
      this.currentLearningChapter = null;
    }
    console.log(`恭喜！你已通过 ${chapterId} 的章节测试`);
    return true;
  }

  // 从localStorage同步已学习的知识点
  syncLearnedNodesFromStorage() {
    try {
      const storedLearnedNodes = JSON.parse(localStorage.getItem('learnedNodes') || '[]');
      // 合并已学习的知识点，避免重复
      storedLearnedNodes.forEach(nodeId => {
        if (!this.learnedNodes.includes(nodeId)) {
          this.learnedNodes.push(nodeId);
        }
      });
    } catch (error) {
      console.error('从localStorage同步已学习知识点时出错:', error);
    }
  }
}