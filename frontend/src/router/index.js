import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/',
    redirect: '/archives',
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/archives',
    name: 'archives',
    component: () => import('../views/ArchivesView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'archives', action: 'access' } },
  },
  {
    path: '/archives/packs',
    name: 'packs',
    component: () => import('../views/PacksView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'packs', action: 'access' } },
  },
  {
    path: '/archives/upload',
    name: 'upload',
    component: () => import('../views/UploadView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'archives', action: 'modify' } },
  },
  {
    path: '/archives/edit/:id',
    name: 'edit',
    component: () => import('../views/EditView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'archives', action: 'modify' } },
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../views/SettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin/categories',
    name: 'categories',
    component: () => import('../views/CategoriesView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'categories', action: 'access' } },
  },
  {
    path: '/admin/ages',
    name: 'ages',
    component: () => import('../views/AgesView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'ages', action: 'access' } },
  },
  {
    path: '/admin/users',
    name: 'users',
    component: () => import('../views/UsersView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'users', action: 'access' } },
  },
  {
    path: '/admin/roles',
    name: 'roles',
    component: () => import('../views/RolesView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'roles', action: 'access' } },
  },
  {
    path: '/submit',
    name: 'submit',
    component: () => import('../views/SubmitView.vue'),
  },
  {
    path: '/rework',
    name: 'rework',
    component: () => import('../views/ReworkListView.vue'),
  },
  {
    path: '/admin/submissions',
    name: 'submissions',
    component: () => import('../views/SubmissionsView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'submissions', action: 'access' } },
  },
  {
    path: '/admin/submissions/:id',
    name: 'submission-review',
    component: () => import('../views/SubmissionReviewView.vue'),
    meta: { requiresAuth: true, requiredPermission: { scope: 'submissions', action: 'access' } },
  },
  {
    path: '/dmca',
    name: 'dmca',
    component: () => import('../views/DmcaView.vue'),
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login' })
  } else if (to.meta.requiredPermission) {
    const { scope, action } = to.meta.requiredPermission
    if (!authStore.hasPermission(scope, action)) {
      next({ name: 'archives' })
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
