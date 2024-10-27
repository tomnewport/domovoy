import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/TasksView.vue'),
      meta: { bottomNav: 0 }
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: () => import('@/views/TasksView.vue'),
      meta: { bottomNav: 0 }
    },
    {
      path: '/homes',
      name: 'homes',
      component: () => import('@/views/HomesView.vue'),
      meta: { bottomNav: 1 }
    },
    {
      path: '/homes/:homeId',
      name: 'HomeDetail',
      component: () => import('@/views/HomeDetailView.vue'),
      meta: { bottomNav: 1 }
    },
    {
      path: '/homes/:homeId/jobs',
      name: 'HomeJobList',
      component: () => import('@/views/HomeJobsView.vue'),
      meta: { bottomNav: 1 }
    },
    {
      path: '/homes/:homeId/jobs/:jobId',
      name: 'HomeJobEditor',
      component: () => import('@/views/HomeJobsView.vue'),
      meta: { bottomNav: 1 }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { bottomNav: 2 }
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('@/views/TasksView.vue'),
      meta: { bottomNav: 3 }
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { bottomNav: false }
    },
    {
      path: '/auth_link/:emailB64/:emailCode',
      name: 'auth_link_login',
      component: () => import('@/views/AuthLinkLogin.vue'),
      meta: { bottomNav: false }
    },
    {
      path: '/auth_link/error',
      name: 'auth_link_error',
      component: () => import('@/views/AuthLinkError.vue'),
      meta: { bottomNav: false }
    }
  ]
})

export default router
