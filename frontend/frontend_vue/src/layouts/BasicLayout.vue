<script setup lang="ts">
import { RouterView } from 'vue-router';

// 底部版权信息
const footerText = 'Copyright © 2025 syncPBL by 宋曹卢余蔡吴林';
</script>

<template>
  <div id="BasicLayout">
    <a-layout class="app-layout">

      <a-layout-header class="app-header">
        <div class="header-content">
          <div class="header-logo">
            <span>SyncPBL Platform</span>
          </div>
          <div class="header-actions">
            <span>User Center</span>
          </div>
        </div>
      </a-layout-header>

      <a-layout-content class="app-content">
        <div class="content-wrapper">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </a-layout-content>

      <a-layout-footer class="app-footer">
        {{ footerText }}
      </a-layout-footer>

    </a-layout>
  </div>
</template>

<style scoped>
/* 全局布局容器 */
#BasicLayout {
  height: 100vh;
  overflow: hidden; /* 防止整个页面出现滚动条 */
}

.app-layout {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f0f2f5; /* 统一的高级灰底色 */
}

/* Header 样式 - 玻璃拟态 */
.app-header {
  height: 64px;
  padding: 0; /* 内部用 container 控制 padding */
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px); /* 毛玻璃 */
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  z-index: 10;
  flex-shrink: 0; /* 防止被压缩 */
}

.header-content {
  max-width: 1400px; /* 限制头部内容最大宽度，避免在超大屏太散 */
  margin: 0 auto;
  padding: 0 24px;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Logo 样式 - 渐变色 */
.header-logo {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #6290c5 0%, #4b79a1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  cursor: pointer;
}

.header-actions {
  color: #64748b;
  font-size: 14px;
}

/* 内容区域 - 核心逻辑 */
.app-content {
  flex: 1; /* 占据剩余空间 */
  overflow-y: auto; /* 开启内部滚动 */
  scroll-behavior: smooth;
  padding: 24px;
  position: relative;
}

/* 内容包裹器 - 卡片式设计 */
.content-wrapper {
  max-width: 1200px; /* 限制内容最大宽度，阅读体验最佳 */
  margin: 0 auto;
  min-height: 100%; /* 确保内容少时也能撑开 */
  /* 这里根据你的需求：
     如果是纯仪表盘，可以去掉背景色和阴影，让内容自己决定；
     如果是表单或阅读页，保留下方的白色卡片样式会更精致。
  */
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  padding: 32px;
}

/* Footer 样式 */
.app-footer {
  background: transparent; /* 基础布局下 footer 可以透明，显得更轻量 */
  text-align: center;
  padding: 16px;
  color: #94a3b8;
  font-size: 13px;
  flex-shrink: 0;
}

/* 动画效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(10px); /* 微微上浮 */
}

.fade-leave-to {
  opacity: 0;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .header-content, .app-content {
    padding: 16px;
  }

  .content-wrapper {
    padding: 16px;
    border-radius: 8px;
  }

  .header-logo {
    font-size: 18px;
  }
}
</style>
