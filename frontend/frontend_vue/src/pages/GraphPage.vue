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
  }
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
      //console.log(dialogState.requiredChapterId)
      router.push({ name: 'test', params: { topicId: `${dialogState.requiredChapterId.split('_')[1]}_end`} });
    }else if (dialogState.reason === 'previous_knowledge_required') {
      console.log(dialogState.requiredKnowledgeId)
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

      // 转换节点数据并根据学习状态更新颜色
      const nodes = updateNodeColors(
        graphData.nodes.map(node => ({
          id: node.data.id,
          label: node.data.label,
          color: {
            background: '#4a90e2',
            border: '#2270b0'
          },
          shape: 'dot',
          font: {
            size: 80,
            color: '#000000'
          },
          size: 100
        })),
        learnedNodes,
        graphData
      )

      // 转换边数据
      const edges = graphData.edges.map(edge => ({
        from: edge.data.source,
        to: edge.data.target,
        color: { 
          color: '#848484' 
        }
      }))

      const data = {
        nodes: nodes,
        edges: edges
      }

      const options = {
        physics: {
          enabled: true,
          stabilization: {
            enabled: true,
            iterations: 1000
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
          size: 40,
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
          width: 5,
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
      const network = new vis.Network(networkContainer.value, data, options)
      
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
                  // if (expandedChapters.value.has(nodeId)) {
                  //   // 收起章节
                  //   expandedChapters.value.delete(nodeId)
                  // } else {
                  //   // 展开章节
                  //   expandedChapters.value.add(nodeId)
                  // }
                  showChapterModal(nodeId, nodeData.data.label, learnedNodes, graphData)
                } else if (nodeData.data.type === 'knowledge') {
                  // 知识点节点处理
                  showKnowledgeModal(nodeId, nodeData.data.label, learnedNodes, graphData)
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
#mynetwork {
  width: 100%;
  height: 70vh;
  border: 1px solid lightgray;
  background-color: #f7f7f7;
  position: relative;
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
  bottom: 10px;
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
