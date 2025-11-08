<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getKnowledgeGraphKnowledgeGraphGet } from '@/api/knowledgeGraph'

const networkContainer = ref<HTMLElement | null>(null)
const selectionText = ref('')

onMounted(() => {
  if (!networkContainer.value) return
  
  // 动态导入 vis-network
  import('vis-network').then((vis) => {
    // 从后端获取知识图谱数据
    getKnowledgeGraphKnowledgeGraphGet().then(response => {
      const graphData = response.data?.data
      if (!graphData) return

      // 转换节点数据
      const nodes = graphData.nodes.map(node => ({
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
      }))

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
            type: 'dymanic'
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

      // 添加选择事件监听
      network.on("select", function (params: any) {
        selectionText.value = 'Selected nodes: ' + params.nodes + ', Edges: ' + params.edges
      })
    }).catch(error => {
      console.error('获取知识图谱数据失败:', error)
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
