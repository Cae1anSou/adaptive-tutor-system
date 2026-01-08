<script setup lang="ts">
import { computed } from 'vue';
import { RouterView, useRoute } from 'vue-router';
import { useUserStore } from '@/stores/user';

const userStore = useUserStore();
const route = useRoute();

const isLoginPage = computed(() => route.name === 'login');

const footerText = 'Copyright © 2025 syncPBL by 宋曹卢余蔡吴林';
</script>

<template>
  <div id="BasicLayout" :class="{ 'is-login': isLoginPage }">
    <a-layout class="layout-wrapper">
      <!-- 头部导航（非登录页面显示） -->
      <a-layout-header v-if="!isLoginPage" class="layout-header">
        <div class="header-inner">
          <div class="logo-area">
            <span class="logo-text">SyncPBL智能教学平台</span>
            <span class="logo-icon">🎓</span>
          </div>
          <div class="nav-area">
            <span class="user-greeting">欢迎您，{{ userStore.nickname }}</span>
          </div>
        </div>
      </a-layout-header>

      <a-layout-content class="layout-content">
        <div class="content-wrapper" :class="{ 'is-login': isLoginPage }">
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
      </a-layout-content>

      <!-- 底部（非登录页面显示） -->
      <a-layout-footer v-if="!isLoginPage" class="layout-footer">
        {{ footerText }}
      </a-layout-footer>
    </a-layout>
  </div>
</template>

<style scoped lang="less">
#BasicLayout {
  min-height: 100vh;
  background-color: #f8fafc;
  transition: background 0.5s ease;
}

#BasicLayout.is-login {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

.layout-wrapper {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: transparent;
}

/* 头部设计 */
.layout-header {
  position: fixed;
  top: 0;
  width: 100%;
  z-index: 100;
  height: 64px;
  padding: 0;
  line-height: 64px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);

  .header-inner {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .logo-area {
    display: flex;
    align-items: center;
    gap: 10px;

    .logo-text {
      font-size: 20px;
      font-weight: 700;
      background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      letter-spacing: -0.5px;
    }

    .logo-icon {
      font-size: 24px;
      animation: float 3s ease-in-out infinite;
    }
  }

  .nav-area {
    .user-greeting {
      color: #64748b;
      font-size: 14px;
      padding: 8px 16px;
      background: #f1f5f9;
      border-radius: 20px;
      transition: all 0.3s ease;

      &:hover {
        background: #e2e8f0;
      }
    }
  }
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

/* 内容区域 */
.layout-content {
  flex: 1;
  padding-top: 88px;
  padding-bottom: 24px;
  padding-left: 24px;
  padding-right: 24px;
  display: flex;
  justify-content: center;
  transition: all 0.5s ease;
}

#BasicLayout.is-login .layout-content {
  padding-top: 0;
  padding-bottom: 0;
  padding-left: 0;
  padding-right: 0;
}

/* 内容容器 */
.content-wrapper {
  width: 100%;
  max-width: 1200px;
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  min-height: 280px;
  position: relative;
  transition: all 0.5s ease;
}

/* 登录页面特殊处理 */
.content-wrapper.is-login {
  max-width: none;
  background: transparent;
  border-radius: 0;
  padding: 0;
  box-shadow: none;
  min-height: auto;
}

/* 底部设计 */
.layout-footer {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 20px 0;
  background: transparent;
}

/* 页面切换动画 */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(20px);
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
      padding: 0 20px;
    }
  }

  .layout-content {
    padding-top: 80px;
    padding-left: 16px;
    padding-right: 16px;
  }

  #BasicLayout.is-login .layout-content {
    padding: 0;
  }

  .content-wrapper {
    padding: 24px;
    border-radius: 12px;
  }

  .content-wrapper.is-login {
    padding: 0;
  }

  .logo-area .logo-text {
    font-size: 18px;
  }
}
</style>
