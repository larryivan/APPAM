import { createRouter, createWebHistory } from 'vue-router'
import Index from './views/Index.vue'
import AuthView from './views/AuthView.vue'
import Documentation from './views/Documentation.vue'
import ProjectList from './views/ProjectList.vue'
import SettingsView from './views/SettingsView.vue'
import AdminUsersView from './views/AdminUsersView.vue'
import WorkerStatusView from './views/WorkerStatusView.vue'
import Workspace from './views/Workspace.vue'
import Overview from './views/Overview.vue'
import WorkflowView from './views/WorkflowView.vue'
import PipelineTool from './components/PipelineTool.vue'
import FileManagerOptimized from './components/FileManagerOptimized.vue'
import { authState, loadCurrentUser } from './lib/auth'

const routes = [
  {
    path: '/',
    name: 'Index',
    component: Index
  },
  {
    path: '/login',
    name: 'Login',
    component: AuthView,
    meta: { requiresGuest: true }
  },
  {
    path: '/documentation',
    name: 'Documentation',
    component: Documentation
  },
  {
    path: '/projects',
    name: 'ProjectList',
    component: ProjectList,
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: SettingsView,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: AdminUsersView,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin/worker',
    name: 'WorkerStatus',
    component: WorkerStatusView,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/workspace/:id',
    name: 'Workspace',
    component: Workspace,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: to => `/workspace/${to.params.id}/overview`
      },
      {
        path: 'overview',
        name: 'Overview',
        component: Overview
      },
      {
        path: 'filemanager',
        name: 'FileManager',
        component: FileManagerOptimized
      },
      {
        path: 'workflow/:workflowId',
        name: 'WorkflowView',
        component: WorkflowView
      },
      {
        path: 'tool/:tool',
        name: 'PipelineTool',
        component: PipelineTool
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  await loadCurrentUser()

  if (to.meta.requiresAuth && !authState.user) {
    return {
      name: 'Login',
      query: { redirect: to.fullPath }
    }
  }

  if (to.meta.requiresAdmin && authState.user?.role !== 'admin') {
    return { name: 'ProjectList' }
  }

  if (to.meta.requiresGuest && authState.user) {
    return { name: 'ProjectList' }
  }

  return true
})

export default router
