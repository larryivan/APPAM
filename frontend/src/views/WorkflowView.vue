<template>
  <div v-if="workflow && workflowTool" class="workflow-view">
    <header class="workflow-hero">
      <div class="workflow-hero-copy">
        <div class="workflow-kicker">Workflow Automation</div>
        <h1>{{ workflow.title }}</h1>
        <p>{{ workflow.description }}</p>
        <div class="workflow-hero-meta">
          <span class="hero-pill">{{ project?.name || `Project ${projectId}` }}</span>
          <span class="hero-pill subtle">{{ progress.completed }}/{{ progress.total }} tracked stages</span>
        </div>
      </div>
      <div class="workflow-hero-actions">
        <div class="hero-status" :class="statusClass">
          <span class="status-dot"></span>
          <span>{{ statusText }}</span>
        </div>
        <button class="hero-btn primary" @click="openRunDialog" :disabled="disableRunActions">
          Run Workflow
        </button>
        <button
          v-if="activeWorkflowRun"
          class="hero-btn danger"
          @click="handleCancel"
          :disabled="!activeWorkflowRun || !['queued', 'starting', 'running'].includes(activeWorkflowRun.status)"
        >
          Stop
        </button>
        <details class="workflow-more">
          <summary class="hero-btn subtle icon-only" aria-label="More actions">···</summary>
          <div class="workflow-more-menu">
            <button class="more-menu-item" @click="safeRefresh" :disabled="loadingState">Refresh</button>
            <button class="more-menu-item" @click="handleResume" :disabled="!canResumeRun">Resume</button>
            <button class="more-menu-item" @click="safeFetchHealth" :disabled="loadingState">Runtime Health</button>
            <button class="more-menu-item" @click="handleTemplate" :disabled="loadingState">Create Template</button>
            <button class="more-menu-item" @click="handleRetry" :disabled="!canRetryRun">Retry</button>
            <button class="more-menu-item" @click="handleProvenanceExport" :disabled="!displayRun?.id">Export Provenance</button>
          </div>
        </details>
      </div>
    </header>

    <div v-if="actionError" class="workflow-banner error">
      {{ actionError }}
    </div>

    <div v-if="busyByOtherJob" class="workflow-banner warning">
      Another task is active in this project: <strong>{{ currentProjectTask.tool }}</strong>. Workflow execution is locked until it finishes.
    </div>

    <section class="workflow-graph-card">
      <div class="panel-header">
        <div>
          <h2>Workflow Map</h2>
          <p>
            The graph stays central and the current path carries the data flow animation.
          </p>
        </div>
        <div class="graph-side">
          <div class="graph-meta-bar">
            <span class="graph-meta-pill">{{ currentStage?.title || 'Waiting for run' }}</span>
            <span class="graph-meta-pill mono">{{ runtimeState.currentRule || 'No active rule' }}</span>
            <span class="graph-meta-pill subtle">Output: {{ displayRun?.output_root || workflow.outputRoot }}</span>
          </div>
          <div class="graph-legend">
            <span><i class="legend-dot completed"></i>Completed</span>
            <span><i class="legend-dot starting"></i>Starting</span>
            <span><i class="legend-dot running"></i>Running</span>
            <span><i class="legend-dot queued"></i>Queued</span>
            <span><i class="legend-dot pending"></i>Pending</span>
          </div>
        </div>
      </div>

      <div class="workflow-canvas-shell">
        <WorkflowDiagram
          :workflow="workflow"
          :node-states="runtimeState.stateByNode"
          :selected-node-id="selectedNodeId"
          @select-node="selectedNodeId = $event"
        />
      </div>
      <div v-if="selectedNode" class="graph-inspector">
        <div class="graph-inspector-main">
          <div class="selected-stage-title compact">
            <span class="stage-state-badge" :class="nodeVisualState(selectedNode)">
              {{ displayStageLabel(selectedNode.id) }}
            </span>
            <h4>{{ selectedNode.title }}</h4>
          </div>
          <p>{{ selectedNode.description }}</p>
        </div>
        <div class="graph-inspector-meta">
          <span class="inline-pill mono">{{ runtimeState.currentRule || 'No active rule' }}</span>
          <span class="inline-pill">Configured {{ configuredParameterCount }}/{{ workflowTool?.parameters?.length || 0 }}</span>
          <span v-if="displayRun?.failure_label && displayRun.status === 'failed'" class="inline-pill alert">
            {{ displayRun.failure_label }}
          </span>
        </div>
      </div>
    </section>

    <section class="workflow-activity-card">
      <div class="panel-header tabs">
        <div class="tab-buttons">
          <button :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">Logs</button>
          <button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">Runs</button>
        </div>
        <div class="activity-meta">
          <span v-if="displayRun" class="mono">{{ displayRun.id }}</span>
        </div>
      </div>

      <div v-if="activeTab === 'logs'" class="activity-panel">
        <div v-if="logLines.length === 0" class="empty-activity">
          <p>No workflow logs yet.</p>
          <span>Start a run to populate the execution console.</span>
        </div>
        <div v-else class="workflow-log-console">
          <div v-for="(line, index) in logLines" :key="`${index}-${line}`" class="log-row">
            <span class="line-no">{{ String(index + 1).padStart(3, '0') }}</span>
            <span class="line-text">{{ line }}</span>
          </div>
        </div>
      </div>

      <div v-else class="activity-panel">
        <div v-if="workflowRuns.length === 0" class="empty-activity">
          <p>No workflow history yet.</p>
          <span>Completed and failed runs will appear here.</span>
        </div>
        <div v-else class="history-grid">
          <div v-for="run in workflowRuns" :key="run.id" class="history-card" @click="inspectHistoryRun(run)">
            <div class="history-card-top">
              <strong>{{ formatDateTime(run.created_at) }}</strong>
              <span class="history-state" :class="run.status">{{ humanizeStatus(run.status) }}</span>
            </div>
            <div class="history-card-bottom">
              <span class="mono">{{ run.id }}</span>
              <span v-if="run.duration">{{ formatDuration(run.duration) }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <FilePicker
      v-if="showFilePicker"
      :project-id="projectId"
      :extensions="currentPickerParam?.extensions || []"
      :multiple="currentPickerParam?.multiple || false"
      :select-directories="currentPickerParam?.type === 'directory'"
      v-model="tempFileSelection"
      @close="closeFilePicker"
    />

    <div v-if="showRunDialog" class="run-dialog-backdrop" @click.self="closeRunDialog">
      <div class="run-dialog">
        <div class="run-dialog-header">
          <div>
            <div class="workflow-kicker">Run Workflow</div>
            <h3>{{ workflow.title }}</h3>
            <p>Only parameters are shown here. The main page stays focused on execution.</p>
          </div>
          <button class="dialog-close" @click="closeRunDialog" aria-label="Close dialog">×</button>
        </div>

        <div class="run-dialog-body">
          <div v-for="param in workflowTool.parameters" :key="param.name" class="compact-field dialog-field">
            <div class="field-topline">
              <label :for="param.name">{{ param.name }}</label>
              <span class="field-tag">{{ param.type }}</span>
            </div>
            <p class="field-help">{{ param.description }}</p>

            <button
              v-if="param.type === 'file' || param.type === 'directory'"
              class="file-picker-btn"
              @click="openFilePicker(param)"
            >
              {{ formValues[param.name] ? formatValue(formValues[param.name]) : (param.type === 'directory' ? 'Choose Directory' : 'Choose File') }}
            </button>

            <label v-else-if="param.type === 'flag'" class="toggle-row">
              <input
                :id="param.name"
                v-model="formValues[param.name]"
                type="checkbox"
              />
              <span>{{ formValues[param.name] ? 'Enabled' : 'Disabled' }}</span>
            </label>

            <select
              v-else-if="param.options?.length"
              :id="param.name"
              v-model="formValues[param.name]"
              class="compact-input"
            >
              <option v-for="option in param.options" :key="option" :value="option">{{ option }}</option>
            </select>

            <input
              v-else
              :id="param.name"
              v-model="formValues[param.name]"
              :type="param.type === 'integer' || param.type === 'float' ? 'number' : 'text'"
              :step="param.type === 'float' ? '0.01' : undefined"
              class="compact-input"
              :placeholder="param.default ?? ''"
            />
          </div>

          <label class="run-mode-toggle">
            <input v-model="runDialogDryRun" type="checkbox" />
            <span>Run as dry-run first</span>
          </label>
        </div>

        <div class="run-dialog-footer">
          <button class="hero-btn secondary" @click="closeRunDialog">Cancel</button>
          <button class="hero-btn primary" @click="handleRunConfirm" :disabled="loadingState">
            {{ runDialogDryRun ? 'Start Dry Run' : 'Start Workflow' }}
          </button>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="workflow-loading">
    <p>Loading workflow definition...</p>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import FilePicker from '@/components/FilePicker.vue'
import WorkflowDiagram from '@/components/workflow/WorkflowDiagram.vue'
import {
  getWorkflowDefinition,
  initWorkflowFormValues,
  runtimeStateFromWorkflowRun,
  stageLabelFromState,
} from '@/lib/workflowDefinitions'

const route = useRoute()

const projectId = computed(() => String(route.params.id || ''))
const workflow = computed(() => getWorkflowDefinition(String(route.params.workflowId || '')))

const workflowTool = ref(null)
const project = ref(null)
const currentProjectTask = ref({ status: 'not_found' })
const workflowRuns = ref([])
const displayRun = ref(null)
const logText = ref('')
const loadingState = ref(false)
const selectedNodeId = ref(null)
const activeTab = ref('history')
const actionError = ref('')
const showRunDialog = ref(false)
const runDialogDryRun = ref(false)

const formValues = ref({})
const showFilePicker = ref(false)
const currentPickerParam = ref(null)
const tempFileSelection = ref(null)
const runtimeHealth = ref(null)

let refreshTimer = null

const runtimeState = computed(() => {
  if (!workflow.value) {
    return { stateByNode: {}, currentStageId: null, currentRule: null, progress: { completed: 0, total: 0 } }
  }
  return runtimeStateFromWorkflowRun(workflow.value, displayRun.value)
})

const progress = computed(() => runtimeState.value.progress)

const currentStage = computed(() => {
  if (!workflow.value || !runtimeState.value.currentStageId) return null
  return workflow.value.nodes.find((node) => node.id === runtimeState.value.currentStageId) || null
})

const selectedNode = computed(() => {
  if (!workflow.value) return null
  return workflow.value.nodes.find((node) => node.id === selectedNodeId.value) || workflow.value.nodes[0] || null
})

const activeWorkflowRun = computed(() => {
  if (!workflowTool.value) return null
  return workflowRuns.value.find((run) => ['queued', 'starting', 'running'].includes(run.status)) || null
})

const busyByOtherJob = computed(() => {
  if (!workflowTool.value) return false
  return ['queued', 'starting', 'running'].includes(currentProjectTask.value.status) && currentProjectTask.value.tool !== workflowTool.value.tool_name
})

const statusClass = computed(() => {
  if (busyByOtherJob.value) return 'blocked'
  return displayRun.value?.status || currentProjectTask.value.status || 'not_found'
})

const statusText = computed(() => {
  if (busyByOtherJob.value) return 'Project Busy'
  return humanizeStatus(displayRun.value?.status || currentProjectTask.value.status || 'not_found')
})

const disableRunActions = computed(() => {
  if (loadingState.value || !workflowTool.value) return true
  if (busyByOtherJob.value) return true
  return ['queued', 'starting', 'running'].includes(activeWorkflowRun.value?.status)
})
const canRetryRun = computed(() => Boolean(displayRun.value && !['queued', 'starting', 'running'].includes(displayRun.value.status)))
const canResumeRun = computed(() => Boolean(displayRun.value && ['failed', 'canceled'].includes(displayRun.value.status)))
const runtimeHealthChecks = computed(() => runtimeHealth.value?.checks || [])
const configuredParameterCount = computed(() => {
  return (workflowTool.value?.parameters || []).filter((param) => {
    const value = formValues.value[param.name]
    if (param.type === 'flag') {
      return Boolean(value)
    }
    if (Array.isArray(value)) {
      return value.length > 0
    }
    return value !== '' && value !== null && value !== undefined
  }).length
})

const logLines = computed(() => {
  return logText.value
    .split('\n')
    .map((line) => line.trimEnd())
    .filter((line) => line !== '')
    .slice(-160)
})

function formatDateTime(value) {
  if (!value) return 'Unknown'
  const date = new Date(value.replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function formatDuration(seconds) {
  const numeric = Number(seconds)
  if (!Number.isFinite(numeric)) return ''
  if (numeric < 60) return `${Math.round(numeric)}s`
  if (numeric < 3600) return `${Math.floor(numeric / 60)}m ${Math.round(numeric % 60)}s`
  return `${Math.floor(numeric / 3600)}h ${Math.round((numeric % 3600) / 60)}m`
}

function humanizeStatus(status) {
  const mapping = {
    queued: 'Queued',
    starting: 'Starting',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    error: 'Failed',
    canceled: 'Canceled',
    not_found: 'Ready',
    blocked: 'Project Busy',
  }
  return mapping[status] || 'Ready'
}

function nodeVisualState(node) {
  if (!node || !workflow.value) return 'pending'
  return runtimeState.value.stateByNode[node.id] || 'pending'
}

function displayStageLabel(nodeId) {
  return stageLabelFromState(runtimeState.value.stateByNode[nodeId] || 'pending')
}

function formatValue(value) {
  if (Array.isArray(value)) return value.join(', ')
  return value || ''
}

function inspectHistoryRun(run) {
  displayRun.value = run
  activeTab.value = 'logs'
  fetchLogsForRun(run)
}

async function fetchProject() {
  const response = await fetch(`/api/projects/${projectId.value}`)
  if (!response.ok) return
  project.value = await response.json()
}

async function fetchWorkflowTool() {
  if (!workflow.value) return
  const response = await fetch('/api/tools')
  const payload = await response.json()
  if (!response.ok || !payload.success) {
    throw new Error(payload.error || 'Failed to load workflow tools')
  }
  const nextTool = payload.tools_by_key?.[workflow.value.toolId]
  workflowTool.value = nextTool || null
  if (nextTool) {
    formValues.value = initWorkflowFormValues(nextTool.parameters || [])
  }
}

async function fetchCurrentTask() {
  const response = await fetch(`/api/pipeline/${projectId.value}/task-status`)
  const payload = await response.json()
  currentProjectTask.value = payload
}

async function fetchWorkflowRuns() {
  if (!workflowTool.value) return
  const response = await fetch(
    `/api/pipeline/${projectId.value}/workflow-runs?workflow_id=${encodeURIComponent(workflow.value.id)}&limit=20`,
  )
  const payload = await response.json()
  if (!response.ok) return
  workflowRuns.value = payload.workflow_runs || []
}

async function fetchRuntimeHealth() {
  if (!workflowTool.value) return
  const response = await fetch(`/api/pipeline/${projectId.value}/runtime-health/${workflowTool.value.id}`)
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.error || 'Failed to load runtime health')
  }
  runtimeHealth.value = payload
}

async function fetchLogsForRun(run) {
  const jobId = run?.job_id
  if (!jobId) {
    logText.value = ''
    return
  }
  const response = await fetch(`/api/jobs/${jobId}/logs?offset=0&limit=262144`)
  const payload = await response.json()
  if (!response.ok) return
  logText.value = payload.content || ''
}

function syncDisplayRun() {
  if (!workflowTool.value) {
    displayRun.value = null
    return
  }
  if (currentProjectTask.value.workflow_run_id) {
    const active = workflowRuns.value.find((run) => run.id === currentProjectTask.value.workflow_run_id)
    if (active) {
      displayRun.value = active
      return
    }
  }
  if (currentProjectTask.value.tool === workflowTool.value.tool_name && currentProjectTask.value.workflow_run_id) {
    displayRun.value = {
      id: currentProjectTask.value.workflow_run_id,
      job_id: currentProjectTask.value.job_id,
      tool_name: currentProjectTask.value.tool,
      status: currentProjectTask.value.status,
      current_stage_id: currentProjectTask.value.current_stage_id,
      current_stage_title: currentProjectTask.value.current_stage_title,
      current_rule: currentProjectTask.value.current_rule,
      output_root: currentProjectTask.value.output_root,
      stage_states: [],
      created_at: currentProjectTask.value.created_at,
    }
    return
  }
  displayRun.value = workflowRuns.value[0] || null
}

async function refreshAll() {
  if (!workflow.value) return
  if (loadingState.value) return
  loadingState.value = true
  try {
    if (!workflowTool.value) {
      await Promise.all([fetchProject(), fetchWorkflowTool()])
    }
    await fetchCurrentTask()
    await fetchWorkflowRuns()
    if (!runtimeHealth.value) {
      try {
        await fetchRuntimeHealth()
      } catch (error) {
        runtimeHealth.value = {
          checks: [
            {
              name: 'runtime',
              message: error instanceof Error ? error.message : String(error),
            },
          ],
        }
      }
    }
    syncDisplayRun()
    await fetchLogsForRun(displayRun.value)
  } finally {
    loadingState.value = false
  }
}

function showActionError(error) {
  actionError.value = error instanceof Error ? error.message : String(error)
}

async function safeRefresh() {
  actionError.value = ''
  try {
    await refreshAll()
  } catch (error) {
    showActionError(error)
  }
}

async function safeFetchHealth() {
  actionError.value = ''
  try {
    await fetchRuntimeHealth()
  } catch (error) {
    showActionError(error)
  }
}

function validateRequiredFields() {
  const missing = []
  for (const param of workflowTool.value?.parameters || []) {
    if (!param.required) continue
    const value = formValues.value[param.name]
    if (value === '' || value === null || value === undefined || (Array.isArray(value) && value.length === 0) || value === false) {
      missing.push(param.name)
    }
  }
  if (missing.length) {
    throw new Error(`Missing required parameters: ${missing.join(', ')}`)
  }
}

async function runWorkflow(forceDryRun) {
  if (!workflowTool.value) return
  validateRequiredFields()
  const payload = {
    ...formValues.value,
    dry_run: Boolean(forceDryRun),
  }
  const preflightResponse = await fetch(`/api/pipeline/${projectId.value}/preflight/${workflowTool.value.id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const preflightResult = await preflightResponse.json()
  if (!preflightResponse.ok) {
    throw new Error(preflightResult.error || 'Preflight failed')
  }
  const response = await fetch(`/api/pipeline/${projectId.value}/run/${workflowTool.value.id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const result = await response.json()
  if (!response.ok) {
    throw new Error(result.error || 'Failed to start workflow')
  }
  showRunDialog.value = false
  await refreshAll()
}

async function cancelActiveRun() {
  if (!activeWorkflowRun.value?.job_id) return
  const response = await fetch(`/api/jobs/${activeWorkflowRun.value.job_id}/cancel`, {
    method: 'POST',
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.error || 'Failed to cancel workflow')
  }
  await refreshAll()
}

async function rerunWorkflow(mode) {
  if (!displayRun.value?.id) return
  const response = await fetch(`/api/pipeline/${projectId.value}/workflow-runs/${displayRun.value.id}/${mode}`, {
    method: 'POST',
  })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.error || `Failed to ${mode} workflow`)
  }
  await refreshAll()
}

async function createTemplate() {
  if (!workflowTool.value) return
  const response = await fetch(`/api/pipeline/${projectId.value}/workflow-templates/${workflowTool.value.id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ overwrite: false }),
  })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.error || 'Failed to create workflow template')
  }
  actionError.value = `Template created under ${payload.created_directories?.[0] || payload.created_files?.[0] || 'project workspace'}`
}

async function handleRun(forceDryRun) {
  actionError.value = ''
  try {
    await runWorkflow(forceDryRun)
  } catch (error) {
    showActionError(error)
  }
}

function openRunDialog() {
  actionError.value = ''
  runDialogDryRun.value = false
  showRunDialog.value = true
}

function closeRunDialog() {
  showRunDialog.value = false
}

async function handleRunConfirm() {
  await handleRun(runDialogDryRun.value)
}

async function handleCancel() {
  actionError.value = ''
  try {
    await cancelActiveRun()
  } catch (error) {
    showActionError(error)
  }
}

async function handleProvenanceExport() {
  if (!displayRun.value?.id) return
  actionError.value = ''
  try {
    const response = await fetch(`/api/pipeline/${projectId.value}/workflow-runs/${displayRun.value.id}/provenance`)
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.error || 'Failed to export provenance')
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${workflow.value.id}-${displayRun.value.id}-provenance.json`
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    showActionError(error)
  }
}

async function handleResume() {
  actionError.value = ''
  try {
    await rerunWorkflow('resume')
  } catch (error) {
    showActionError(error)
  }
}

async function handleRetry() {
  actionError.value = ''
  try {
    await rerunWorkflow('retry')
  } catch (error) {
    showActionError(error)
  }
}

async function handleTemplate() {
  actionError.value = ''
  try {
    await createTemplate()
  } catch (error) {
    showActionError(error)
  }
}

function openFilePicker(param) {
  currentPickerParam.value = param
  tempFileSelection.value = formValues.value[param.name]
  showFilePicker.value = true
}

function closeFilePicker() {
  if (currentPickerParam.value && tempFileSelection.value !== null) {
    formValues.value[currentPickerParam.value.name] = tempFileSelection.value
  }
  showFilePicker.value = false
  currentPickerParam.value = null
  tempFileSelection.value = null
}

watch(
  () => workflow.value?.id,
  async () => {
    if (!workflow.value) return
    workflowTool.value = null
    displayRun.value = null
    logText.value = ''
    runtimeHealth.value = null
    actionError.value = ''
    await refreshAll()
    selectedNodeId.value = runtimeState.value.currentStageId || workflow.value.nodes[0]?.id || null
  },
  { immediate: true },
)

watch(
  () => runtimeState.value.currentStageId,
  (stageId) => {
    if (stageId && !selectedNodeId.value) {
      selectedNodeId.value = stageId
    }
  },
)

onMounted(() => {
  refreshTimer = window.setInterval(() => {
    refreshAll().catch((error) => {
      console.error('Workflow refresh failed:', error)
    })
  }, 4000)
})

onUnmounted(() => {
  if (refreshTimer) {
    window.clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.workflow-view {
  min-height: 100%;
  background: linear-gradient(180deg, #f6f8fb 0%, #eef3f8 100%);
  color: #0f172a;
}

.workflow-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  padding: 18px 24px 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.82);
}

.workflow-kicker {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(47, 111, 237, 0.12);
  color: #2154b7;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.workflow-hero h1 {
  margin: 8px 0 8px;
  font-size: clamp(1.7rem, 2.6vw, 2.35rem);
  line-height: 1.05;
  letter-spacing: -0.03em;
}

.workflow-hero p {
  max-width: 720px;
  margin: 0;
  color: #475569;
  font-size: 0.94rem;
  line-height: 1.5;
}

.workflow-hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.hero-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid rgba(148, 163, 184, 0.2);
  font-size: 0.82rem;
  color: #0f172a;
}

.hero-pill.subtle {
  background: rgba(255, 255, 255, 0.7);
  color: #475569;
}

.workflow-hero-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  max-width: 320px;
}

.hero-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 13px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.2);
  font-weight: 700;
  color: #475569;
}

