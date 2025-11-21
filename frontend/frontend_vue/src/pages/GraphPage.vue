<script setup lang="ts">
import { onMounted, ref, reactive, computed } from 'vue'
import { getKnowledgeGraphKnowledgeGraphGet } from '@/api/knowledgeGraph'
import { getUserProgressProgressParticipantsParticipantIdProgressGet } from '@/api/progress'
import { useRouter } from 'vue-router'
import { Modal, Button, message } from 'ant-design-vue'

const networkContainer = ref<HTMLElement | null>(null)
const selectionText = ref('')
const router = useRouter()

// 弹窗相关状态
const dialogState = reactive({
  visible: false,
  title: '',
  status: '',
  knowledgeId: '',
  isLearned: false,
  isUnlocked: false,
  type: 'knowledge', // 'knowledge' 或 'chapter'
  action: 'learn', // 'learn' 或 'test'
  requiredKnowledgeId: '',
  requiredKnowledgeName: '',
  requiredChapterId: '',
  requiredChapterName: '',
  reason:''
})

// 存储展开的章节集合
const expandedChapters = ref<Set<string>>(new Set())

// 图数据存储
const graphDataRef = ref<any>(null)
const learnedNodesRef = ref<string[]>([])

// 动画状态管理
const animationInProgress = ref<{[key: string]: boolean}>({})
const chapterState = ref<{[key: string]: boolean}>({})

// vis-network 实例
let network: any = null
let nodes: any = null
let edges: any = null

// 从localStorage获取用户ID
const getParticipantId = (): string | null => {
  return localStorage.getItem('participant_id')
}

// 检查节点是否已学习
const isNodeLearned = (nodeId: string, learnedNodes: string[]): boolean => {
  return learnedNodes.includes(nodeId)
}

