<template>
  <div class="workspace-layout">
    <aside class="workspace-nav" aria-label="Project navigation">
      <header class="project-context">
        <router-link to="/projects" class="back-link" title="All projects" aria-label="All projects">
          <Icon name="layout-grid" :size="18" />
        </router-link>
        <div class="project-copy">
          <span>Project</span>
          <strong :title="project?.name || ''">{{ project?.name || 'Loading...' }}</strong>
        </div>
      </header>

      <nav class="project-links">
        <router-link :to="overviewRoute" class="project-link" :class="{ active: route.name === 'Overview' }">
          <Icon name="layout-dashboard" :size="18" />
          <span>Overview</span>
        </router-link>
        <router-link :to="analysisRoute" class="project-link" :class="{ active: route.name === 'WorkflowView' }">
          <Icon name="activity" :size="18" />
          <span>Analysis</span>
        </router-link>
        <router-link :to="filesRoute" class="project-link" :class="{ active: route.name === 'FileManager' }">
          <Icon name="folder" :size="18" />
          <span>Files</span>
        </router-link>
        <router-link :to="toolsRoute" class="project-link" :class="{ active: toolsRouteActive }">
          <Icon name="wrench" :size="18" />
          <span>Tools</span>
        </router-link>
      </nav>

      <footer v-if="project" class="project-nav-footer">
        <span>Default analysis</span>
        <strong>{{ workflowName }}</strong>
      </footer>
    </aside>

    <main class="workspace-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import { getWorkflowOption } from '@/lib/workflowUi.js'

const route = useRoute()
const router = useRouter()
const project = ref(null)

const projectId = computed(() => String(route.params.id || ''))
const defaultWorkflowId = computed(() => project.value?.analysis_workflow || 'appam-smk')
const workflowName = computed(() => getWorkflowOption(defaultWorkflowId.value)?.shortLabel || 'Not selected')

const overviewRoute = computed(() => ({ name: 'Overview', params: { id: projectId.value } }))
const analysisRoute = computed(() => ({
  name: 'WorkflowView',
  params: { id: projectId.value, workflowId: defaultWorkflowId.value },
}))
const filesRoute = computed(() => ({ name: 'FileManager', params: { id: projectId.value } }))
const toolsRoute = computed(() => ({ name: 'ToolLibrary', params: { id: projectId.value } }))
const toolsRouteActive = computed(() => ['ToolLibrary', 'PipelineTool'].includes(String(route.name || '')))

async function loadProject() {
  if (!projectId.value) return
  try {
    const response = await fetch(`/api/projects/${projectId.value}`)
    if (response.status === 404) {
      await router.replace('/projects')
      return
    }
    if (!response.ok) throw new Error('Project could not be loaded')
    project.value = await response.json()
  } catch (error) {
    console.error('Failed to load project navigation:', error)
  }
}

watch(projectId, loadProject, { immediate: true })
</script>

<style scoped>
.workspace-layout {
  display: grid;
  grid-template-columns: 216px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  min-height: 0;
  background: var(--surface-0);
  overflow: hidden;
}

.workspace-nav {
  display: flex;
  min-width: 0;
  flex-direction: column;
  border-right: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.project-context {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--spacing-3);
  min-height: 64px;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--border-color-light);
}

.back-link {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--gray-600);
  text-decoration: none;
}

.back-link:hover {
  border-color: var(--border-color-dark);
  background: var(--surface-2);
  color: var(--gray-900);
}

.project-copy {
  display: grid;
  min-width: 0;
  gap: 1px;
}

.project-copy span,
.project-nav-footer span {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.project-copy strong {
  overflow: hidden;
  color: var(--gray-900);
  font-size: var(--text-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-links {
  display: grid;
  gap: 4px;
  padding: var(--spacing-4) var(--spacing-3);
}

.project-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  min-height: 42px;
  padding: 0 var(--spacing-3);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--gray-600);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
}

.project-link:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.project-link.active {
  border-color: rgba(var(--accent-rgb), 0.2);
  background: var(--primary-50);
  color: var(--primary-700);
}

.project-nav-footer {
  display: grid;
  gap: 2px;
  margin-top: auto;
  padding: var(--spacing-4);
  border-top: 1px solid var(--border-color-light);
}

.project-nav-footer strong {
  color: var(--gray-700);
  font-size: var(--text-sm);
}

.workspace-content {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

@media (max-width: 760px) {
  .workspace-layout {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
  }

  .workspace-nav {
    border-right: 0;
    border-bottom: 1px solid var(--border-color-light);
  }

  .project-context {
    min-height: 48px;
    padding: 7px var(--spacing-3);
  }

  .back-link {
    width: 32px;
    height: 32px;
    flex-basis: 32px;
  }

  .project-links {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 2px;
    padding: 4px var(--spacing-2) var(--spacing-2);
  }

  .project-link {
    justify-content: center;
    gap: 6px;
    min-height: 38px;
    padding: 0 4px;
    font-size: var(--text-xs);
  }

  .project-nav-footer {
    display: none;
  }
}

@media (max-width: 430px) {
  .project-link {
    display: grid;
    place-items: center;
    gap: 1px;
    min-height: 48px;
  }
}
</style>
