<template>
  <div class="project-home">
    <div class="project-home__inner">
      <PageHeader
        eyebrow="Project"
        :title="project?.name || 'Loading project'"
        :description="project?.description || ''"
      >
        <template #meta>
          <span>{{ accessRoleLabel }}</span>
        </template>
      </PageHeader>

      <div v-if="errorMessage" class="page-notice" role="alert">
        <span>{{ errorMessage }}</span>
        <button type="button" @click="loadProject">Try again</button>
      </div>

      <div v-if="loading" class="loading-state" aria-live="polite">
        <Icon name="rotate-ccw" :size="28" spin />
        <span>Preparing your workspace...</span>
      </div>

      <template v-else-if="project && dashboard">
        <section v-if="homeState" class="next-action" :class="homeState.kind">
          <div class="next-action__copy">
            <div class="section-kicker">Next step</div>
            <div class="next-action__title-row">
              <h2>{{ homeState.title }}</h2>
              <span class="state-badge" :class="homeState.kind">
                <span class="state-dot"></span>
                {{ homeState.status }}
              </span>
            </div>
            <p>{{ homeState.description }}</p>
            <div v-if="homeState.details.length" class="state-details">
              <span v-for="detail in homeState.details" :key="detail">{{ detail }}</span>
            </div>
          </div>
          <div class="next-action__actions">
            <router-link :to="homeState.route" class="primary-action">
              <Icon :name="homeState.icon" :size="17" />
              {{ homeState.action }}
            </router-link>
          </div>
        </section>

        <section
          id="analysis-workflows"
          class="analysis-section"
          :class="{ primary: !homeState }"
        >
          <div class="section-heading">
            <div>
              <div class="section-kicker">Guided workflows</div>
              <h2>Choose an analysis</h2>
            </div>
            <router-link
              :to="{ name: 'ToolLibrary', params: { id: projectId } }"
              class="secondary-action"
            >
              <Icon name="wrench" :size="16" />
              Individual tools
            </router-link>
          </div>

          <div class="analysis-list">
            <article
              v-for="workflow in workflowOptions"
              :key="workflow.id"
              class="analysis-row"
            >
              <div class="analysis-icon">
                <Icon :name="workflow.id === 'appam-smk' ? 'dna' : 'activity'" :size="22" />
              </div>
              <div class="analysis-copy">
                <div class="analysis-title-line">
                  <h3>{{ workflow.label }}</h3>
                </div>
                <p>{{ workflow.description }}</p>
                <span class="input-hint">Input: {{ workflow.inputHint }}</span>
              </div>
              <div class="analysis-state">
                <span :class="['run-state', workflowRun(workflow.id)?.status || 'new']">
                  {{ workflowStateLabel(workflow.id) }}
                </span>
                <router-link :to="workflowActionRoute(workflow.id)" class="row-action">
                  {{ workflowActionLabel(workflow.id) }}
                </router-link>
              </div>
            </article>
          </div>
        </section>

        <section v-if="recentRuns.length" class="recent-section">
          <div class="section-heading compact">
            <div>
              <div class="section-kicker">History</div>
              <h2>Recent analyses</h2>
            </div>
          </div>

          <div class="run-list">
            <router-link
              v-for="run in recentRuns"
              :key="run.id"
              :to="runRoute(run)"
              class="run-row"
            >
              <div>
                <strong>{{ workflowLabel(run.workflow_id) }}</strong>
                <span>{{ formatDateTime(run.created_at) }}</span>
              </div>
              <span :class="['run-state', run.status]">{{ runStatusLabel(run.status) }}</span>
              <span class="run-open">Open</span>
            </router-link>
          </div>
        </section>

      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import Icon from '../components/ui/Icon.vue'
import PageHeader from '../components/ui/PageHeader.vue'
import {
  WORKFLOW_OPTIONS,
  runStatusLabel,
  workflowLabel,
} from '../lib/workflowUi.js'