// 检查知识点是否可以跳跃学习（新规则：章节测试解锁下一章节，知识点间需要内部解锁）
const canJumpToKnowledge = (knowledgeId: string, graphData: any, learnedNodes: string[]) => {
  // 解析知识点ID，获取章节和序号
  const parts = knowledgeId.split('_');
  if (parts.length < 2) {
    return { canJump: false, reason: 'invalid_format' };
  }

  const chapter = parseInt(parts[0]);
  const section = parseInt(parts[1]);

  // 如果是第一章第一个知识点，直接可以学习
  if (chapter === 1 && section === 1) {
    return { canJump: true, reason: 'first_knowledge' };
  }

  // 检查章节是否解锁（章节测试解锁下一章节）
  if (chapter > 1) {
    const previousChapterTestId = `${chapter - 1}_end`; // 章节测试ID格式：{章节号}_end
    if (!learnedNodes.includes(previousChapterTestId)) {
      // 查找章节名称
      const chapterNode = graphData.nodes.find((n: any) => n.data.id === `chapter${chapter - 1}`);
      const chapterName = chapterNode ? chapterNode.data.label : `第${chapter - 1}章`;

      return {
        canJump: false,
        reason: 'chapter_locked',
        requiredChapter: `chapter_${chapter - 1}`,
        requiredChapterName: chapterName
      };
    }
  }

  // 检查知识点前置条件（知识点间需要内部解锁）
  if (section > 1) {
    // 检查同章节的前一个知识点
    const previousKnowledgeId = `${chapter}_${section - 1}`;
    if (!learnedNodes.includes(previousKnowledgeId)) {
      // 查找知识点名称
      const knowledgeNode = graphData.nodes.find((n: any) => n.data.id === previousKnowledgeId);
      const knowledgeName = knowledgeNode ? knowledgeNode.data.label : previousKnowledgeId;

      return {
        canJump: false,
        reason: 'previous_knowledge_required',
        requiredKnowledgeId: previousKnowledgeId,
        requiredKnowledgeName: knowledgeName
      };
    }
  } else if (chapter > 1) {
    // 检查前一章节的章节测试
    const previousChapterTestId = `${chapter - 1}_end`; // 章节测试ID格式：{章节号}_end
    if (!learnedNodes.includes(previousChapterTestId)) {
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

// 检查知识点是否已解锁
const isKnowledgeUnlocked = (nodeId: string, graphData: any, learnedNodes: string[]): boolean => {
  // 使用更完整的检查逻辑
  const jumpResult = canJumpToKnowledge(nodeId, graphData, learnedNodes);
  return jumpResult.canJump;
}

// 更新节点颜色以反映学习状态
const updateNodeColors = (nodes: any[], learnedNodes: string[], graphData: any) => {
  return nodes.map(node => {
    const isLearned = isNodeLearned(node.id, learnedNodes)
    const isUnlocked = isKnowledgeUnlocked(node.id, graphData, learnedNodes)

    let backgroundColor, borderColor;

    if (isLearned) {
      // 已学完的节点使用绿色
      backgroundColor = '#4CAF50';
      borderColor = '#388E3C';
    } else if (isUnlocked) {
      // 未学但可解锁的节点使用蓝色
      backgroundColor = '#4a90e2';
      borderColor = '#2270b0';
    } else {
      // 未学且不可解锁的节点使用灰色
      backgroundColor = '#cccccc';
      borderColor = '#888888';
    }

    return {
      ...node,
      color: {
        background: backgroundColor,
        border: borderColor
      }
    }
  })
}

// 获取学习按钮文本
const getLearnButtonText = () => {
  if (dialogState.type === 'knowledge') {
    if (dialogState.isLearned) {
      return '复习';
    } else if (dialogState.isUnlocked) {
      return '学习';
    } else {
      return '是'; // 前置条件未满足时
    }
  } else {
    // 章节类型
    if (dialogState.isLearned) {
      return '是';
    } else {
      return dialogState.status.includes('前置') ? '是' : '测试';
    }
  };
};

// 获取测试按钮文本
const getTestButtonText = () => {
  if (dialogState.isUnlocked&&dialogState.type === 'knowledge') {
    return '测试';
  }
  return "是";
  if (dialogState.type === 'knowledge') {
    return '测试';
  } else {
    return '否';
  }
};

// 判断是否应该显示测试按钮
const shouldShowTestButton = () => {
  return true;
  if (dialogState.type === 'knowledge') {
    // 知识点总是显示测试按钮
    return true;
  } else {
    // 章节类型
    if (dialogState.isLearned) {
      // 已完成的章节不显示测试按钮（否按钮）
      return false;
    } else {
      // 未完成的章节根据状态决定是否显示测试按钮
      // 如果是"还未学完当前章节内容"的情况，不显示"否"按钮
      // 如果是前置章节未完成的情况，也不显示"否"按钮
      return !dialogState.status.includes('前置章节') && !dialogState.status.includes('还未学完当前章节内容');
    }
  }
};

const shouldShowLearnButton = () => {
  return !isTestButtonPrimary();
  return true;
  if (dialogState.type === 'knowledge') {
    // 知识点总是显示学习按钮
    return true;
  } else {
    // 章节类型
    if (dialogState.isLearned) {
      // 已完成的章节不显示学习按钮（是按钮）
      return false;
    } else {
      // 未完成的章节根据状态决定是否显示学习按钮
      // 如果是"还未学完当前章节内容"的情况，
    }
  }
}

const isTestButtonPrimary = () => {
  if (!dialogState.isUnlocked||(dialogState.isLearned&&dialogState.type==='chapter')||(!dialogState.isLearned&&dialogState.isUnlocked&&dialogState.type==='chapter')) {
    return true;
  }
  return false;
}
// 显示知识点弹窗
const showKnowledgeModal = (knowledgeId: string, nodeLabel: string, learnedNodes: string[], graphData: any) => {
  dialogState.title = nodeLabel || knowledgeId;
  dialogState.knowledgeId = knowledgeId;
  dialogState.type = 'knowledge';

  // 检查知识点是否已学习
  dialogState.isLearned = learnedNodes.includes(knowledgeId);

  // 检查知识点是否已解锁
  const jumpResult = canJumpToKnowledge(knowledgeId, graphData, learnedNodes);
  dialogState.isUnlocked = jumpResult.canJump;

  // 根据学习状态设置按钮文本和行为
  if (dialogState.isLearned) {
    dialogState.status = '您已学过该知识点，是否再次复习或重新测试？';
  } else if (dialogState.isUnlocked) {
    dialogState.status = '您可以开始学习该知识点或直接进行测试';
  } else {
    dialogState.reason = jumpResult.reason;
    // 根据不能解锁的原因显示不同的提示
    if (jumpResult.reason === 'chapter_locked') {
      dialogState.status = `您还未完成前置章节"${jumpResult.requiredChapterName}"的测试，需要先完成该章节的测试才能学习本知识点。是否现在开始测试前置章节？`;
      dialogState.requiredChapterId = jumpResult.requiredChapter;
      dialogState.requiredChapterName = jumpResult.requiredChapterName;
    } else if (jumpResult.reason === 'previous_knowledge_required' || jumpResult.reason === 'previous_chapter_test_required') {
      dialogState.status = `您还未学习前置知识点"${jumpResult.requiredKnowledgeName}"，需要先完成该知识点的测试才能学习本知识点。是否现在开始测试前置知识点？`;
      dialogState.requiredKnowledgeId = jumpResult.requiredKnowledgeId;
      dialogState.requiredKnowledgeName = jumpResult.requiredKnowledgeName;
    } else {
      dialogState.status = '该知识点尚未解锁，您是否要直接开始测试？';
    }
  }

  dialogState.visible = true;
};

// 显示章节弹窗
const showChapterModal = (chapterId: string, nodeLabel: string, learnedNodes: string[], graphData: any) => {
  dialogState.title = nodeLabel || chapterId;
  dialogState.knowledgeId = chapterId;
  dialogState.type = 'chapter';

  // 检查章节是否已完成（通过章节测试）
  const chapterTestId = `${chapterId.split('_')[0]}_end`;
  dialogState.isLearned = learnedNodes.includes(chapterTestId);

  // 检查章节是否可以学习（前置章节是否已完成）
  const chapterNumber = parseInt(chapterId.replace('chapter', ''));
  let previousChapterCompleted = true;
  let previousChapterNumber = 0;

  if (chapterNumber > 1) {
    const previousChapterTestId = `${chapterNumber - 1}_end`;
    previousChapterCompleted = learnedNodes.includes(previousChapterTestId);
    previousChapterNumber = chapterNumber - 1;
  }

  if (dialogState.isLearned) {
    // 章节已完成
    dialogState.status = '您已学过本章节，是否再次进行测试？';
    dialogState.isUnlocked = true;
  } else if (previousChapterCompleted) {
    // 章节未完成但可以学习
    dialogState.status = '您还未学完当前章节内容，是否直接开始测试？';
    dialogState.isUnlocked = true;
  } else {
    // 章节未完成且前置章节未完成
    dialogState.status = `您还未完成前置章节（第${previousChapterNumber}章）的学习，无法学习当前章节。是否前往学习前置章节？`;
    dialogState.requiredChapter = `chapter_${previousChapterNumber}`;
    dialogState.requiredChapterName = `第${previousChapterNumber}章`;
  }

  dialogState.visible = true;
};

// 弹窗按钮处理函数
const handleLearn = () => {
  if (dialogState.type === 'knowledge') {
    if (dialogState.isLearned) {
      // 复习知识点
      router.push({ name: 'learning', params: { topicId: dialogState.knowledgeId } });
    } else if (dialogState.isUnlocked) {
      // 学习知识点
      router.push({ name: 'learning', params: { topicId: dialogState.knowledgeId } });
    } else {
      // 跳转到前置章节或知识点测试
      const jumpResult = canJumpToKnowledge(dialogState.knowledgeId, graphDataRef.value, learnedNodesRef.value);

      if (jumpResult.reason === 'chapter_locked') {
        // 设置跳转目标，测试完成后自动跳转回来
        localStorage.setItem('jumpLearningTarget', JSON.stringify({
          knowledgeId: dialogState.knowledgeId,
          timestamp: Date.now()
        }));

        const chapterNum = parseInt(jumpResult.requiredChapter.replace('chapter', ''));
        const chapterTestId = `${chapterNum}_end`;
        router.push({ name: 'test', params: { topicId: chapterTestId } });
      } else if (jumpResult.reason === 'previous_knowledge_required' || jumpResult.reason === 'previous_chapter_test_required') {
        // 设置跳转目标，测试完成后自动跳转回来
        localStorage.setItem('jumpLearningTarget', JSON.stringify({
          knowledgeId: dialogState.knowledgeId,
          timestamp: Date.now()
        }));

        router.push({ name: 'test', params: { topicId: jumpResult.requiredKnowledgeId } });
      }
    }
  } else {
    // 章节类型
    const chapterTestId = `${dialogState.knowledgeId.split('_')[0]}_end`;
    console.log();
    if (dialogState.reason === 'chapter_locked') {
      // 设置跳转目标，测试完成后自动跳转回来
      localStorage.setItem('jumpLearningTarget', JSON.stringify({
        knowledgeId: dialogState.knowledgeId,
        timestamp: Date.now()
      }));

      // 测试已完成的章节
      router.push({ name: 'test', params: { topicId: chapterTestId } });
    } else {
      // 检查是否需要跳转到前置章节
      const chapterNumber = parseInt(dialogState.knowledgeId.replace('chapter', ''));
      let previousChapterCompleted = true;
      let previousChapterTestId = '';

      if (chapterNumber > 1) {
        previousChapterTestId = `${chapterNumber - 1}_end`;
        previousChapterCompleted = learnedNodesRef.value.includes(previousChapterTestId);
      }

      if (previousChapterCompleted) {
        // 直接测试当前章节
        router.push({ name: 'test', params: { topicId: chapterTestId } });
      } else {
        // 设置跳转目标，测试完成后自动跳转回来
        localStorage.setItem('jumpLearningTarget', JSON.stringify({
          knowledgeId: dialogState.knowledgeId,
          timestamp: Date.now()
        }));

        // 跳转到前置章节测试
        router.push({ name: 'test', params: { topicId: previousChapterTestId } });
      }
    }
  }

  dialogState.visible = false;
};

const handleTest = () => {
  if (dialogState.type === 'knowledge') {
    if (dialogState.isLearned || dialogState.isUnlocked) {
      // 测试知识点
      router.push({ name: 'test', params: { topicId: dialogState.knowledgeId } });
    } else if(dialogState.reason === 'chapter_locked'){
      // 对于未解锁的知识点，也允许测试
      // 设置跳转目标，测试完成后自动跳转回来
      localStorage.setItem('jumpLearningTarget', JSON.stringify({
        knowledgeId: dialogState.knowledgeId,
        timestamp: Date.now()
      }));

      router.push({ name: 'test', params: { topicId: `${dialogState.requiredChapterId.split('_')[1]}_end`} });
    }else if (dialogState.reason === 'previous_knowledge_required' || dialogState.reason === 'previous_chapter_test_required') {
      // 设置跳转目标，测试完成后自动跳转回来
      localStorage.setItem('jumpLearningTarget', JSON.stringify({
        knowledgeId: dialogState.knowledgeId,
        timestamp: Date.now()
      }));

      router.push({ name: 'test', params: { topicId: dialogState.requiredKnowledgeId } });
    }

  } else {
    // 章节类型
    const chapterTestId = `${dialogState.knowledgeId.split('_')[0]}_end`;
    //console.log(dialogState.requiredChapter);
    if(dialogState.isUnlocked){
      router.push({ name: 'test', params: { topicId: chapterTestId } });
    }
    else{
      // 设置跳转目标，测试完成后自动跳转回来
      localStorage.setItem('jumpLearningTarget', JSON.stringify({
        knowledgeId: dialogState.knowledgeId,
        timestamp: Date.now()
      }));

      const lastchapterTestId = `${dialogState.requiredChapter.split('_')[1]}_end`;
      router.push({ name: 'test', params: { topicId: lastchapterTestId } });
    }
  }

  dialogState.visible = false;
};

const handleCancel = () => {
  dialogState.visible = false;
  resetDialogState(); // 清理状态
};
const resetDialogState = () => {
  dialogState.title = '';
  dialogState.status = '';
  dialogState.knowledgeId = '';
  dialogState.isLearned = false;
  dialogState.isUnlocked = false;
  dialogState.type = 'knowledge';
  dialogState.action = 'learn';
  dialogState.requiredKnowledgeId = '';
  dialogState.requiredKnowledgeName = '';
  dialogState.requiredChapterId = '';
  dialogState.requiredChapterName = '';
  dialogState.reason = '';
};

// 定义常量
const ANIMATION_STEPS = 8;
const BASE_NODE_SIZE = 100;
const MIN_NODE_SIZE = 10;
const BASE_FONT_SIZE = 80;
const MIN_FONT_SIZE = 8;
const BASE_EDGE_WIDTH = 5;
const MIN_EDGE_WIDTH = 0.5;
const ANIMATION_INTERVAL = 40;
const STABILIZE_ITERATIONS = 50;
const STABILIZATION_ITERATIONS = 1000;

// 缩放动画实现 - 适配当前大小配置
function toggleChapterWithScaleAnimation(chapterId: string) {
  // 防止重复点击
  if (animationInProgress.value[chapterId]) return;
  animationInProgress.value[chapterId] = true;
  console.log('node:', nodes.get());
  // 获取该章节下所有的小节节点
  var sectionNodes = nodes.get({
    filter: function (node: any) {
      return !node.id.endsWith('_end') && node.id.startsWith(chapterId.replace('_end', '_'));
    }
  });
  console.log('s:', sectionNodes);
  var sectionEdges = edges.get({
    filter: function (edge: any) {
      var fromNode = nodes.get(edge.from);
      var toNode = nodes.get(edge.to);
      return (fromNode && fromNode.id === chapterId && toNode && toNode.type === 'knowledge' && toNode.id.startsWith(chapterId.replace('_end', '_'))) ||
             (toNode && toNode.id === chapterId && fromNode && fromNode.type === 'knowledge' && fromNode.id.startsWith(chapterId.replace('_end', '_')));
    }
  });

  var isCurrentlyExpanded = chapterState.value[chapterId];
  var newHiddenState = !isCurrentlyExpanded;

  // 更新章节节点的视觉状态
  updateChapterNodeIndicator(chapterId, newHiddenState);

  // 根据状态执行展开或收缩动画
  if (newHiddenState) {
    expandWithScaleAnimation(sectionNodes, sectionEdges, chapterId);
  } else {
    collapseWithScaleAnimation(sectionNodes, sectionEdges, chapterId);
  }
}

// 展开动画 - 适配当前大小
function expandWithScaleAnimation(sectionNodes: any[], sectionEdges: any[], chapterId: string) {
  // 1. 先显示节点和边，但设置为最小状态
  console.log('展开:', chapterId);
  var nodeUpdates = sectionNodes.map(function (section: any) {
    return {
      id: section.id,
      hidden: false,
      size: MIN_NODE_SIZE,  // 最小尺寸 (100的1/10)
      font: { size: MIN_FONT_SIZE },  // 最小字体 (80的1/10)
      color: section.originalColor || {
        background: '#E3F2FD',
        border: '#2196F3'
      }
    };
  });

  var edgeUpdates = sectionEdges.map(function (edge: any) {
    return {
      id: edge.id,
      hidden: false,
      width: MIN_EDGE_WIDTH,  // 最小宽度 (5的1/10)
      color: {
        color: 'rgba(132, 132, 132, 0.3)',
        highlight: 'rgba(132, 132, 132, 0.5)'
      }
    };
  });

  nodes.update(nodeUpdates);
  edges.update(edgeUpdates);

  // 2. 给物理引擎一点时间适应新节点
  setTimeout(function() {
    // 3. 逐步放大节点和边
    var steps = ANIMATION_STEPS;
    var currentStep = 0;

    var animationInterval = setInterval(function() {
      currentStep++;

      var progress = currentStep / steps;
      var easeProgress = easeOutCubic(progress);

      // 计算当前步骤的大小 - 适配当前配置
      var currentSize = MIN_NODE_SIZE + ((BASE_NODE_SIZE - MIN_NODE_SIZE) * easeProgress); // 从10到100
      var currentFontSize = MIN_FONT_SIZE + ((BASE_FONT_SIZE - MIN_FONT_SIZE) * easeProgress); // 从8到80
      var currentEdgeWidth = MIN_EDGE_WIDTH + ((BASE_EDGE_WIDTH - MIN_EDGE_WIDTH) * easeProgress); // 从0.5到5
      var currentEdgeOpacity = 0.3 + (0.7 * easeProgress); // 从0.3到1

      // 更新节点
      var nodeUpdates = sectionNodes.map(function (section: any) {
        return {
          id: section.id,
          size: currentSize,
          font: { size: Math.max(1, currentFontSize) },
          // 使用节点的原始颜色，避免硬编码
          color: section.originalColor || {
            background: interpolateColor('#E3F2FD', '#4a90e2', easeProgress),
            border: '#2196F3'
          }
        };
      });

      // 更新边
      var edgeUpdates = sectionEdges.map(function (edge: any) {
        return {
          id: edge.id,
          width: currentEdgeWidth,
          color: {
            color: `rgba(132, 132, 132, ${currentEdgeOpacity})`,
            highlight: `rgba(132, 132, 132, ${Math.min(1, currentEdgeOpacity + 0.2)})`
          }
        };
      });

      nodes.update(nodeUpdates);
      edges.update(edgeUpdates);

      // 动画完成
      if (currentStep >= steps) {
        clearInterval(animationInterval);

        // 恢复节点原始颜色
        var finalUpdates = sectionNodes.map(function (section: any) {
          return {
            id: section.id,
            color: section.originalColor || {
              background: '#4a90e2',
              border: '#2270b0'
            }
          };
        });
        nodes.update(finalUpdates);

        // 恢复边原始样式
        var finalEdgeUpdates = sectionEdges.map(function (edge: any) {
          return {
            id: edge.id,
            color: {
              color: '#848484',
              highlight: '#ff9800'
            }
          };
        });
        edges.update(finalEdgeUpdates);

        // 更新章节状态
        chapterState.value[chapterId] = true;

        // 重新稳定布局
        network.stopSimulation();
        network.stabilize(STABILIZE_ITERATIONS);

        // 允许再次点击
        setTimeout(function() {
          animationInProgress.value[chapterId] = false;
        }, 200);
      }
    }, ANIMATION_INTERVAL);
  }, 50);
}

// 收缩动画 - 适配当前大小
function collapseWithScaleAnimation(sectionNodes: any[], sectionEdges: any[], chapterId: string) {
   console.log('收缩:', chapterId);
   console.log('sectionNodes:', sectionNodes);
  // 逐步缩小节点和边
  var steps = ANIMATION_STEPS;
  var currentStep = 0;

  var animationInterval = setInterval(function() {
    //console.log('currentStep:', currentStep);
    currentStep++;

    var progress = currentStep / steps;
    var easeProgress = easeInCubic(progress);

    // 计算当前步骤的大小 - 适配当前配置
    var currentSize = BASE_NODE_SIZE - ((BASE_NODE_SIZE - MIN_NODE_SIZE) * easeProgress); // 从100到10
    var currentFontSize = BASE_FONT_SIZE - ((BASE_FONT_SIZE - MIN_FONT_SIZE) * easeProgress); // 从80到8
    var currentEdgeWidth = BASE_EDGE_WIDTH - ((BASE_EDGE_WIDTH - MIN_EDGE_WIDTH) * easeProgress); // 从5到0.5
    var currentEdgeOpacity = 1 - (0.7 * easeProgress); // 从1到0.3

    // 更新节点
    var nodeUpdates = sectionNodes.map(function (section: any) {
      return {
        id: section.id,
        size: Math.max(MIN_NODE_SIZE, currentSize),
        font: { size: Math.max(MIN_FONT_SIZE, currentFontSize) },
        // 使用完整的原始颜色对象
        color: section.originalColor || {
          background: interpolateColor('#4a90e2', '#E3F2FD', easeProgress),
          border: '#2196F3'
        }
      };
    });

    // 更新边
    var edgeUpdates = sectionEdges.map(function (edge: any) {
      return {
        id: edge.id,
        width: Math.max(MIN_EDGE_WIDTH, currentEdgeWidth),
        color: {
          color: `rgba(132, 132, 132, ${currentEdgeOpacity})`,
          highlight: `rgba(132, 132, 132, ${Math.max(0.3, currentEdgeOpacity - 0.2)})`
        }
      };
    });

    nodes.update(nodeUpdates);
    edges.update(edgeUpdates);

    // 动画完成
    if (currentStep >= steps) {
      clearInterval(animationInterval);

      // 隐藏节点和边
      var hideNodeUpdates = sectionNodes.map(function (section: any) {
        return {
          id: section.id,
          hidden: true,
          // 恢复原始大小，以便下次展开时正确动画
          size: BASE_NODE_SIZE,
          font: { size: BASE_FONT_SIZE }
        };
      });

      var hideEdgeUpdates = sectionEdges.map(function (edge: any) {
        return {
          id: edge.id,
          hidden: true,
          width: BASE_EDGE_WIDTH
        };
      });

      nodes.update(hideNodeUpdates);
      edges.update(hideEdgeUpdates);

      // 更新章节状态
      chapterState.value[chapterId] = false;

      // 重新稳定布局
      network.stopSimulation();
      network.stabilize(STABILIZE_ITERATIONS);

      // 允许再次点击
      setTimeout(function() {
        animationInProgress.value[chapterId] = false;
      }, 200);
    }
  }, ANIMATION_INTERVAL);
}

// 缓动函数
function easeOutCubic(t: number) {
  return 1 - Math.pow(1 - t, 3);
}

function easeInCubic(t: number) {
  return t * t * t;
}

// 颜色插值函数
function interpolateColor(color1: string, color2: string, progress: number) {
  // 将十六进制颜色转换为RGB
  const hexToRgb = (hex: string) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : { r: 0, g: 0, b: 0 };
  };

  // 将RGB转换为十六进制颜色
  const rgbToHex = (r: number, g: number, b: number) => {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  };

  const rgb1 = hexToRgb(color1);
  const rgb2 = hexToRgb(color2);

  // 在两种颜色之间进行插值
  const r = Math.round(rgb1.r + (rgb2.r - rgb1.r) * progress);
  const g = Math.round(rgb1.g + (rgb2.g - rgb1.g) * progress);
  const b = Math.round(rgb1.b + (rgb2.b - rgb1.b) * progress);

  return rgbToHex(r, g, b);
}

// 更新章节节点的指示器
function updateChapterNodeIndicator(chapterId: string, isExpanded: boolean) {
  var chapterNode = nodes.get(chapterId);
  if (!chapterNode) return;
  //console.log('更新章节节点的指示器:', chapterId, isExpanded);
  var newLabel = !isExpanded ?
    '[-] ' + chapterNode.label.replace(/^\[[+-]\]\s*/, '') :
    '[+] ' + chapterNode.label.replace(/^\[[+-]\]\s*/, '');

  nodes.update({
    id: chapterId,
    label: newLabel
  });
}

// 在节点初始化时保存原始颜色
function initializeNodesWithOriginalColor(allNodes: any[]) {
  allNodes.forEach(function(node: any) {
    // 保存整个color对象而不是仅仅background颜色
    if (node.color) {
      //console.log('保存原始颜色:', node.id, node.color);
      node.originalColor = {...node.color};
    }
  });
  nodes.update(allNodes);
}

onMounted(() => {
  if (!networkContainer.value) return

  // 动态导入 vis-network
  import('vis-network').then((vis) => {
    // 获取用户ID
    const participantId = getParticipantId()
    if (!participantId) {
      // 如果没有用户ID，重定向到登录页或其他处理
      console.warn('未找到用户ID')
      // 可以重定向到登录页面
      router.push('/login')
      return
    }

    // 并行获取知识图谱数据和用户进度
    Promise.all([
      getKnowledgeGraphKnowledgeGraphGet(),
      getUserProgressProgressParticipantsParticipantIdProgressGet({ participant_id: participantId })
    ]).then(([graphResponse, progressResponse]) => {
      const graphData = graphResponse.data?.data
      const progressData = progressResponse.data?.data

      if (!graphData) return

      // 保存数据引用
      graphDataRef.value = graphData;

      // 获取已学习的节点
      const learnedNodes = progressData?.completed_topics || []
      learnedNodesRef.value = learnedNodes;

      // 转换节点数据并根据学习状态更新颜色// 定义常量
const BASE_NODE_SIZE = 100;
const BASE_FONT_SIZE = 80;
const BASE_EDGE_WIDTH = 5;

      const nodeData = updateNodeColors(
        graphData.nodes.map(node => ({
          id: node.data.id,
          label: node.data.label,
          color: {
            background: '#4a90e2',
            border: '#2270b0'
          },
          shape: 'dot',
          font: {
            size: BASE_FONT_SIZE,
            color: '#000000'
          },
          size: BASE_NODE_SIZE
        })),
        learnedNodes,
        graphData
      )

      // 转换边数据
      const edgeData = graphData.edges.map(edge => ({
        from: edge.data.source,
        to: edge.data.target,
        color: {
          color: '#848484'
        },
        width: BASE_EDGE_WIDTH
      }))

      const data = {
        nodes: nodeData,
        edges: edgeData
      }

      const options = {
        physics: {
          enabled: true,
          stabilization: {
            enabled: true,
            iterations: STABILIZATION_ITERATIONS
          },
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -3000,
            centralGravity: 0.02,
            springLength: 200,  // 减小弹簧长度以增加张力
            springConstant: 0.05, // 增加弹簧常数以增加张力
            damping: 0.5,
            avoidOverlap: 1
          },
          maxVelocity: 50,
          minVelocity: 0.1,
          timestep: 0.5
        },
        nodes: {
          borderWidth: 3,
          size: BASE_NODE_SIZE * 0.4,
          shadow: true,
          shape: 'dot',
          color: {
            background: '#4a90e2',
            border: '#2270b0',
            highlight: {
              background: '#ff9800',
              border: '#e65100'
            }
          }
        },
        edges: {
          width: BASE_EDGE_WIDTH,
          shadow: false,
          smooth: {
            enabled: true,
            type: 'continuous'
          },
          color: {
            color: '#848484',
            highlight: '#ff9800'
          }
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
          dragNodes: true,
          dragView: true,
          zoomView: true
        },
        configure: {
          enabled: false
        }
      }

      // 创建网络
      network = new vis.Network(networkContainer.value, data, options)

      // 获取节点和边的数据集
      nodes = network.body.data.nodes;
      edges = network.body.data.edges;

      // 初始化章节状态，使所有章节默认展开
      graphData.nodes.forEach((node: any) => {
        if (node.data.type === 'chapter') {
          chapterState.value[node.data.id] = true;
          // 更新章节节点的指示器显示为展开状态
          updateChapterNodeIndicator(node.data.id, true);
        }
      });

      // 初始化节点原始颜色
      initializeNodesWithOriginalColor(nodeData);

      // 单击/双击处理状态
      const clickState = { lastId: null as string | null, timer: null as number | null, ts: 0 }
      const DBL_DELAY = 280

      // 添加点击事件监听
      network.on("click", function (params: any) {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]

          const now = Date.now()

          if (clickState.lastId === nodeId && (now - clickState.ts) < DBL_DELAY) {
            // 双击事件
            clearTimeout(clickState.timer!)
            clickState.timer = null
            clickState.lastId = null
            console.log('1双击击章节节点：', nodeId);
            const nodeData = graphData.nodes.find((n: any) => n.data.id === nodeId)
            if (nodeData) {
                if (nodeData.data.type === 'chapter') {
                  // 章节节点处理：展开/折叠
                  console.log('2双击击章节节点：', nodeId);
                  showChapterModal(nodeId, nodeData.data.label, learnedNodes, graphData);
                  //showChapterModal(nodeId, nodeData.data.label, learnedNodes, graphData)
                }
              }
            // 双击节点跳转功能
            //router.push({ name: 'learning', params: { topicId: nodeId } })
          } else {
            // 单击事件
            clickState.lastId = nodeId
            clickState.ts = now
            clickState.timer = window.setTimeout(() => {
              // 处理单击事件
              const nodeData = graphData.nodes.find((n: any) => n.data.id === nodeId)
              if (nodeData) {
                if (nodeData.data.type === 'chapter') {
                  // 章节节点处理：展开/折叠
                  toggleChapterWithScaleAnimation(nodeId);
                  //showChapterModal(nodeId, nodeData.data.label, learnedNodes, graphData)
                } else if (nodeData.data.type === 'knowledge') {
                  // 知识点节点处理
                  showKnowledgeModal(nodeId, nodeData.data.label, learnedNodes, graphData);
                }
              }

              clickState.timer = null
              clickState.lastId = null
            }, DBL_DELAY)
          }
        }
      })

      // 添加选择事件监听
      // network.on("select", function (params: any) {
      //   selectionText.value = 'Selected nodes: ' + params.nodes + ', Edges: ' + params.edges

      //   // 点击节点聚焦功能
      //   if (params.nodes.length > 0) {
      //     const nodeId = params.nodes[0];
      //     // 聚焦到选中的节点
      //     network.focus(nodeId, {
      //       scale: 0.4,  // 缩放级别
      //       animation: {
      //         duration: 1000,
      //         easingFunction: 'easeInOutQuad'
      //       }
      //     });
      //   }
      // })
    }).catch(error => {
      console.error('获取数据失败:', error)
    })
  })
})
</script>

