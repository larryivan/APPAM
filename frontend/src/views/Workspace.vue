<template>
  <div
    class="workspace-layout"
    :class="{
      'nav-collapsed': navCollapsed,
      'mobile-nav-open': mobileNavOpen,
      'has-admin-tools': isAdmin,
    }"
  >
    <aside class="workspace-nav" aria-label="Project navigation">
      <header class="project-context">
        <router-link to="/projects" class="back-link" title="All projects" aria-label="All projects">
          <Icon name="layout-grid" :size="18" />
        </router-link>
        <div class="project-copy" aria-live="polite">
          <span>Project</span>
          <strong v-if="project" :title="project.name">{{ project.name }}</strong>
          <span v-else-if="projectLoading" class="project-name-skeleton" aria-label="Loading project"></span>
          <button v-else type="button" class="project-retry" title="Reload project" @click="loadProject">
            <span>{{ projectLoadError || 'Project unavailable' }}</span>
            <Icon name="rotate-ccw" :size="13" />
          </button>
        </div>
        <button
          type="button"
          class="mobile-nav-toggle"
          :class="{ open: mobileNavOpen }"
          :aria-expanded="mobileNavOpen"
          title="Toggle project navigation"
          aria-label="Toggle project navigation"
          @click="mobileNavOpen = !mobileNavOpen"
        >
          <Icon name="chevron-down" :size="16" />
        </button>
      </header>

      <nav class="project-links">
        <router-link
          :to="overviewRoute"
          class="project-link"
          :class="{ active: route.name === 'Overview' && route.hash !== '#analysis-workflows' }"
          title="Overview"
        >
          <Icon name="layout-dashboard" :size="18" />
          <span>Overview</span>
        </router-link>

        <div class="nav-section">
          <div class="nav-group-row">
            <router-link
              :to="analysisHubRoute"
              class="project-link"
              :class="{ active: route.name === 'WorkflowView' || (route.name === 'Overview' && route.hash === '#analysis-workflows') }"
              title="Analysis"
            >
              <Icon name="activity" :size="18" />
              <span>Analysis</span>
            </router-link>
            <button
              type="button"
              class="nav-disclosure"
              :class="{ open: analysisMenuOpen }"
              :aria-expanded="analysisMenuOpen"
              aria-controls="analysis-submenu"
              :title="analysisMenuOpen ? 'Collapse analyses' : 'Expand analyses'"
              @click="toggleMenu('analysis')"
            >
              <Icon name="chevron-down" :size="15" />
            </button>
          </div>
          <Transition name="submenu">
            <div v-if="analysisMenuOpen" id="analysis-submenu" class="nav-submenu">
              <router-link
                v-for="workflow in workflowOptions"
                :key="workflow.id"
                :to="workflowRoute(workflow.id)"
                class="submenu-link"
                :class="{ active: activeWorkflowId === workflow.id }"
              >
                <span class="submenu-marker"></span>
                <span>{{ workflow.shortLabel }}</span>
              </router-link>
            </div>
          </Transition>
        </div>

        <router-link
          :to="filesRoute"
          class="project-link"
          :class="{ active: route.name === 'FileManager' }"
          title="Files"
        >
          <Icon name="folder" :size="18" />
          <span>Files</span>
        </router-link>

        <div class="nav-section">
          <div class="nav-group-row">
            <router-link
              :to="plotsRoute"
              class="project-link"
              :class="{ active: route.name === 'PlotStudio' }"
              title="Plots"
            >
              <Icon name="chart-no-axes-combined" :size="18" />
              <span>Plots</span>
            </router-link>
            <button
              type="button"
              class="nav-disclosure"
              :class="{ open: plotsMenuOpen }"
              :aria-expanded="plotsMenuOpen"
              aria-controls="plots-submenu"
              :title="plotsMenuOpen ? 'Collapse plot options' : 'Expand plot options'"
              @click="toggleMenu('plots')"
            >
              <Icon name="chevron-down" :size="15" />
            </button>
          </div>
          <Transition name="submenu">
            <div v-if="plotsMenuOpen" id="plots-submenu" class="nav-submenu">
              <router-link
                v-for="section in plotSections"
                :key="section.id"
                :to="plotViewRoute(section.id)"
                class="submenu-link"
                :class="{ active: activePlotView === section.id }"
              >
                <span class="submenu-marker"></span>
                <span>{{ section.label }}</span>
              </router-link>
            </div>
          </Transition>
        </div>

        <router-link
          :to="reportsRoute"
          class="project-link"
          :class="{ active: route.name === 'ReportCenter' }"
          title="Reports"
        >
          <Icon name="clipboard-list" :size="18" />
          <span>Reports</span>
        </router-link>

        <div class="nav-section">
          <div class="nav-group-row">
            <router-link
              :to="toolsRoute"
              class="project-link"
              :class="{ active: toolsRouteActive }"
              title="Tools"
            >
              <Icon name="wrench" :size="18" />
              <span>Tools</span>
            </router-link>
            <button
              type="button"
              class="nav-disclosure"
              :class="{ open: toolsMenuOpen }"
              :aria-expanded="toolsMenuOpen"
              aria-controls="tools-submenu"
              :title="toolsMenuOpen ? 'Collapse tool categories' : 'Expand tool categories'"
              @click="toggleMenu('tools')"
            >
              <Icon name="chevron-down" :size="15" />
            </button>
          </div>
          <Transition name="submenu">
            <div v-if="toolsMenuOpen" id="tools-submenu" class="nav-submenu">
              <router-link
                v-for="section in toolSections"
                :key="section.id"
                :to="toolSectionRoute(section.id)"
                class="submenu-link"
                :class="{ active: activeToolSection === section.id }"
              >
                <span class="submenu-marker"></span>
                <span>{{ section.label }}</span>
              </router-link>
            </div>
          </Transition>
        </div>
      </nav>

      <footer class="project-nav-footer">
        <button
          type="button"
          class="nav-collapse-button"
          :title="navCollapsed ? 'Expand project navigation' : 'Collapse project navigation'"
          :aria-label="navCollapsed ? 'Expand project navigation' : 'Collapse project navigation'"
          @click="navCollapsed = !navCollapsed"
        >
          <Icon :name="navCollapsed ? 'panel-left-open' : 'panel-left-close'" :size="17" />
        </button>
      </footer>
    </aside>

    <main class="workspace-content">
      <router-view />
    </main>

    <div v-if="isAdmin" class="admin-runtime-tools" role="group" aria-label="Administrator tools">
      <FloatingSystemMonitor />
      <button
        type="button"
        class="opencode-trigger"
        :disabled="opencodeAvailable !== true"
        :title="openCodeTitle"
        aria-label="Open OpenCode assistant"
        @click="openOpenCodeWindow"
      >
        <Icon name="wand-sparkles" :size="20" />
      </button>
      <FloatingTerminal
        v-if="opencodeAvailable === true"
        ref="openCodeRef"
        preset="opencode"
        title="OpenCode"
        :show-trigger="false"
      />
      <FloatingTerminal />
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onBeforeUnmount, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import { authState } from '@/lib/auth.js'
import { TOOL_SECTION_OPTIONS, normalizeToolSection } from '@/lib/toolUi.js'
import { WORKFLOW_OPTIONS } from '@/lib/workflowUi.js'

