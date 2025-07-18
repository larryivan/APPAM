import { createRouter, createWebHistory } from 'vue-router'
import Index from './views/Index.vue'
import Documentation from './views/Documentation.vue'
import ProjectList from './views/ProjectList.vue'
import Workspace from './views/Workspace.vue'
import Overview from './views/Overview.vue'
import PipelineTool from './components/PipelineTool.vue'
import FileManagerOptimized from './components/FileManagerOptimized.vue'

const routes = [
  {
    path: '/',
    name: 'Index',
    component: Index
  },
  {
    path: '/documentation',
    name: 'Documentation',
    component: Documentation
  },
  {
    path: '/projects',
    name: 'ProjectList',
    component: ProjectList
  },
  {
    path: '/workspace/:id',
    name: 'Workspace',
    component: Workspace,
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

export default router