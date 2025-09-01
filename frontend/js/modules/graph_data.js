// graphData.js - 数据与状态管理

// 布局参数
export const LAYOUT_PARAMS = {
  TOP_ROW_Y: 150,// 顶部行的Y位置
  ROW_DELTA_Y: 180,//  底部行的Y间隔
  KNOWLEDGE_TOP_ROW_Y: 120,// 知识点顶部行的Y位置
  KNOWLEDGE_ROW_DELTA_Y: 380,// 知识点底部行的Y间隔
  KNOWLEDGE_GAP_X: 170,// 知识点间的水平间距
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

  // 知识点解锁判断
  isKnowledgeUnlocked(knowledgeId) {
    const pres = this.prereqMap[knowledgeId] || [];
    const node = this.graphData.nodes.find(n => n.data && n.data.id === knowledgeId);
    const type = node && node.data && node.data.type ? node.data.type : '';

    return pres.every(pid => {
      const preNode = this.graphData.nodes.find(n => n.data && n.data.id === pid);
      const preType = preNode && preNode.data && preNode.data.type ? preNode.data.type : '';
      
      if (preType === 'chapter') {
        return this.canLearnChapter(pid); // 如果是章节节点，检查章节是否可学
      } else {
        return this.learnedNodes.includes(pid); // 否则检查是否已学
      }
    });
  }

  // 章节学习判断
  canLearnChapter(chapterId) {
    const idx = parseInt(chapterId.replace('chapter', ''));
    if (idx === 1) return true;
    return this.isChapterCompleted(`chapter${idx - 1}`);
  }

  // 章节完成判断
  isChapterCompleted(chapterId) {
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
}