const FloatingSystemMonitor = defineAsyncComponent(() => import('@/components/FloatingSystemMonitor.vue'))
const FloatingTerminal = defineAsyncComponent(() => import('@/components/FloatingTerminal.vue'))

const route = useRoute()
const router = useRouter()
const project = ref(null)
provide('appamProject', project)
const projectLoading = ref(true)
const projectLoadError = ref('')
const openCodeRef = ref(null)
const opencodeAvailable = ref(null)
const workflowOptions = WORKFLOW_OPTIONS
const toolSections = TOOL_SECTION_OPTIONS
const plotSections = [
  { id: 'analysis', label: 'Analysis figures' },
  { id: 'create', label: 'Create your own' },
]

const NAV_COLLAPSED_KEY = 'appam.workspace.navigation.collapsed'
const ANALYSIS_MENU_KEY = 'appam.workspace.navigation.analysis-open'
const PLOTS_MENU_KEY = 'appam.workspace.navigation.plots-open'
const TOOLS_MENU_KEY = 'appam.workspace.navigation.tools-open'

function readPreference(key, fallback) {
  if (typeof window === 'undefined') return fallback
  try {
    const value = window.localStorage.getItem(key)
    return value === null ? fallback : value === 'true'
  } catch {
    return fallback
  }
}

function writePreference(key, value) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(key, String(value))
  } catch {
    // Navigation remains usable when storage is unavailable.
  }
}

const navCollapsed = ref(readPreference(NAV_COLLAPSED_KEY, false))
const analysisMenuOpen = ref(readPreference(ANALYSIS_MENU_KEY, true))
const plotsMenuOpen = ref(readPreference(PLOTS_MENU_KEY, true))
const toolsMenuOpen = ref(readPreference(TOOLS_MENU_KEY, false))
const mobileNavOpen = ref(false)
let projectLoadController = null

