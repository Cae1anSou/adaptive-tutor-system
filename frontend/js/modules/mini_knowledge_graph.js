// modules/mini_knowledge_graph.js
import { GraphState } from './graph_data.js';
import { buildBackendUrl } from './config.js';
import { getParticipantId } from './session.js';

export class MiniKnowledgeGraph {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.options = {
      height: 200,
      nodeSize: 20,
      chapterNodeSize: 30,
      fontSize: 10,
      ...options
    };
    
    this.cy = null;
    this.graphState = null;
    this.isInitialized = false;
  }

  // 初始化简化知识图谱
  async init() {
    if (this.isInitialized) return;
    
    try {
      const participantId = getParticipantId();
      if (!participantId) {
        console.warn('未找到用户ID，无法加载简化知识图谱');
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
      
      this.isInitialized = true;
      console.log('简化知识图谱初始化完成');
      
    } catch (error) {
      console.error('初始化简化知识图谱失败:', error);
    }
  }

  // 创建Cytoscape实例
  createCytoscapeInstance() {
    this.cy = cytoscape({
      container: document.getElementById(this.containerId),
      style: [
        {
          selector: 'node',
          style: {
            'label': '',
            'text-valign': 'center',
            'text-halign': 'center',
            'background-color': '#9ca3af',
            'width': this.options.nodeSize,
            'height': this.options.nodeSize,
            'shape': 'ellipse',
            'border-width': 1,
            'border-color': '#6b7280',
            'transition': 'all 0.3s ease'
          }
        },
        {
          selector: 'node[type="chapter"]',
          style: {
            'shape': 'roundrectangle',
            'width': this.options.chapterNodeSize,
            'height': this.options.chapterNodeSize,
            'background-color': '#4f46e5',
            'border-width': 2,
            'border-color': '#3730a3'
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
            'width': 1,
            'line-color': '#cbd5e1',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#cbd5e1',
            'curve-style': 'bezier',
            'arrow-scale': 0.8
          }
        }
      ],
      minZoom: 0.1,
      maxZoom: 1.0,
      wheelSensitivity: 0.2
    });
  }

  // 更新节点状态
  updateNodeStates() {
    this.cy.nodes().forEach(node => {
      const id = node.id();
      const type = node.data('type');
      
      if (type === 'chapter') {
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
        if (this.graphState.learnedNodes.includes(id)) {
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
    this.cy.layout({
      name: 'cose',
      idealEdgeLength: 80,
      nodeOverlap: 20,
      refresh: 20,
      fit: true,
      padding:0,
      randomize: false,
      componentSpacing: 40,
      nodeRepulsion: 2048,
      edgeElasticity: 32,
      nestingFactor: 0.1,
      gravity: 0.25,
      numIter: 1000,
      initialTemp: 200,
      coolingFactor: 0.95,
      minTemp: 1.0
    }).run();
  }

  // 设置交互效果
  setupInteractions() {
    const tooltip = this.createTooltip();
    
    // 悬停显示标签
    this.cy.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      const label = node.data('label') || node.id();
      
      // 显示标签
      node.style({
        'label': label,
        'font-size': `${this.options.fontSize}px`,
        'text-background-color': 'white',
        'text-background-opacity': 0.9,
        'text-background-padding': '2px',
        'text-border-width': 1,
        'text-border-color': '#e2e8f0'
      });
      
      // 显示工具提示
      this.showTooltip(tooltip, node, label);
    });
    
    // 离开隐藏标签
    this.cy.on('mouseout', 'node', (evt) => {
      const node = evt.target;
      
      // 隐藏标签
      node.style({
        'label': '',
        'text-background-opacity': 0
      });
      
      // 隐藏工具提示
      this.hideTooltip(tooltip);
    });
    
    // 禁用点击交互
    this.cy.on('tap', (evt) => {
      evt.preventDefault();
      evt.stopPropagation();
    });
  }

  // 创建工具提示
  createTooltip() {
    const tooltip = document.createElement('div');
    tooltip.className = 'mini-graph-tooltip';
    tooltip.style.cssText = `
      position: absolute;
      background: rgba(255, 255, 255, 0.95);
      border: 1px solid #e5e7eb;
      border-radius: 6px;
      padding: 4px 8px;
      font-size: 12px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
      z-index: 1000;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s ease;
      max-width: 200px;
    `;
    
    document.getElementById(this.containerId).appendChild(tooltip);
    return tooltip;
  }

  // 显示工具提示
  showTooltip(tooltip, node, text) {
    const position = node.renderedPosition();
    const container = this.cy.container();
    const rect = container.getBoundingClientRect();
    
    tooltip.textContent = text;
    tooltip.style.left = (position.x + rect.left + 20) + 'px';
    tooltip.style.top = (position.y + rect.top - 10) + 'px';
    tooltip.style.opacity = '1';
  }

  // 隐藏工具提示
  hideTooltip(tooltip) {
    tooltip.style.opacity = '0';
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
}

// 默认导出
export default MiniKnowledgeGraph;