const route = useRoute()
const projectId = computed(() => String(route.params.id || ''))
const project = ref(null)
const dashboard = ref(null)
const inputScan = ref(null)
const loading = ref(true)
const errorMessage = ref('')
const workflowOptions = WORKFLOW_OPTIONS
let refreshTimer = null

const accessRoleLabel = computed(() => {
  const role = project.value?.access_role
  return role === 'owner' ? 'Project owner' : role === 'admin' ? 'Administrator' : role === 'editor' ? 'Editor' : 'Viewer'
})
const recentRuns = computed(() => (dashboard.value?.recent_runs || []).slice(0, 6))
const latestRun = computed(() => recentRuns.value[0] || null)
const activeJob = computed(() => dashboard.value?.active_job || null)
const analysisHubRoute = computed(() => ({
  name: 'Overview',
  params: { id: projectId.value },
  hash: '#analysis-workflows',
}))

function workflowRun(workflowId) {
  return recentRuns.value.find((run) => run.workflow_id === workflowId) || null
}

function workflowInputCount(workflowId) {
  if (workflowId === 'appam-paleoproteomics') {
    return Number(inputScan.value?.counts?.proteomics_samples || 0)
  }
  return Number(inputScan.value?.counts?.complete_fastq_pairs || 0)
}

function workflowStateLabel(workflowId) {
  const run = workflowRun(workflowId)
  if (run) return runStatusLabel(run.status)
  return workflowInputCount(workflowId) ? 'Ready to start' : 'Not started'
}

function routeFor(workflowId, runId = '', tab = '') {
  const query = {}
  if (runId) query.run = runId
  if (tab) query.tab = tab
  return {
    name: 'WorkflowView',
    params: { id: projectId.value, workflowId },
    query,
  }
}

function runRoute(run) {
  if (!run?.workflow_id) return analysisHubRoute.value
  const tab = run.status === 'completed' ? 'results' : run.status === 'failed' ? 'logs' : 'history'
  return routeFor(run.workflow_id, run.id, tab)
}

function workflowActionRoute(workflowId) {
  const run = workflowRun(workflowId)
  return run ? runRoute(run) : routeFor(workflowId)
}

function workflowActionLabel(workflowId) {
  const status = workflowRun(workflowId)?.status
  if (status === 'completed') return 'View results'
  if (['queued', 'starting', 'running'].includes(status)) return 'View progress'
  if (status === 'failed') return 'Review issue'
  if (workflowInputCount(workflowId)) return 'Review and start'
  return 'Set up'
}

const homeState = computed(() => {
  const job = activeJob.value
  if (job) {
    const workflowId = job.workflow_id || latestRun.value?.workflow_id || ''
    const runId = job.workflow_run_id || ''
    const queued = job.status === 'queued'
    const details = []
    if (job.queue_position) details.push(`Queue position ${job.queue_position}`)
    if (job.current_stage_title) details.push(job.current_stage_title)
    return {
      kind: queued ? 'queued' : 'running',
      title: queued ? 'Your analysis is waiting to start' : `${workflowLabel(workflowId)} is running`,
      status: runStatusLabel(job.status),
      description: queued
        ? 'You can leave this page. APPAM will keep the job in the shared queue.'
        : 'Results will appear automatically as soon as the workflow finishes.',
      details,
      action: 'View progress',
      icon: 'activity',
      route: workflowId ? routeFor(workflowId, runId, 'logs') : analysisHubRoute.value,
    }
  }

  const run = latestRun.value
  if (run?.status === 'failed') {
    return {
      kind: 'failed',
      title: 'The latest analysis needs attention',
      status: 'Needs attention',
      description: run.failure_suggestion || 'Review the issue, correct the input or setup, and retry the analysis.',
      details: [run.failure_label].filter(Boolean),
      action: 'Review and retry',
      icon: 'triangle-alert',
      route: runRoute(run),
    }
  }
  if (run?.status === 'completed') {
    const details = []
    if ((run.metrics || []).length) details.push(`${run.metrics.length} summary metrics`)
    if ((run.artifacts || []).length) details.push(`${run.artifacts.length} result files`)
    return {
      kind: 'completed',
      title: 'Your latest results are ready',
      status: 'Completed',
      description: `Open the ${workflowLabel(run.workflow_id)} summary or continue with another analysis.`,
      details,
      action: 'Open results',
      icon: 'circle-check',
      route: runRoute(run),
    }
  }

  return null
})

