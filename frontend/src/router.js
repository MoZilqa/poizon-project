import { createRouter, createWebHistory } from 'vue-router'
import { auth } from './api'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    // сайт — только админка; покупатели работают через бота
    { path: '/login', name: 'login', component: () => import('./pages/Login.vue') },
    { path: '/', name: 'orders', component: () => import('./pages/Orders.vue'), meta: { admin: true } },
    { path: '/orders/:id', name: 'order', component: () => import('./pages/Order.vue'), meta: { admin: true }, props: true },
    { path: '/settings', name: 'settings', component: () => import('./pages/Settings.vue'), meta: { admin: true } },
    // старые адреса /admin/... и всё неизвестное
    { path: '/admin/:rest(.*)*', redirect: (to) => '/' + (to.params.rest || []).join('/') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  if (to.meta.admin && !auth.token) return { name: 'login', query: { next: to.fullPath } }
})