.hero-status.running,
.status-value.running {
  color: #975a16;
}

.hero-status.starting,
.status-value.starting {
  color: #1d4ed8;
}

.hero-status.completed,
.status-value.completed {
  color: #166534;
}

.hero-status.failed,
.status-value.failed,
.hero-status.error,
.status-value.error {
  color: #b91c1c;
}

.hero-status.queued,
.status-value.queued {
  color: #c2410c;
}

.hero-status.blocked,
.status-value.blocked {
  color: #7c3aed;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: currentColor;
}

.hero-btn {
  border: none;
  border-radius: 12px;
  min-height: 38px;
  padding: 0 13px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.hero-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.hero-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.hero-btn.primary {
  background: linear-gradient(135deg, #2154b7 0%, #2f6fed 100%);
  color: #fff;
  box-shadow: 0 16px 28px rgba(47, 111, 237, 0.2);
}

.hero-btn.secondary {
  background: #fff;
  color: #0f172a;
  border: 1px solid rgba(148, 163, 184, 0.26);
}

.hero-btn.subtle {
  background: transparent;
  color: #64748b;
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.hero-btn.icon-only {
  min-width: 38px;
  padding: 0 12px;
  font-size: 1.1rem;
  line-height: 1;
}

.hero-btn.danger {
  background: #fff5f5;
  color: #b91c1c;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.workflow-more {
  position: relative;
}

.workflow-more summary {
  list-style: none;
}

.workflow-more summary::-webkit-details-marker {
  display: none;
}

.workflow-more[open] .hero-btn.secondary {
  background: rgba(47, 111, 237, 0.08);
  color: #1d4ed8;
}

.workflow-more-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 20;
  min-width: 180px;
  padding: 8px;
  display: grid;
  gap: 6px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(16px);
}

.more-menu-item {
  min-height: 38px;
  padding: 0 12px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #0f172a;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.more-menu-item:hover:not(:disabled) {
  background: rgba(47, 111, 237, 0.08);
}

.more-menu-item:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.workflow-banner {
  margin: 14px 24px 0;
  padding: 13px 15px;
  border-radius: 14px;
  font-weight: 600;
}

.workflow-banner.error {
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.16);
  color: #b91c1c;
}

.workflow-banner.warning {
  background: rgba(124, 58, 237, 0.08);
  border: 1px solid rgba(124, 58, 237, 0.14);
  color: #6d28d9;
}

.workflow-graph-card,
.workflow-activity-card {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 22px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.05);
}