async function fetchJson(url) {
  const response = await fetch(url)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.error || 'The workspace could not be loaded.')
  return payload
}

async function loadProject({ background = false } = {}) {
  if (!background) loading.value = true
  errorMessage.value = ''
  try {
    const [nextProject, nextDashboard] = await Promise.all([
      fetchJson(`/api/projects/${projectId.value}`),
      fetchJson(`/api/projects/${projectId.value}/dashboard`),
    ])
    project.value = nextProject
    dashboard.value = nextDashboard
    if (!background || !inputScan.value) {
      inputScan.value = await fetchJson(`/api/pipeline/${projectId.value}/data/scan?path=.`)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

function formatDateTime(value) {
  if (!value) return 'Unknown time'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

async function revealAnalysisSection() {
  if (route.hash !== '#analysis-workflows' || loading.value) return
  await nextTick()
  document.getElementById('analysis-workflows')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}

watch([() => route.hash, loading], revealAnalysisSection)

onMounted(() => {
  loadProject()
  refreshTimer = window.setInterval(() => loadProject({ background: true }), 8000)
})

onUnmounted(() => {
  if (refreshTimer) window.clearInterval(refreshTimer)
})
</script>

<style scoped>
.project-home {
  min-height: 100%;
  background: var(--surface-0);
  color: var(--gray-900);
  overflow-y: auto;
}

.project-home__inner {
  width: min(var(--content-width), 100%);
  margin: 0 auto;
  padding: var(--spacing-6);
}

.state-badge,
.run-state {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  border-radius: var(--radius-sm);
  font-weight: var(--font-semibold);
}

.header-button,
.primary-action,
.secondary-action,
.row-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  min-height: var(--control-height);
  border: 1px solid var(--primary-600);
  border-radius: var(--radius-sm);
  background: var(--primary-600);
  color: white;
  padding: 0 var(--spacing-4);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  text-decoration: none;
}

.header-button.secondary,
.secondary-action {
  border-color: var(--border-color);
  background: var(--surface-1);
  color: var(--gray-700);
}

.page-notice,
.loading-state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-4);
  min-height: 64px;
  padding: var(--spacing-4);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
}

.page-notice {
  border-color: rgba(220, 38, 38, 0.22);
  background: var(--error-50);
  color: var(--error-600);
}

.page-notice button {
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: var(--font-semibold);
  cursor: pointer;
}

.loading-state {
  justify-content: center;
  color: var(--gray-500);
}

.next-action {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--spacing-6);
  align-items: center;
  padding: 20px;
  border: 1px solid var(--border-color);
  border-left: 4px solid var(--primary-500);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
}

.next-action.running { border-left-color: var(--primary-500); }
.next-action.ready { border-left-color: var(--success-500); }
.next-action.queued { border-left-color: var(--warning-500); }
.next-action.completed { border-left-color: var(--success-500); }
.next-action.failed { border-left-color: var(--error-500); }

.section-kicker {
  color: var(--gray-500);
  font-size: 11px;
  font-weight: var(--font-medium);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.next-action__title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-3);
  margin-top: var(--spacing-1);
}

.next-action h2,
.section-heading h2 {
  margin: 0;
  font-size: var(--text-xl);
}

.next-action p {
  max-width: 68ch;
  margin: var(--spacing-2) 0 0;
  color: var(--gray-600);
  line-height: var(--leading-normal);
}

