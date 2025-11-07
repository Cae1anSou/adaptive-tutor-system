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
const configContainer = ref<HTMLElement | null>(null)
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
  if (!networkContainer.value || !configContainer.value) return
  
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
        filter: function (option: string, path: string[]) {
          if (path.indexOf("physics") !== -1) {
            return true;
          }
          if (path.indexOf("smooth") !== -1 || option === "smooth") {
            return true;
          }
          return false;
        },
        container: configContainer.value,
        showButton: false
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
    <h2>Playing with Physics</h2>
    <div style="width: 700px; font-size: 14px; text-align: justify">
      Every dataset is different. Nodes can have different sizes based on
      content, interconnectivity can be high or low etc. Because of this, the
      network configurator can be used to explore which settings may be good for
      him or her. This is ment to be used during the development phase when you
      are implementing vis.js. Once you have found settings you are happy with,
      you can supply them to network using the documented physics options.
    </div>
    
    <div class="info-box">
      <strong>注意:</strong> 如果网络没有立即显示，请尝试调整右侧物理参数或稍微移动节点以触发布局计算。
    </div>
    
    <div class="clearfix">
      <div ref="networkContainer" id="mynetwork"></div>
      <div ref="configContainer" id="config"></div>
    </div>

    <p id="selection">{{ selectionText }}</p>
  </div>
</template>

<style scoped>
body {
  font: 10pt sans;
  margin: 20px;
}

#mynetwork {
  float: left;
  width: 600px;
  height: 600px;
  margin: 5px;
  border: 1px solid lightgray;
  background-color: #f7f7f7;
}

#config {
  float: left;
  width: 400px;
  height: 600px;
  padding: 10px;
  overflow-y: auto;
}

.clearfix::after {
  content: "";
  clear: both;
  display: table;
}

.info-box {
  background-color: #f0f8ff;
  border-left: 4px solid #4a90e2;
  padding: 10px;
  margin-bottom: 15px;
}
</style>
