import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
// 移除全量引入 ant-design-vue，改为按需引入（通过 unplugin-vue-components 自动处理）
import 'ant-design-vue/dist/reset.css';

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')