const projectId = computed(() => String(route.params.id || ''))
const isAdmin = computed(() => authState.user?.role === 'admin')
const activeWorkflowId = computed(() => (
  route.name === 'WorkflowView' ? String(route.params.workflowId || '') : ''
))
const activePlotView = computed(() => {
  if (route.name !== 'PlotStudio') return ''
  return route.query.view === 'create' ? 'create' : 'analysis'
})
const activeToolSection = computed(() => {
  if (!['ToolLibrary', 'PipelineTool'].includes(String(route.name || ''))) return ''
  return normalizeToolSection(route.query.section)
})
const openCodeTitle = computed(() => {
  if (opencodeAvailable.value === null) return 'Checking OpenCode availability'
  return opencodeAvailable.value ? 'Open OpenCode assistant' : 'OpenCode is not configured on this server'
})

const overviewRoute = computed(() => ({ name: 'Overview', params: { id: projectId.value } }))
const analysisHubRoute = computed(() => ({
  name: 'Overview',
  params: { id: projectId.value },
  hash: '#analysis-workflows',
}))
const filesRoute = computed(() => ({ name: 'FileManager', params: { id: projectId.value } }))
const plotsRoute = computed(() => ({
  name: 'PlotStudio',
  params: { id: projectId.value },
  query: { view: 'analysis' },
}))
const reportsRoute = computed(() => ({ name: 'ReportCenter', params: { id: projectId.value } }))
const toolsRoute = computed(() => ({ name: 'ToolLibrary', params: { id: projectId.value } }))
const toolsRouteActive = computed(() => ['ToolLibrary', 'PipelineTool'].includes(String(route.name || '')))

function workflowRoute(workflowId) {
  return {
    name: 'WorkflowView',
    params: { id: projectId.value, workflowId },
  }
}

function toolSectionRoute(sectionId) {
  return {
    name: 'ToolLibrary',
    params: { id: projectId.value },
    query: { section: sectionId },
  }
}

function plotViewRoute(view) {
  return {
    name: 'PlotStudio',
    params: { id: projectId.value },
    query: { view },
  }
}

function toggleMenu(menu) {
  if (navCollapsed.value) {
    navCollapsed.value = false
    if (menu === 'analysis') analysisMenuOpen.value = true
    if (menu === 'plots') plotsMenuOpen.value = true
    if (menu === 'tools') toolsMenuOpen.value = true
    return
  }
  if (menu === 'analysis') analysisMenuOpen.value = !analysisMenuOpen.value
  if (menu === 'plots') plotsMenuOpen.value = !plotsMenuOpen.value
  if (menu === 'tools') toolsMenuOpen.value = !toolsMenuOpen.value
}

function openOpenCodeWindow() {
  if (opencodeAvailable.value === true) openCodeRef.value?.openWindow?.()
}

async function checkOpenCodeAvailability(admin) {
  opencodeAvailable.value = null
  if (!admin) return
  try {
    const response = await fetch('/api/parameter-fill/health')
    const payload = await response.json().catch(() => ({}))
    opencodeAvailable.value = response.ok && payload.available === true
  } catch {
    opencodeAvailable.value = false
  }
}

async function loadProject() {
  const requestedProjectId = projectId.value
  if (!requestedProjectId) {
    project.value = null
    projectLoading.value = false
    return
  }

  projectLoadController?.abort()
  const controller = new AbortController()
  projectLoadController = controller
  projectLoading.value = true
  projectLoadError.value = ''
  try {
    const response = await fetch(`/api/projects/${requestedProjectId}`, { signal: controller.signal })
    if (response.status === 404) {
      if (requestedProjectId === projectId.value) await router.replace('/projects')
      return
    }
    if (!response.ok) throw new Error('Project could not be loaded')
    const payload = await response.json()
    if (!controller.signal.aborted && requestedProjectId === projectId.value) {
      project.value = payload
    }
  } catch (error) {
    if (error?.name === 'AbortError') return
    if (controller.signal.aborted) return
    projectLoadError.value = error instanceof Error ? error.message : 'Project could not be loaded'
    console.error('Failed to load project navigation:', error)
  } finally {
    if (projectLoadController === controller) {
      projectLoadController = null
      projectLoading.value = false
    }
  }
}

