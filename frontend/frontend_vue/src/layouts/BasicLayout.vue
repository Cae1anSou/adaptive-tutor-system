<script setup lang="ts">
import { RouterView } from 'vue-router';

const footerText = 'Copyright © 2025 syncPBL by 宋曹卢余蔡吴林';
</script>

<template>
  <div id="BasicLayout">
    <a-layout class="layout-wrapper">
      <a-layout-header class="layout-header">
        <div class="header-inner">
          <div class="logo-area">
            <span>SyncPBL Platform</span>
          </div>
          <div class="nav-area">
            Header Content
          </div>
        </div>
      </a-layout-header>

      <a-layout-content class="layout-content">
        <div class="content-wrapper">
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </a-layout-content>

      <a-layout-footer class="layout-footer">
        {{ footerText }}
      </a-layout-footer>
    </a-layout>
  </div>
</template>

<style scoped lang="less">
/* 全局容器：
  使用 Flexbox 确保 Footer 始终在底部，
  背景色采用高级灰，营造干净的视觉基调
*/
#BasicLayout {
  min-height: 100vh;
  background-color: #f0f2f5;
}

.layout-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: transparent; /* 让外层背景透视 */
}

/* 头部设计：与 SiderLayout 保持一致的通透感 */
.layout-header {
  position: fixed; /* 固定头部，更符合现代网页习惯 */
  top: 0;
  width: 100%;
  z-index: 100;
  height: 64px;
  padding: 0;
  line-height: 64px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

  .header-inner {
    max-width: 1200px; /* 内容限宽，防止在大屏上太散 */
    margin: 0 auto;
    padding: 0 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .logo-area {
    font-size: 20px;
    font-weight: 700;
    background: linear-gradient(135deg, #6290c5 0%, #4b79a1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;
  }

  .nav-area {
    color: #64748b;
    font-size: 15px;
  }
}

/* 内容区域：弹性伸缩 */
.layout-content {
  flex: 1;
  padding-top: 88px; /* 64px header + 24px gap */
  padding-bottom: 24px;
  padding-left: 24px;
  padding-right: 24px;
  display: flex;
  justify-content: center; /* 内容水平居中 */
}

/* 内容容器：核心卡片 */
.content-wrapper {
  width: 100%;
  max-width: 1200px; /* 限制最大宽度，阅读体验更佳 */
  background: #fff;
  border-radius: 12px; /* 圆角让界面更柔和 */
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05); /* 极轻微的阴影 */
  min-height: 280px; /* 防止内容过少时卡片太扁 */
  position: relative;
}

/* 底部设计 */
.layout-footer {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 24px 0;
  background: transparent;
}

/* 页面切换动画：轻微的上浮淡入效果 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .layout-header {
    padding: 0;
    .header-inner {
      padding: 0 16px;
    }
  }

  .layout-content {
    padding-top: 80px;
    padding-left: 16px;
    padding-right: 16px;
  }

  .content-wrapper {
    padding: 20px;
    border-radius: 8px;
  }
}
</style>