.workflow-graph-card {
  margin: 14px 24px 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 18px 0;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.panel-header p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 0.92rem;
}

.graph-side {
  display: grid;
  gap: 10px;
  justify-items: end;
}

.graph-meta-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  max-width: 560px;
}

.graph-meta-pill {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  background: rgba(248, 250, 252, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: #334155;
  font-size: 0.8rem;
  font-weight: 600;
}

.graph-meta-pill.subtle {
  color: #64748b;
}

.graph-legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px 10px;
  font-size: 0.74rem;
  color: #64748b;
}

.legend-dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  margin-right: 6px;
  border-radius: 50%;
  background: #cbd5e1;
}

.legend-dot.completed { background: #37a866; }
.legend-dot.starting { background: #60a5fa; }
.legend-dot.running { background: #2f6fed; }
.legend-dot.queued { background: #ef8d27; }
.legend-dot.pending { background: #cbd5e1; }
.legend-dot.optional { background: #94a3b8; }

.workflow-canvas-shell {
  padding: 10px 14px 14px;
}

.graph-inspector {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 0 18px 18px;
}

.graph-inspector-main {
  min-width: 0;
}

.graph-inspector-main p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 0.9rem;
  line-height: 1.5;
}

.graph-inspector-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  max-width: 45%;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

.selected-stage-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.selected-stage-title.compact {
  margin-bottom: 0;
}

.selected-stage-title h4 {
  margin: 0;
  font-size: 1rem;
}

.stage-inline-note {
  margin: -4px 0 12px;
  color: #92400e;
  font-size: 0.84rem;
  font-weight: 600;
}

.stage-state-badge,
.inline-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.12);
  color: #475569;
  font-size: 0.74rem;
  font-weight: 700;
}

.inline-pill.alert {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.stage-state-badge.starting { background: rgba(96, 165, 250, 0.14); color: #1d4ed8; }
.stage-state-badge.running { background: rgba(47, 111, 237, 0.12); color: #1d4ed8; }
.stage-state-badge.completed { background: rgba(55, 168, 102, 0.14); color: #166534; }
.stage-state-badge.queued { background: rgba(239, 141, 39, 0.12); color: #b45309; }
.stage-state-badge.failed,
.stage-state-badge.canceled { background: rgba(220, 38, 38, 0.12); color: #b91c1c; }
.stage-state-badge.optional { background: rgba(148, 163, 184, 0.16); color: #475569; }

.compact-form {
  display: grid;
  gap: 14px;
  padding: 0 20px 20px;
}

.compact-field {
  display: grid;
  gap: 8px;
}

.field-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.field-topline label {
  font-weight: 700;
  font-size: 0.9rem;
}

.field-tag {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.14);
  color: #64748b;
  font-size: 0.7rem;
  font-weight: 700;
}

.field-help {
  margin: 0;
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.45;
}

.compact-input,
.file-picker-btn {
  width: 100%;
  min-height: 42px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  background: #fff;
  padding: 0 14px;
  font-size: 0.92rem;
  color: #0f172a;
}

.file-picker-btn {
  text-align: left;
  cursor: pointer;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 0 4px;
  font-weight: 600;
}

.run-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(10px);
}

.run-dialog {
  width: min(720px, 100%);
  max-height: min(86vh, 960px);
  display: flex;
  flex-direction: column;
  border-radius: 24px;
  background: #ffffff;
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 28px 60px rgba(15, 23, 42, 0.18);
  overflow: hidden;
}

.run-dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
}

.run-dialog-header h3 {
  margin: 10px 0 6px;
  font-size: 1.28rem;
}

.run-dialog-header p {
  margin: 0;
  color: #64748b;
  font-size: 0.9rem;
}

.dialog-close {
  width: 38px;
  height: 38px;
  border: none;
  border-radius: 12px;
  background: rgba(148, 163, 184, 0.12);
  color: #334155;
  font-size: 1.4rem;
  line-height: 1;
  cursor: pointer;
}

.dialog-close:hover {
  background: rgba(148, 163, 184, 0.2);
}

.run-dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 18px 22px;
  display: grid;
  gap: 16px;
}

.dialog-field {
  padding: 14px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.run-mode-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 0 14px;
  border-radius: 16px;
  background: rgba(47, 111, 237, 0.06);
  border: 1px solid rgba(47, 111, 237, 0.12);
  font-weight: 600;
  color: #1e3a8a;
}

.run-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 22px 20px;
  border-top: 1px solid rgba(148, 163, 184, 0.14);
}

.workflow-activity-card {
  margin: 16px 24px 24px;
}

.panel-header.tabs {
  align-items: center;
  padding-bottom: 0;
}

.tab-buttons {
  display: flex;
  gap: 8px;
}

.tab-buttons button {
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: transparent;
  color: #64748b;
  font-weight: 700;
  cursor: pointer;
}

.tab-buttons button.active {
  background: rgba(47, 111, 237, 0.12);
  color: #1d4ed8;
}

.activity-meta {
  padding-top: 2px;
  color: #64748b;
  font-size: 0.8rem;
}

.activity-panel {
  padding: 18px 20px 20px;
}

.workflow-log-console {
  display: grid;
  gap: 6px;
  max-height: 360px;
  overflow: auto;
  padding: 16px;
  border-radius: 18px;
  background: #0f172a;
  color: #dbe4f0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  box-shadow: inset 0 0 0 1px rgba(71, 85, 105, 0.35);
}

.log-row {
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 12px;
  line-height: 1.5;
  font-size: 0.82rem;
}

.line-no {
  color: #64748b;
}

.line-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.history-grid {
  display: grid;
  gap: 12px;
}

.history-card {
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.16);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.history-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 24px rgba(15, 23, 42, 0.06);
}

.history-card-top,
.history-card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-card-bottom {
  margin-top: 10px;
  color: #64748b;
  font-size: 0.82rem;
}

.history-state {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  background: rgba(148, 163, 184, 0.14);
}

.history-state.starting { background: rgba(96, 165, 250, 0.14); color: #1d4ed8; }
.history-state.running { background: rgba(47, 111, 237, 0.12); color: #1d4ed8; }
.history-state.completed { background: rgba(55, 168, 102, 0.14); color: #166534; }
.history-state.queued { background: rgba(239, 141, 39, 0.12); color: #b45309; }
.history-state.failed,
.history-state.error,
.history-state.canceled { background: rgba(220, 38, 38, 0.12); color: #b91c1c; }

.empty-activity,
.workflow-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 220px;
  text-align: center;
  color: #64748b;
}

.empty-activity p,
.workflow-loading p {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.empty-activity span {
  margin-top: 8px;
  font-size: 0.88rem;
}

@media (max-width: 900px) {
  .workflow-hero {
    padding-left: 16px;
    padding-right: 16px;
  }

  .workflow-banner {
    margin-left: 16px;
    margin-right: 16px;
  }

  .workflow-hero {
    flex-direction: column;
  }

  .workflow-hero-actions {
    max-width: 100%;
  }

  .workflow-graph-card {
    margin-left: 16px;
    margin-right: 16px;
  }

  .workflow-activity-card {
    margin: 16px 16px 16px;
  }

  .panel-header {
    flex-direction: column;
    align-items: stretch;
  }

  .graph-side,
  .graph-meta-bar,
  .graph-legend {
    justify-items: start;
    justify-content: flex-start;
  }

  .graph-inspector {
    flex-direction: column;
  }

  .graph-inspector-meta {
    max-width: 100%;
    justify-content: flex-start;
  }

  .run-dialog-backdrop {
    padding: 14px;
  }

  .run-dialog {
    max-height: 92vh;
  }
}
</style>
