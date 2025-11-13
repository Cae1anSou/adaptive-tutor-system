<script setup lang="ts">
import type { CSSProperties } from 'vue';
import { RouterView } from 'vue-router';

const headerHeight = 64;
const footerHeight = 40;

const isMobile = window.innerWidth <= 768;

const mobileHeaderHeight = 56;
const mobileFooterHeight = 60;

const containerStyle: CSSProperties = {
  minHeight: '100vh',
  display: 'flex',
  flexDirection: 'column'
};

const headerStyle: CSSProperties = {
  background: '#6290c5',
  color: '#efefef',
  padding: isMobile ? '0 16px' : '0 24px',
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
  borderBottom: '1px solid #f0f0f0',
  display: 'flex',
  alignItems: 'center',
  height: isMobile ? `${mobileHeaderHeight}px` : `${headerHeight}px`,
  zIndex: 10
};

const bodyStyle: CSSProperties = {
  padding: isMobile ? '16px' : '24px',
  background: '#f5f7fa',
  flex: 1,
  overflowY: 'auto',
  minHeight: `calc(100vh - ${isMobile ? mobileHeaderHeight : headerHeight}px - ${isMobile ? mobileFooterHeight : footerHeight}px)`
};

const footerStyle: CSSProperties = {
  background: '#fff',
  padding: isMobile ? '12px 16px' : '16px 24px',
  borderTop: '1px solid #f0f0f0',
  textAlign: 'center',
  color: '#666',
  fontSize: isMobile ? '12px' : '14px',
  height: isMobile ? `${mobileFooterHeight}px` : `${footerHeight}px`,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
};

const footerText: string ='Copyright © 2025 syncPBL by 宋曹卢余蔡吴林';
</script>

<template>
  <div id="BasicLayout" :style="containerStyle">
    <a-layout>
      <a-layout-header :style="headerStyle">Header</a-layout-header>
      <a-layout>
        <a-layout-content :style="bodyStyle">
          <RouterView />
        </a-layout-content>
      </a-layout>
      <a-layout-footer :style="footerStyle">{{ footerText }}</a-layout-footer>
    </a-layout>
  </div>
</template>

<style scoped>
#BasicLayout :deep(.ant-layout) {
  background: #f5f7fa;
}

#BasicLayout :deep(.ant-layout-content) {
  background: #f5f7fa;
}

#BasicLayout :deep(.ant-layout-sider-children) {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
