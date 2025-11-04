import { createRouter, createWebHistory } from 'vue-router'
import BasicLayout from '../layouts/BasicLayout.vue'
import SiderLayout from '../layouts/SiderLayout.vue'
import LearningPage from '../pages/LearningPage.vue'
import TestPage from '../pages/TestPage.vue'
import LoginPage from '../pages/LoginPage.vue'
import GraphPage from '../pages/GraphPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: BasicLayout,
      children: [
        {
          path: 'login',
          name: 'login',
          component: LoginPage
        },
        {
          path: 'graph',
          name: 'graph',
          component: GraphPage
        }
      ]
    },
    {
      path: '/',
      component: SiderLayout,
      children: [
        {
          path: 'learning',
          name: 'learning',
          component: LearningPage
        },
        {
          path: 'test',
          name: 'test',
          component: TestPage
        }
      ]
    },
    {
      path: '/',
      redirect: '/test'
    }
  ],
})

export default router