.next-action__actions {
  display: grid;
  gap: var(--spacing-2);
  min-width: 168px;
}

.state-badge {
  gap: 6px;
  padding: 4px 8px;
  background: var(--surface-2);
  color: var(--gray-600);
  font-size: var(--text-xs);
}

.state-badge.completed { background: var(--success-50); color: var(--success-600); }
.state-badge.ready { background: var(--success-50); color: var(--success-600); }
.state-badge.failed { background: var(--error-50); color: var(--error-600); }
.state-badge.queued { background: var(--warning-50); color: var(--warning-600); }
.state-badge.running { background: var(--primary-50); color: var(--primary-700); }

.state-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.state-details {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
  margin-top: var(--spacing-3);
}

.state-details span,
.input-hint {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.state-details span {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--surface-2);
}

.analysis-section,
.recent-section {
  margin-top: var(--spacing-8);
  padding-top: var(--spacing-6);
  border-top: 1px solid var(--border-color-light);
}

.analysis-section.primary {
  margin-top: 0;
  padding-top: 0;
  border-top: 0;
}

#analysis-workflows {
  scroll-margin-top: var(--spacing-4);
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.section-heading.compact { margin-bottom: var(--spacing-3); }

.section-note {
  color: var(--gray-500);
  font-size: var(--text-sm);
}

.analysis-list,
.run-list {
  display: grid;
  gap: var(--spacing-2);
}

.analysis-row {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: var(--spacing-4);
  align-items: center;
  min-height: 112px;
  padding: var(--spacing-4);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
}

.analysis-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-sm);
  background: var(--primary-50);
  color: var(--primary-700);
}

.analysis-title-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.analysis-copy h3 {
  margin: 0;
  font-size: var(--text-base);
}

.analysis-copy p {
  margin: 4px 0;
  color: var(--gray-600);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.analysis-state {
  display: grid;
  justify-items: end;
  gap: var(--spacing-2);
}

.run-state {
  padding: 3px 7px;
  background: var(--surface-2);
  color: var(--gray-600);
  font-size: var(--text-xs);
}

.run-state.completed { background: var(--success-50); color: var(--success-600); }
.run-state.failed { background: var(--error-50); color: var(--error-600); }
.run-state.queued { background: var(--warning-50); color: var(--warning-600); }
.run-state.running,
.run-state.starting { background: var(--primary-50); color: var(--primary-700); }

.row-action {
  min-height: 34px;
  background: var(--surface-1);
  color: var(--primary-700);
}

.run-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 48px;
  gap: var(--spacing-4);
  align-items: center;
  min-height: 62px;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--border-color-light);
  color: inherit;
  text-decoration: none;
}

.run-row > div {
  display: grid;
  gap: 3px;
}

.run-row > div span,
.run-open {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.run-open { text-align: right; }

.workspace-footer {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-4);
  margin-top: var(--spacing-8);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--border-color-light);
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.workspace-footer a {
  color: var(--primary-700);
  font-weight: var(--font-semibold);
  text-decoration: none;
}

@media (max-width: 760px) {
  .project-home__inner { padding: var(--spacing-4); }
  .next-action { grid-template-columns: 1fr; padding: var(--spacing-4); }
  .next-action__actions { grid-template-columns: 1fr 1fr; min-width: 0; }
  .section-heading { align-items: flex-start; flex-direction: column; }
  .analysis-row { grid-template-columns: 40px minmax(0, 1fr); }
  .analysis-state {
    grid-column: 1 / -1;
    grid-template-columns: 1fr auto;
    align-items: center;
    justify-items: start;
  }
  .run-row { grid-template-columns: minmax(0, 1fr) auto; }
  .run-open { display: none; }
}

@media (max-width: 480px) {
  .next-action__actions { grid-template-columns: 1fr; }
  .header-button { flex: 1; }
  .workspace-footer { flex-direction: column; }
}
</style>