watch(projectId, (nextProjectId, previousProjectId) => {
  if (nextProjectId !== previousProjectId) project.value = null
  loadProject()
}, { immediate: true })
watch(isAdmin, checkOpenCodeAvailability, { immediate: true })
watch(navCollapsed, (value) => writePreference(NAV_COLLAPSED_KEY, value))
watch(analysisMenuOpen, (value) => writePreference(ANALYSIS_MENU_KEY, value))
watch(plotsMenuOpen, (value) => writePreference(PLOTS_MENU_KEY, value))
watch(toolsMenuOpen, (value) => writePreference(TOOLS_MENU_KEY, value))
watch(() => route.name, (routeName, previousRouteName) => {
  if (routeName === previousRouteName) return
  mobileNavOpen.value = false
  if (routeName === 'WorkflowView') analysisMenuOpen.value = true
  if (routeName === 'PlotStudio') plotsMenuOpen.value = true
  if (['ToolLibrary', 'PipelineTool'].includes(String(routeName || ''))) toolsMenuOpen.value = true
}, { immediate: true })

onBeforeUnmount(() => projectLoadController?.abort())
</script>

<style scoped>
.workspace-layout {
  display: grid;
  flex: 1 1 auto;
  grid-template-columns: 232px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  min-height: 0;
  background: var(--surface-0);
  overflow: hidden;
  transition: grid-template-columns var(--transition-base);
}

.workspace-layout.nav-collapsed {
  grid-template-columns: 64px minmax(0, 1fr);
}

.workspace-layout.has-admin-tools {
  grid-template-columns: 232px minmax(0, 1fr) 52px;
}

.workspace-layout.nav-collapsed.has-admin-tools {
  grid-template-columns: 64px minmax(0, 1fr) 52px;
}

.workspace-nav {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  border-right: 1px solid var(--border-color-light);
  background: #fbfcfe;
}

.project-context {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--spacing-3);
  min-height: 66px;
  padding: var(--spacing-3);
  border-bottom: 1px solid var(--border-color-light);
}

.back-link {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
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
  flex: 1;
}

