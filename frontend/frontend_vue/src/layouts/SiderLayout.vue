<script setup lang="ts">
import { ref } from 'vue';
import { RouterView } from 'vue-router';
import SiderAI from "@/components/SiderAI.vue";

// 底部版权信息
const footerText = 'Copyright © 2025 syncPBL by 宋曹卢余蔡吴林';

// 控制 Sider 在移动端的折叠状态
const collapsed = ref(false);
</script>

<template>
  <a-layout class="app-layout">
    <a-layout-header class="app-header">
      <div class="header-logo">
        <span>SyncPBL智能教学平台</span>
      </div>
      <div class="header-menu">
        Header Content
      </div>
    </a-layout-header>

    <a-layout class="main-wrapper">

      <a-layout-content class="app-content">
        <div class="content-container">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </a-layout-content>

      <a-layout-sider
        v-model:collapsed="collapsed"
        :width="400"
        breakpoint="lg"
        collapsed-width="0"
        class="app-sider"
        theme="light"
      >
        <div class="sider-content">
          <SiderAI />
        </div>
      </a-layout-sider>
    </a-layout>

    <a-layout-footer class="app-footer">
      {{ footerText }}
    </a-layout-footer>
  </a-layout>
</template>

<style scoped lang="less">
/* 全局容器：铺满屏幕，禁止最外层滚动 */
.app-layout {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #f0f2f5; /* 更高级的浅灰色背景 */
}

/* 头部设计：白色背景+轻微透明+底部柔和阴影 */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.85); /* 半透明 */
  backdrop-filter: blur(10px); /* 毛玻璃效果 */
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  z-index: 20;

  .header-logo {
    font-size: 20px;
    font-weight: 700;
    color: #1f2937;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #6290c5 0%, #4b79a1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; /* 文字渐变色，显得高级 */
  }

  .header-menu {
    color: #64748b;
  }
}

/* 主体包裹器：占据剩余空间 */
.main-wrapper {
  flex: 1;
  overflow: hidden; /* 内部滚动，外部不滚 */
  position: relative;
}

/* 内容区域 */
.app-content {
  flex: 1;
  overflow-y: auto; /* 只有内容区自己滚动 */
  scroll-behavior: smooth;
  position: relative;

  /* 内容容器：限制最大宽度，防止在大屏上太散，类似于Notion或知乎的设计 */
  .content-container {
    max-width: 1200px;
    margin: 0 auto;
    height: 100%;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }
}

/* Sider 区域：增加左侧边框阴影，使其看起来是浮在上面的面板 */
.app-sider {
  background: #fff;
  border-left: 1px solid rgba(0, 0, 0, 0.06);
  box-shadow: -5px 0 15px rgba(0, 0, 0, 0.02);
  z-index: 15;
  height: 100%;
}

/* Sider 内部容器 */
.sider-content {
  height: 100%;
  overflow-y: auto; /* AI 对话框独立滚动 */
  padding: 16px;
  display: flex;
  flex-direction: column;
}

/* 底部设计 */
.app-footer {
  background: #fff;
  text-align: center;
  padding: 12px;
  color: #94a3b8;
  font-size: 13px;
  border-top: 1px solid rgba(0, 0, 0, 0.03);
  flex-shrink: 0; /* 防止被压缩 */
}

/* 路由切换动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 移动端适配微调 */
@media (max-width: 768px) {
  .app-content {
    padding: 12px;
    .content-container {
      padding: 16px;
      border-radius: 8px;
    }
  }

  .app-header {
    padding: 0 16px;
  }
}
</style>
