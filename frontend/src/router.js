import { createRouter, createWebHistory } from 'vue-router'
import { authState, loadCurrentUser } from './lib/auth'
import { notifyInfo } from './lib/notify'

const AuthView = () => import('./views/AuthView.vue')
const HomeView = () => import('./views/HomeView.vue')
const Documentation = () => import('./views/Documentation.vue')
const ProjectList = () => import('./views/ProjectList.vue')
const SettingsView = () => import('./views/SettingsView.vue')
const AdminLayoutView = () => import('./views/AdminLayoutView.vue')
const AdminUsersView = () => import('./views/AdminUsersView.vue')
const AdminCenterView = () => import('./views/AdminCenterView.vue')
const WorkerStatusView = () => import('./views/WorkerStatusView.vue')
const Workspace = () => import('./views/Workspace.vue')
const Overview = () => import('./views/Overview.vue')
const WorkflowView = () => import('./views/WorkflowView.vue')
const PlotStudioView = () => import('./views/PlotStudioView.vue')
const ReportCenterView = () => import('./views/ReportCenterView.vue')
const ToolLibraryView = () => import('./views/ToolLibraryView.vue')
const NotFoundView = () => import('./views/NotFoundView.vue')
const PipelineTool = () => import('./components/PipelineTool.vue')
const FileManagerOptimized = () => import('./components/FileManagerOptimized.vue')

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HomeView,
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
    component: AdminLayoutView,
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: '',
        name: 'AdminCenter',
        component: AdminCenterView,
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: AdminUsersView,
      },
      {
        path: 'worker',
        name: 'WorkerStatus',
        component: WorkerStatusView,
      },
    ]
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
        path: 'tools',
        name: 'ToolLibrary',
        component: ToolLibraryView
      },
      {
        path: 'plots',
        name: 'PlotStudio',
        component: PlotStudioView
      },
      {
        path: 'reports',
        name: 'ReportCenter',
        component: ReportCenterView
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
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFoundView
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    // Staying on the same view (a tab or query change) should not jump to the top.
    if (to.name === from.name && to.path === from.path) return false
    return { top: 0 }
  }
})

// Views are lazy chunks. After a redeploy an open tab still holds the previous
// build's hashed filenames, so navigation would otherwise fail silently.
router.onError((error, to) => {
  const message = String(error?.message || '')
  const isStaleChunk = /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(message)
  if (isStaleChunk && to?.fullPath) {
    window.location.assign(router.resolve(to).href)
    return
  }
  console.error('Navigation failed:', error)
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
    notifyInfo('That area is limited to administrators.', { title: 'Access denied' })
    return { name: 'ProjectList' }
  }

  if (to.meta.requiresGuest && authState.user) {
    return { name: 'ProjectList' }
  }

  return true
})

export default router
