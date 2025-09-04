/* ============================
   graph_renderer.js
   功能：
   - 初始化 Cytoscape
   - 固定章节位置
   - 布局知识点
   - 随窗口调整中心和缩放
   ============================ */
// graphRenderer.js - 图谱渲染与布局

import { LAYOUT_PARAMS } from './graph_data.js';
import { getUrlParam } from './navigation.js';

// 图谱渲染类
export class GraphRenderer {
  constructor(containerId, graphState) {
    this.cy = cytoscape({
      container: document.getElementById(containerId),
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'color': '#1e293b',
            'background-color': '#f1f5f9',
            'width': 120,
            'height': 120,
            'font-size': '14px',
            'font-family': 'Inter, sans-serif',
            'font-weight': '500',
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
            'width': 200,
            'height': 80,
            'background-color': '#4f46e5',
            'color': '#1e293b',
            'border-width': 3,
            'border-color': '#3730a3',
            'font-size': '16px'
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
            'width': 3,
            'line-color': '#2563eb',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': '#2563eb',
            'curve-style': 'unbundled-bezier',
            'control-point-step-size': 80,
            'control-point-distance': 60,
            'control-point-weight': 0.4,
            'arrow-scale': 1.8,
            'line-style': 'solid',
            'transition-property': 'line-color, width, target-arrow-color',
            'transition-duration': '0.3s',
            'transition-timing-function': 'ease'
          }
        },
        {
          // 章节到章节的边样式
          selector: 'edge.chapter-to-chapter',
          style: {
            'line-color': '#4f46e5',
            'target-arrow-color': '#4f46e5',
            'width': 4,
            'line-style': 'solid',
            'opacity': 0.9
          }
        },
        {
          // 章节到知识点的边样式
          selector: 'edge.chapter-to-knowledge',
          style: {
            'line-color': '#f59e0b',
            'target-arrow-color': '#f59e0b',
            'width': 2.5,
            'line-style': 'dashed',
            'opacity': 0.8
          }
        },
        {
          // 边悬停效果
          selector: 'edge.hover',
          style: {
            'width': 5,
            'opacity': 1,
            'line-color': '#facc15',  // 悬停时使用更明亮的颜色
            'target-arrow-color': '#facc15'
          }
        },
        {
          // 边光效动画
          selector: 'edge.edge-glow',
          style: {
            'line-gradient-stop-colors': '#facc15 #facc15 #f59e0b #f59e0b',
            'line-gradient-stop-positions': '0 0.5 0.5 1'
          }
        }
      ],
      layout: { name: 'preset' },
      minZoom: 0.2,
      maxZoom: 2.0,
      wheelSensitivity: 0.2
    });
    this.graphState = graphState;
    this.layoutParams = LAYOUT_PARAMS;
    this.debounceTimer = null; // 初始化防抖计时器
    // 存储节点的原始尺寸
    this.originalSizes = new Map();
    
    // 添加鼠标事件监听器来模拟悬停效果
    this.setupHoverEffects();
  }

  // 添加网格背景
  addGridBackground() {
    const container = this.cy.container();
    if (container) {
      container.classList.add('cy-grid');
    }
  }

  // 添加元素到图谱
  addElements(elements) {
    this.cy.add(elements);

    // 为不同类型的边设置不同的样式类
    this.cy.edges().forEach(edge => {
      const sourceId = edge.data('source');
      const targetId = edge.data('target');
      
      // 获取源节点和目标节点
      const sourceNode = this.cy.getElementById(sourceId);
      const targetNode = this.cy.getElementById(targetId);
      
      // 判断节点类型
      const sourceType = sourceNode.data('type');
      const targetType = targetNode.data('type');
      
      // 章节到知识点的边添加特殊类
      if (sourceType === 'chapter' && targetType === 'knowledge') {
        edge.addClass('chapter-to-knowledge');
      } 
      // 章节到章节的边添加特殊类
      else if (sourceType === 'chapter' && targetType === 'chapter') {
        edge.addClass('chapter-to-chapter');
      }
    });

    // 存储新添加节点的原始尺寸
    this.cy.nodes().forEach(node => {
      if (!this.originalSizes.has(node.id())) {
        this.originalSizes.set(node.id(), {
          width: parseFloat(node.style('width')),
          height: parseFloat(node.style('height'))
        });
      }
    });
  }

    // 设置悬停效果
  setupHoverEffects() {
    // 存储所有节点的原始尺寸
    this.cy.nodes().forEach(node => {
      this.originalSizes.set(node.id(), {
        width: parseFloat(node.style('width')),
        height: parseFloat(node.style('height'))
      });
    });

    // 节点悬停效果 - 添加动画过渡
    this.cy.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      const originalSize = this.originalSizes.get(node.id()) || { width: 120, height: 120 };
      const scaleFactor = node.data('type') === 'chapter' ? 1.15 : 1.1;
      
      // 获取当前学习节点ID
      let currentLearningNodeId = null;
      try {
        const topicData = getUrlParam('topic');
        if (topicData && topicData.id) {
          currentLearningNodeId = topicData.id;
        }
      } catch (error) {
        console.warn('获取当前学习节点失败:', error);
      }
      
      // 根据节点类型和是否为当前学习节点/章节设置悬停样式
      let backgroundColor, borderColor;
      
      if (node.id() === currentLearningNodeId) {
        // 当前学习节点悬停时使用更深的橙色
        backgroundColor = '#d97706';
        borderColor = '#b45309';
      } else if (node.data('type') === 'chapter' && this.graphState.currentLearningChapter === node.id()) {
        // 当前学习章节悬停时也使用更深的橙色
        backgroundColor = '#d97706';
        borderColor = '#b45309';
      } else if (node.data('type') === 'chapter') {
        backgroundColor = '#3730a3';
        borderColor = '#4f46e5';
      } else {
        backgroundColor = '#c7d2fe';
        borderColor = '#4f46e5';
      }
      
      // 使用动画过渡效果
      node.stop().animate({
        style: {
          'background-color': backgroundColor,
          'border-color': borderColor,
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

    // 边悬停效果 - 优化样式变化
    this.cy.on('mouseover', 'edge', (evt) => {
      const edge = evt.target;
      
      // 直接使用CSS类切换而不是动态修改样式
      edge.addClass('hover');
      
      // 添加光效动画
      if (!edge.data('isChapterToChapter')) {
        edge.addClass('edge-glow');
        setTimeout(() => edge.removeClass('edge-glow'), 1500);
      }
    });

    this.cy.on('mouseout', 'edge', (evt) => {
      const edge = evt.target;
      edge.removeClass('hover');
    });
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
    
    // 然后根据状态设置正确的颜色
    if (type === 'chapter') {
      // 检查是否为当前学习章节
      if (this.graphState.currentLearningChapter === id) {
        // 当前学习章节使用橙色
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
  
  // 在graph_renderer.js中添加更多工具栏功能
addToolbarFunctionality() {
  // 缩放功能
  document.getElementById('zoomIn').addEventListener('click', () => {
    this.cy.zoom(this.cy.zoom() * 1.2);
  });
  
  document.getElementById('zoomOut').addEventListener('click', () => {
    this.cy.zoom(this.cy.zoom() / 1.2);
  });
  
  // 居中功能
  document.getElementById('centerGraph').addEventListener('click', () => {
    this.centerAndZoomGraph();
  });
  
  // 添加键盘快捷键
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
      if (e.key === '+' || e.key === '=') {
        this.cy.zoom(this.cy.zoom() * 1.1);
        e.preventDefault();
      } else if (e.key === '-') {
        this.cy.zoom(this.cy.zoom() / 1.1);
        e.preventDefault();
      } else if (e.key === '0') {
        this.centerAndZoomGraph();
        e.preventDefault();
      }
    }
  });
  
  // 添加平移功能
  let panStart = { x: 0, y: 0 };
  let isPanning = false;
  
  this.cy.on('mousedown', (e) => {
    if (e.originalEvent.button === 1 || (e.originalEvent.button === 0 && e.originalEvent.shiftKey)) {
      isPanning = true;
      panStart = { x: e.originalEvent.clientX, y: e.originalEvent.clientY };
      this.cy.container().style.cursor = 'grabbing';
      e.originalEvent.preventDefault();
    }
  });
  
  document.addEventListener('mousemove', (e) => {
    if (isPanning) {
      const dx = e.clientX - panStart.x;
      const dy = e.clientY - panStart.y;
      const currentPan = this.cy.pan();
      this.cy.pan({
        x: currentPan.x - dx / this.cy.zoom(),
        y: currentPan.y - dy / this.cy.zoom()
      });
      panStart = { x: e.clientX, y: e.clientY };
    }
  });
  
  document.addEventListener('mouseup', () => {
    if (isPanning) {
      isPanning = false;
      this.cy.container().style.cursor = 'default';
    }
  });
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

    // 上排章节 → 知识点在下方；下排章节 → 知识点在上方
    const baseY = isTop 
      ? chapterPos.y + this.layoutParams.KNOWLEDGE_ROW_DELTA_Y
      : chapterPos.y - this.layoutParams.KNOWLEDGE_ROW_DELTA_Y;

    const n = kids.length;
    const maxWidth = this.cy.container().clientWidth * 0.7;
    const gap = Math.min(this.layoutParams.KNOWLEDGE_GAP_X, maxWidth / Math.max(n, 4));
    const half = (n - 1) / 2;
    const slopeStep = this.layoutParams.KNOWLEDGE_HEIGHT_STEP || 25;

    kids.forEach((id, i) => {
      const x = chapterPos.x + (i - half) * gap;
      // 给知识点加一个倾斜偏移
      const y = baseY + (i - half) * slopeStep * (isTop ? 1 : -1);

      this.graphState.fixedPositions[id] = { x, y };
    });
}
// ========== 新增：绑定布局事件 ==========
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
  // 添加自动布局调整功能
  adjustLayoutToAvoidOverlap() {
    const visibleNodes = this.cy.nodes().filter(node => node.visible());
    
    // 简单的重叠检测和调整
    visibleNodes.forEach((node, i) => {
      const pos1 = node.position();
      const width1 = parseFloat(node.style('width')) || 0;
      const height1 = parseFloat(node.style('height')) || 0;
      
      for (let j = i + 1; j < visibleNodes.length; j++) {
        const otherNode = visibleNodes[j];
        const pos2 = otherNode.position();
        const width2 = parseFloat(otherNode.style('width')) || 0;
        const height2 = parseFloat(otherNode.style('height')) || 0;
        
        // 检测重叠
        const dx = Math.abs(pos1.x - pos2.x);
        const dy = Math.abs(pos1.y - pos2.y);
        const minDistance = (width1 + width2) / 2 + 20;
        
        if (dx < minDistance && dy < minDistance) {
          // 轻微调整位置避免重叠
          const adjustX = (minDistance - dx) * (pos1.x > pos2.x ? 1 : -1) * 0.5;
          const adjustY = (minDistance - dy) * (pos1.y > pos2.y ? 1 : -1) * 0.5;
          
          node.position({
            x: pos1.x + adjustX,
            y: pos1.y + adjustY
          });
          
          otherNode.position({
            x: pos2.x - adjustX,
            y: pos2.y - adjustY
          });
        }
      }
    });
  }
  // ========== 新增：防抖函数避免频繁调用 ==========
  debounceCenterAndZoom() {
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      /* this.adjustLayoutToAvoidOverlap(); */// 添加自动布局调整功能
      this.centerAndZoomGraph();
    }, 100);
  }

  // 展开章节
  expandChapter(chapterId) {
     this.ensurePositionsForChapterKnowledge(chapterId);
    const kids = this.graphState.collectKnowledgeDescendantsForDisplay(chapterId);
    
    // 使用动画展开
    kids.forEach(id => {
      const node = this.cy.getElementById(id);
      if (node && node.length) {
        const pos = this.graphState.fixedPositions[id];
        if (pos) {
          node.position(pos);
          node.style({
            'opacity': 0
          });
          node.show();
          
          // 淡入动画
          node.animate({
            style: {
              'opacity': 1
            }
          }, {
            duration: 300,
            complete: () => {
              this.updateEdgesVisibility();
            }
          });
        }
      }
    });

    this.updateEdgesVisibility();
    this.graphState.expandedSet.add(chapterId);
    this.updateNodeColors();
    
    // 延迟调整布局，确保动画完成
    setTimeout(() => this.debounceCenterAndZoom(), 350);
  }

  // 收起章节
  collapseChapter(chapterId) {
    const kids = this.graphState.collectKnowledgeDescendantsForDisplay(chapterId);
    kids.forEach(id => {
      const node = this.cy.getElementById(id);
      if (node && node.length) node.hide();
    });
    
    this.updateEdgesVisibility();
    this.graphState.expandedSet.delete(chapterId);
    this.updateNodeColors();
    this.debounceCenterAndZoom(); // 新增：收起后调整布局
  }

  // 更新边可见性
  updateEdgesVisibility() {
    this.cy.edges().forEach(e => {
      const s = e.data('source'), t = e.data('target');
      const sn = this.cy.getElementById(s), tn = this.cy.getElementById(t);
      if (sn && tn && sn.length && tn.length && sn.visible() && tn.visible()) {
        e.style({
          'opacity': 0
        });
        e.show();
        
        // 淡入动画
        e.animate({
          style: {
            'opacity': e.classes().includes('chapter-to-knowledge') ? 0.8 : 
                       e.classes().includes('chapter-to-chapter') ? 0.9 : 1
          }
        }, {
          duration: 300
        });
      } else {
        e.hide();
      }
    });
  }

  // 更新节点颜色
  updateNodeColors() {
    this.cy.nodes().forEach(node => {
      this.restoreNodeStyle(node);
    });
  }

  // 设置章节固定位置 - 优化布局
  setFixedChapterPositions() {
    const chapterNodes = this.cy.nodes('[type="chapter"]');
    const containerWidth = this.cy.container().clientWidth;

      // 增加间距系数，1.2表示比原来宽20%
    const spacingFactor = 1.2;
    const baseSpacing = containerWidth / (chapterNodes.length + 1);
    const actualSpacing = baseSpacing * spacingFactor;

    chapterNodes.forEach((node, idx) => {
      // 使用调整后的间距
      const x = (idx + 1) * actualSpacing;
      const isTop = idx % 2 === 0;  // 偶数序号放上排，奇数序号放下排
      const y = isTop 
        ? this.layoutParams.TOP_ROW_Y 
        : this.layoutParams.TOP_ROW_Y + this.layoutParams.ROW_DELTA_Y;

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
    this.updateEdgesVisibility();
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
      
      minX = Math.min(minX, pos.x - width/2);
      maxX = Math.max(maxX, pos.x + width/2);
      minY = Math.min(minY, pos.y - height/2);
      maxY = Math.max(maxY, pos.y + height/2);
    });
    
    // 减少边距，创建更紧凑的布局
    const margin = 20; // 减少边距
    minX -= margin+20;
    maxX += margin;
    minY -= margin;
    maxY += margin;
    
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    const width = maxX - minX;
    const height = maxY - minY;
    
    const containerWidth = this.cy.container().clientWidth;
    const containerHeight = this.cy.container().clientHeight;
    
    const scaleX = containerWidth / width;
    const scaleY = containerHeight / height;
    const scale = Math.min(scaleX, scaleY, 1.5) * 0.9; // 稍微增加缩放比例
    
    const panX = -centerX * scale + containerWidth / 2;
    const panY = -centerY * scale + containerHeight / 2;
    
    this.cy.animate({
      zoom: scale,
      pan: { x: panX, y: panY },
      duration: 300
    });
  }
}