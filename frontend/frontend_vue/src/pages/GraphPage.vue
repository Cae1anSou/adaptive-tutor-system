<script setup lang="ts">
import { onMounted, ref, reactive } from 'vue'
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
  isUnlocked: false
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

// 检查知识点是否已解锁
const isKnowledgeUnlocked = (nodeId: string, graphData: any, learnedNodes: string[]): boolean => {
  // 解析知识点ID，获取章节和序号
  const parts = nodeId.split('_');
  if (parts.length < 2) return true; // 不符合知识点ID格式，默认解锁
  
  const chapter = parseInt(parts[0]);
  const section = parseInt(parts[1]);

  // 如果是第一章第一个知识点，直接可以学习
  if (chapter === 1 && section === 1) {
    return true;
  }

  // 检查章节是否解锁（章节测试解锁下一章节）
  // 检查前一章节是否已完成（通过章节测试）
  if (chapter > 1) {
    const previousChapterTestId = `${chapter - 1}_end`; // 章节测试ID格式：{章节号}_end
    if (!learnedNodes.includes(previousChapterTestId)) {
      return false;
    }
  }

  // 检查知识点前置条件（知识点间需要顺序解锁）
  if (section > 1) {
    // 检查同章节的前一个知识点
    const previousKnowledgeId = `${chapter}_${section - 1}`;
    if (!learnedNodes.includes(previousKnowledgeId)) {
      return false;
    }
  } else if (chapter > 1) {
    // 第一个知识点需要前一章节测试完成
    const previousChapterTestId = `${chapter - 1}_end`;
    if (!learnedNodes.includes(previousChapterTestId)) {
      return false;
    }
  }

  return true;
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
      
      // 获取已学习的节点
      const learnedNodes = progressData?.completed_topics || []

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
            router.push({ name: 'learning', params: { topicId: nodeId } })
          } else {
            // 单击事件
            clickState.lastId = nodeId
            clickState.ts = now
            clickState.timer = window.setTimeout(() => {
              // 处理单击事件
              const nodeData = graphData.nodes.find((n: any) => n.data.id === nodeId)
              if (nodeData) {
                if (nodeData.data.type === 'chapter') {
                  // // 章节节点处理：展开/折叠
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

// 显示知识点弹窗
function showKnowledgeModal(knowledgeId: string, nodeLabel: string, learnedNodes: string[], graphData: any) {
  // 检查知识点是否已学习
  const isLearned = learnedNodes.includes(knowledgeId)
  
  // 检查知识点是否已解锁
  const isUnlocked = isKnowledgeUnlocked(knowledgeId, graphData, learnedNodes)
  
  // 创建弹窗元素
  const modal = document.createElement('div')
  modal.id = 'knowledgeModal'
  modal.style.cssText = `
    display: block;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.4);
  `
  
  // 创建弹窗内容
  const modalContent = document.createElement('div')
  modalContent.style.cssText = `
    background-color: #fefefe;
    margin: 15% auto;
    padding: 20px;
    border: 1px solid #888;
    width: 80%;
    max-width: 500px;
    border-radius: 5px;
  `
  
  // 标题
  const title = document.createElement('h3')
  title.id = 'modalTitle'
  title.textContent = nodeLabel || knowledgeId
  title.style.marginTop = '0'
  
  // 状态文本
  const status = document.createElement('p')
  status.id = 'modalStatus'
  
  // 按钮容器
  const buttonContainer = document.createElement('div')
  buttonContainer.style.cssText = `
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
  `
  
  // 学习按钮
  const learnBtn = document.createElement('button')
  learnBtn.id = 'learnBtn'
  learnBtn.style.cssText = `
    padding: 8px 16px;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  `
  
  // 测试按钮
  const testBtn = document.createElement('button')
  testBtn.id = 'testBtn'
  testBtn.style.cssText = `
    padding: 8px 16px;
    background-color: #848484;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  `
  
  // 关闭按钮
  const closeBtn = document.createElement('span')
  closeBtn.innerHTML = '&times;'
  closeBtn.style.cssText = `
    float: right;
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
    line-height: 1;
  `
  
  closeBtn.onclick = () => {
    document.body.removeChild(modal)
  }
  
  // 根据学习状态设置按钮文本和行为
  if (isLearned) {
    status.textContent = '您已学过该知识点，是否再次复习或重新测试？'
    learnBtn.textContent = '复习'
    testBtn.textContent = '测试'
    
    learnBtn.onclick = () => {
      router.push({ name: 'learning', params: { topicId: knowledgeId } })
      document.body.removeChild(modal)
    }
    
    testBtn.onclick = () => {
      // 跳转到测试页面
      router.push({ name: 'test', params: { topicId: knowledgeId } })
      console.log('跳转到测试页面:', knowledgeId)
      document.body.removeChild(modal)
    }
  } else if (isUnlocked) {
    status.textContent = '您可以开始学习该知识点或直接进行测试'
    learnBtn.textContent = '学习'
    testBtn.textContent = '测试'
    
    learnBtn.onclick = () => {
      router.push({ name: 'learning', params: { topicId: knowledgeId } })
      document.body.removeChild(modal)
    }
    
    testBtn.onclick = () => {
      // 跳转到测试页面
      console.log('跳转到测试页面:', knowledgeId)
      router.push({ name: 'test', params: { topicId: knowledgeId } })
      document.body.removeChild(modal)
    }
  } else {
    status.textContent = '该知识点尚未解锁，您是否要直接开始测试？'
    learnBtn.textContent = '学习'
    learnBtn.disabled = true
    learnBtn.style.opacity = '0.5'
    testBtn.textContent = '测试'
    
    learnBtn.onclick = () => {}
    
    testBtn.onclick = () => {
      // 跳转到测试页面
      console.log('跳转到测试页面:', knowledgeId)
      document.body.removeChild(modal)
      
    }
  }
  
  // 组装弹窗
  modalContent.appendChild(closeBtn)
  modalContent.appendChild(title)
  modalContent.appendChild(status)
  buttonContainer.appendChild(learnBtn)
  buttonContainer.appendChild(testBtn)
  modalContent.appendChild(buttonContainer)
  modal.appendChild(modalContent)
  
  // 添加到页面
  document.body.appendChild(modal)
  
  // 点击背景关闭弹窗
  modal.onclick = (event) => {
    if (event.target === modal) {
      document.body.removeChild(modal)
    }
  }
}

// 显示章节弹窗
function showChapterModal(chapterId: string, nodeLabel: string, learnedNodes: string[], graphData: any) {
  // 创建弹窗元素
  const modal = document.createElement('div')
  modal.id = 'chapterModal'
  modal.style.cssText = `
    display: block;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.4);
  `
  
  // 创建弹窗内容
  const modalContent = document.createElement('div')
  modalContent.style.cssText = `
    background-color: #fefefe;
    margin: 15% auto;
    padding: 20px;
    border: 1px solid #888;
    width: 80%;
    max-width: 500px;
    border-radius: 5px;
  `
  
  // 标题
  const title = document.createElement('h3')
  title.id = 'modalTitle'
  title.textContent = nodeLabel || chapterId
  title.style.marginTop = '0'
  
  // 状态文本
  const status = document.createElement('p')
  status.id = 'modalStatus'
  
  // 按钮容器
  const buttonContainer = document.createElement('div')
  buttonContainer.style.cssText = `
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 20px;
  `
  
  // 学习按钮
  const learnBtn = document.createElement('button')
  learnBtn.id = 'learnBtn'
  learnBtn.style.cssText = `
    padding: 8px 16px;
    background-color: #4a90e2;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  `
  
  // 测试按钮
  const testBtn = document.createElement('button')
  testBtn.id = 'testBtn'
  testBtn.style.cssText = `
    padding: 8px 16px;
    background-color: #848484;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  `
  
  // 关闭按钮
  const closeBtn = document.createElement('span')
  closeBtn.innerHTML = '&times;'
  closeBtn.style.cssText = `
    float: right;
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
    line-height: 1;
  `
  
  closeBtn.onclick = () => {
    document.body.removeChild(modal)
  }
  
  // 根据章节状态设置按钮文本和行为
  // 检查章节是否已完成（通过章节测试）
  const chapterTestId = `${chapterId.split('_')[0]}_end`
  const isChapterCompleted = learnedNodes.includes(chapterTestId)
  
  if (isChapterCompleted) {
    // 章节已完成
    status.textContent = '您已学过本章节，是否再次进行测试？'
    learnBtn.textContent = '是'
    testBtn.textContent = '否'
    
    learnBtn.onclick = () => {
      router.push({ name: 'test', params: { topicId: chapterTestId } })
      document.body.removeChild(modal)
    }
    
    testBtn.onclick = () => {
      document.body.removeChild(modal)
    }
  } else {
    // 章节未完成
    status.textContent = '您还未学完当前章节内容，是否直接开始测试？'
    learnBtn.textContent = '是'
    testBtn.textContent = '否'
    
    learnBtn.onclick = () => {
      router.push({ name: 'test', params: { topicId: chapterTestId } })
      document.body.removeChild(modal)
    }
    
    testBtn.onclick = () => {
      document.body.removeChild(modal)
    }
  }
  
  // 组装弹窗
  modalContent.appendChild(closeBtn)
  modalContent.appendChild(title)
  modalContent.appendChild(status)
  buttonContainer.appendChild(learnBtn)
  buttonContainer.appendChild(testBtn)
  modalContent.appendChild(buttonContainer)
  modal.appendChild(modalContent)
  
  // 添加到页面
  document.body.appendChild(modal)
  
  // 点击背景关闭弹窗
  modal.onclick = (event) => {
    if (event.target === modal) {
      document.body.removeChild(modal)
    }
  }
}
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
</style>