.project-copy > span:first-child {
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

.mobile-nav-toggle {
  display: none;
}

.project-name-skeleton {
  display: block;
  width: min(96px, 80%);
  height: 15px;
  margin-top: 2px;
  border-radius: 4px;
  background: var(--surface-3);
  animation: project-pulse 1.25s ease-in-out infinite alternate;
}

.project-retry {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 5px;
  padding: 0;
  overflow: hidden;
  border: 0;
  background: transparent;
  color: var(--error-600);
  font: inherit;
  font-size: var(--text-xs);
  text-align: left;
  cursor: pointer;
}

.project-retry span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@keyframes project-pulse {
  to { opacity: 0.45; }
}

.project-links {
  display: grid;
  align-content: start;
  gap: 3px;
  min-height: 0;
  padding: var(--spacing-3) 10px;
  overflow-x: hidden;
  overflow-y: auto;
}

.project-link {
  position: relative;
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 10px;
  border: 0;
  border-radius: 6px;
  color: var(--gray-600);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.project-link::before {
  position: absolute;
  top: 9px;
  bottom: 9px;
  left: 0;
  width: 2px;
  border-radius: 2px;
  background: var(--accent-500);
  content: '';
  opacity: 0;
}

.project-link:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.project-link.active {
  background: var(--surface-2);
  color: var(--gray-900);
  font-weight: var(--font-semibold);
}

.project-link.active::before {
  opacity: 1;
}

.nav-section {
  display: grid;
  min-width: 0;
}

.nav-group-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 28px;
  align-items: center;
  gap: 2px;
}

.nav-disclosure,
.nav-collapse-button {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-400);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.nav-disclosure:hover,
.nav-collapse-button:hover {
  background: var(--surface-2);
  color: var(--gray-700);
}

.nav-disclosure :deep(.app-icon) {
  transition: transform var(--transition-fast);
}

.nav-disclosure.open :deep(.app-icon) {
  transform: rotate(180deg);
}

.nav-submenu {
  display: grid;
  gap: 1px;
  margin: 2px 0 7px 28px;
  padding-left: 10px;
  border-left: 1px solid var(--border-color);
}

.submenu-link {
  display: flex;
  min-width: 0;
  min-height: 32px;
  align-items: center;
  gap: 8px;
  padding: 0 8px;
  border-radius: 6px;
  color: var(--gray-500);
  font-size: 12.5px;
  text-decoration: none;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.submenu-link:hover {
  background: var(--surface-2);
  color: var(--gray-800);
}

.submenu-link.active {
  background: var(--surface-2);
  color: var(--gray-900);
  font-weight: var(--font-semibold);
}

.submenu-link > span:last-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.submenu-marker {
  width: 4px;
  height: 4px;
  flex: 0 0 4px;
  border-radius: 50%;
  background: var(--gray-300);
}

.submenu-link.active .submenu-marker {
  background: var(--accent-500);
}

.submenu-enter-active,
.submenu-leave-active {
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.submenu-enter-from,
.submenu-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}

.project-nav-footer {
  display: flex;
  min-height: 58px;
  align-items: center;
  justify-content: flex-end;
  margin-top: auto;
  padding: 10px;
  border-top: 1px solid var(--border-color-light);
}

.nav-collapse-button {
  flex: 0 0 28px;
}

.nav-collapsed .project-context {
  justify-content: center;
  padding-inline: 10px;
}

.nav-collapsed .project-copy,
.nav-collapsed .nav-disclosure,
.nav-collapsed .nav-submenu {
  display: none;
}

.nav-collapsed .project-links {
  padding-inline: 10px;
}

.nav-collapsed .nav-group-row {
  grid-template-columns: minmax(0, 1fr);
}

.nav-collapsed .project-link {
  justify-content: center;
  gap: 0;
  padding: 0;
}

.nav-collapsed .project-link > span {
  display: none;
}

.nav-collapsed .project-nav-footer {
  justify-content: center;
}

.workspace-content {
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.admin-runtime-tools {
  position: static;
  z-index: auto;
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
  padding: 6px;
  border-left: 1px solid var(--border-color-light);
  background: #fbfcfe;
}

.opencode-trigger {
  position: static;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--primary-600);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.opencode-trigger:hover:not(:disabled) {
  background: var(--surface-2);
}

.opencode-trigger:disabled {
  border-color: var(--border-color-light);
  color: var(--gray-400);
  cursor: not-allowed;
}

.admin-runtime-tools :deep(.monitor-trigger),
.admin-runtime-tools :deep(.terminal-trigger) {
  position: static;
  display: flex;
}

.admin-runtime-tools :deep(.monitor-button),
.admin-runtime-tools :deep(.terminal-button) {
  width: 40px;
  height: 40px;
  border: 0;
  border-radius: var(--radius-base);
  box-shadow: none;
}

.admin-runtime-tools :deep(.monitor-button:hover),
.admin-runtime-tools :deep(.terminal-button:hover) {
  transform: none;
  box-shadow: none;
}

@media (max-width: 760px) {
  .workspace-layout,
  .workspace-layout.nav-collapsed,
  .workspace-layout.has-admin-tools,
  .workspace-layout.nav-collapsed.has-admin-tools {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
  }

  .workspace-nav {
    max-height: none;
    border-right: 0;
    border-bottom: 1px solid var(--border-color-light);
  }

  .project-context {
    min-height: 48px;
    padding: 7px var(--spacing-3);
  }

  .mobile-nav-toggle {
    display: grid;
    place-items: center;
    width: 32px;
    height: 32px;
    flex: 0 0 32px;
    padding: 0;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-base);
    background: var(--surface-1);
    color: var(--gray-600);
  }

  .mobile-nav-toggle :deep(.app-icon) {
    transition: transform var(--transition-fast);
  }

  .mobile-nav-toggle.open :deep(.app-icon) {
    transform: rotate(180deg);
  }

  .back-link {
    width: 32px;
    height: 32px;
    flex-basis: 32px;
  }

  .nav-collapsed .project-context {
    justify-content: flex-start;
    padding: 7px var(--spacing-3);
  }

  .nav-collapsed .project-copy {
    display: grid;
  }

  .project-links {
    display: none;
    gap: 3px;
    padding: 7px var(--spacing-3) var(--spacing-3);
    max-height: min(42dvh, 360px);
    overflow-y: auto;
  }

  .mobile-nav-open .project-links {
    display: grid;
  }

  .nav-collapsed .nav-group-row {
    grid-template-columns: minmax(0, 1fr) 28px;
  }

  .nav-collapsed .project-link {
    justify-content: flex-start;
    gap: 10px;
    padding: 0 10px;
  }

  .nav-collapsed .project-link > span {
    display: inline;
  }

  .nav-collapsed .nav-disclosure {
    display: grid;
  }

  .nav-collapsed .nav-submenu {
    display: grid;
  }

  .project-nav-footer {
    display: none;
  }

  .admin-runtime-tools {
    position: fixed;
    right: max(12px, env(safe-area-inset-right));
    bottom: max(12px, env(safe-area-inset-bottom));
    z-index: var(--z-fixed, 1030);
    flex-direction: row;
    padding: 4px;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-lg);
    background: rgba(255, 255, 255, 0.96);
    box-shadow: var(--shadow-md);
  }

  .opencode-trigger,
  .admin-runtime-tools :deep(.monitor-button),
  .admin-runtime-tools :deep(.terminal-button) {
    width: 42px;
    height: 42px;
  }
}

@media (max-width: 430px) {
  .nav-submenu {
    margin-left: 27px;
  }
}
</style>
