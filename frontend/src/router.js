import { createRouter, createWebHistory } from 'vue-router'
import { authState, loadCurrentUser } from './lib/auth'

const Index = () => import('./views/Index.vue')
const AuthView = () => import('./views/AuthView.vue')
const Documentation = () => import('./views/Documentation.vue')
const ProjectList = () => import('./views/ProjectList.vue')
const SettingsView = () => import('./views/SettingsView.vue')
const AdminUsersView = () => import('./views/AdminUsersView.vue')
const AdminCenterView = () => import('./views/AdminCenterView.vue')
const WorkerStatusView = () => import('./views/WorkerStatusView.vue')
const Workspace = () => import('./views/Workspace.vue')
const Overview = () => import('./views/Overview.vue')
const WorkflowView = () => import('./views/WorkflowView.vue')
const PipelineTool = () => import('./components/PipelineTool.vue')
const FileManagerOptimized = () => import('./components/FileManagerOptimized.vue')

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
    path: '/admin',
    name: 'AdminCenter',
    component: AdminCenterView,
    meta: { requiresAuth: true, requiresAdmin: true }
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