<template>
  <div id="GraphPage">
    <div class="graph-container">
      <div ref="networkContainer" id="mynetwork"></div>
    </div>

    <div class="legend">
      <div class="legend-item">
        <div class="legend-color learned"></div>
        <span>已学完的节点</span>
      </div>
      <div class="legend-item">
        <div class="legend-color unlocked"></div>
        <span>未学但可解锁的节点</span>
      </div>
      <div class="legend-item">
        <div class="legend-color locked"></div>
        <span>未学且不可解锁的节点</span>
      </div>
    </div>

    <!-- 知识点/章节弹窗 -->
    <a-modal
      v-model:open="dialogState.visible"
      :title="dialogState.title"
      @ok="handleLearn"
      @cancel="handleCancel"
      :footer="null"
      centered
    >
      <p>{{ dialogState.status }}</p>
      <div class="modal-buttons">
        <a-button
        key="learn"
        :type="isTestButtonPrimary()?'default' :'primary'"
         @click="handleLearn"
         v-if="shouldShowLearnButton()"
        >{{ getLearnButtonText() }}
        </a-button>
        <a-button
          key="test"
          :type="isTestButtonPrimary() ? 'primary' : 'default'"
          @click="handleTest"
          v-if="shouldShowTestButton()"
        >
          {{ getTestButtonText() }}
        </a-button>
        <a-button key="cancel" @click="handleCancel">取消</a-button>
      </div>
    </a-modal>

    <p id="selection">{{ selectionText }}</p>
  </div>
</template>

<style scoped>
#GraphPage {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
}

.graph-container {
  flex: 1;
  position: relative;
  min-height: 0; /* 重要：允许flex子项收缩 */
}

#mynetwork {
  width: 100%;
  height: 100%;
  border: 1px solid lightgray;
  background-color: #f7f7f7;
  position: absolute;
  top: 0;
  left: 0;
}

.legend {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background-color: #f9f9f9;
  position: absolute;
  bottom: 5%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}

.legend-item {
  display: flex;
  align-items: center;
}

.legend-color {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  margin-right: 5px;
  border: 1px solid #666;
}

.learned {
  background-color: #4CAF50;
}

.unlocked {
  background-color: #4a90e2;
}

.locked {
  background-color: #cccccc;
}

.modal-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
</style>
