<script setup lang="ts">
import { onMounted, ref } from 'vue'

// 定义节点和边的类型
interface Node {
  id: number
  label: string
  color: {
    background: string
    border: string
  }
  shape: string
  font: {
    size: number
    color: string
  }
}

interface Edge {
  from: number
  to: number
  color: { 
    color: string 
  }
}

const networkContainer = ref<HTMLElement | null>(null)
const selectionText = ref('')

// 修复随机数生成函数
function seededRandom() {
  return Math.random();
}

function generateRandomNodesAndEdges(nodeCount: number): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = []
  const edges: Edge[] = []
  const connectionCount: number[] = []

  // 创建节点和边
  for (let i = 0; i < nodeCount; i++) {
    nodes.push({
      id: i,
      label: String(i),
      color: {
        background: getRandomColor(),
        border: '#2B7CE9'
      },
      shape: 'circle',
      font: {
        size: 14,
        color: '#ffffff'
      }
    })

    connectionCount[i] = 0

    // 创建边
    if (i === 1) {
      const from = i
      const to = 0
      edges.push({
        from: from,
        to: to,
        color: { color: '#848484' }
      })
      connectionCount[from]++
      connectionCount[to]++
    } else if (i > 1) {
      const conn = edges.length * 2
      const rand = Math.floor(seededRandom() * conn)
      let cum = 0
      let j = 0
      while (j < connectionCount.length && cum < rand) {
        cum += connectionCount[j]
        j++
      }

      const from = i
      const to = j
      edges.push({
        from: from,
        to: to,
        color: { color: '#848484' }
      })
      connectionCount[from]++
      connectionCount[to]++
    }
  }

  return { nodes: nodes, edges: edges }
}

// 生成随机颜色
function getRandomColor(): string {
  const letters = '0123456789ABCDEF'
  let color = '#'
  for (let i = 0; i < 6; i++) {
    color += letters[Math.floor(Math.random() * 16)]
  }
  return color
}

onMounted(() => {
  if (!networkContainer.value) return
  
  // 动态导入 vis-network
  import('vis-network').then((vis) => {
    // 生成数据
    const data = generateRandomNodesAndEdges(25) // 减少节点数量以便更快渲染

    const options = {
      physics: {
        enabled: true,
        stabilization: {
          enabled: true,
          iterations: 100
        },
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springLength: 100,
          springConstant: 0.08,
          damping: 0.4,
          avoidOverlap: 1
        },
        maxVelocity: 50,
        minVelocity: 0.1,
        timestep: 0.5
      },
      nodes: {
        borderWidth: 2,
        size: 30,
        shadow: true
      },
      edges: {
        width: 2,
        shadow: true,
        smooth: {
          enabled: true,
          type: 'continuous'
        }
      },
      interaction: {
        hover: true,
        tooltipDelay: 200
      },
      configure: {
        enabled: false
      }
    }

    // 创建网络
    const network = new vis.Network(networkContainer.value, data, options)

    // 添加选择事件监听
    network.on("select", function (params: any) {
      selectionText.value = 'Selected nodes: ' + params.nodes + ', Edges: ' + params.edges
    })
  })
})
</script>

<template>
  <div id="GraphPage">
    <div class="graph-container">
      <div ref="networkContainer" id="mynetwork"></div>
    </div>

    <p id="selection">{{ selectionText }}</p>
  </div>
</template>

<style scoped>
#mynetwork {
  width: 100%;
  height: 80vh;
  border: 1px solid lightgray;
  background-color: #f7f7f7;
}
</style>
