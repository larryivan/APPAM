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
        <button class="hero-btn primary" @click="handleOneClickDryRun" :disabled="disableRunActions || !hasInputSetup">
          Prepare + Dry Run
        </button>
        <button class="hero-btn secondary" @click="openRunDialog" :disabled="disableRunActions">
          Run...
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

    <section v-if="hasInputSetup" class="workflow-input-card">
      <div class="panel-header compact">
        <div>
          <h2>Input Setup</h2>
          <p>{{ inputSetupSubtitle }}</p>
        </div>
        <div class="input-actions">
          <button class="hero-btn primary" @click="handleOneClickDryRun" :disabled="disableRunActions || loadingState">
            Prepare + Dry Run
          </button>
          <button class="hero-btn secondary" @click="handlePrepareInputs" :disabled="loadingState">
            Prepare Table
          </button>
          <button class="hero-btn subtle" @click="handleValidateInputs" :disabled="loadingState || !preparedTablePath">
            Validate
          </button>
        </div>
      </div>

      <div class="input-setup-row">
        <button class="file-picker-btn compact" @click="openInputDirPicker">
          {{ inputDataDir || defaultInputDir }}
        </button>
        <span class="setup-state" :class="inputSetupState">
          {{ inputSetupStatus || defaultInputStatus }}
        </span>
        <span v-if="preparedTablePath" class="setup-path mono">{{ preparedTablePath }}</span>
      </div>

      <div v-if="workflow.id === 'appam-paleoproteomics'" class="input-setup-row reference-row">
        <button
          class="file-picker-btn compact"
          @click="openFilePicker({ name: 'fasta_path', type: 'file', extensions: ['.fasta', '.fa', '.faa'] })"
        >
          {{ formValues.fasta_path || 'Reference FASTA' }}
        </button>
        <span class="setup-state" :class="formValues.fasta_path ? 'ok' : 'error'">
          {{ formValues.fasta_path ? 'Reference set' : 'Reference required' }}
        </span>
      </div>

      <div v-if="detectedSamples.length" class="sample-table-wrap">
        <table class="sample-table">
          <thead>
            <tr v-if="workflow.id === 'appam-smk'">
              <th>Sample</th>
              <th>R1</th>
              <th>R2</th>
              <th>Status</th>
            </tr>
            <tr v-else>
              <th>Sample</th>
              <th>Input</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sample in detectedSamples" :key="sample.sample_id">
              <template v-if="workflow.id === 'appam-smk'">
                <td>{{ sample.sample_id }}</td>
                <td class="mono compact-cell">{{ sample.forward_reads || '-' }}</td>
                <td class="mono compact-cell">{{ sample.reverse_reads || '-' }}</td>
                <td>
                  <span class="sample-state" :class="{ ok: sample.forward_reads && sample.reverse_reads, error: !(sample.forward_reads && sample.reverse_reads) }">
                    {{ sample.forward_reads && sample.reverse_reads ? 'Ready' : 'Pair missing' }}
                  </span>
                </td>
              </template>
              <template v-else>
                <td>{{ sample.sample_id }}</td>
                <td class="mono compact-cell">{{ sample.input_path }}</td>
                <td>{{ sample.input_path?.toLowerCase().endsWith('.d') ? 'Bruker' : 'Thermo' }}</td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section class="workflow-graph-card">
      <div class="panel-header">
        <div>
          <h2>Workflow Map</h2>
          <p>Live workflow status.</p>
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
      <div v-if="runtimeHealthChecks.length" class="runtime-checks">
        <div v-for="check in runtimeHealthChecks" :key="`${check.name}-${check.message}`" class="runtime-check" :class="check.status || 'warn'">
          <span class="status-dot"></span>
          <strong>{{ check.name }}</strong>
          <span>{{ check.message }}</span>
        </div>
      </div>
    </section>

    <section class="workflow-activity-card">
      <div class="panel-header tabs">
        <div class="tab-buttons">
          <button :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">Logs</button>
          <button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">Runs</button>
          <button :class="{ active: activeTab === 'results' }" @click="activeTab = 'results'">Results</button>
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

      <div v-else-if="activeTab === 'history'" class="activity-panel">
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

      <div v-else class="activity-panel">
        <div v-if="!displayRun || (displayRun.artifacts || []).length === 0" class="empty-activity">
          <p>No parsed results yet.</p>
          <span>Completed workflow artifacts and summaries will appear here.</span>
        </div>
        <div v-else class="history-grid">
          <div v-for="artifact in displayRun.artifacts" :key="artifact.path" class="history-card artifact-card">
            <div class="history-card-top">
              <strong>{{ artifact.label || artifact.kind || 'Result file' }}</strong>
              <span class="history-state completed">{{ artifact.kind || 'artifact' }}</span>
            </div>
            <div class="history-card-bottom artifact-card-bottom">
              <span class="mono">{{ artifact.path }}</span>
              <span v-if="artifact.size_bytes">{{ formatBytes(artifact.size_bytes) }}</span>
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
            <p>Review inputs and options.</p>
          </div>
          <button class="dialog-close" @click="closeRunDialog" aria-label="Close dialog">×</button>
        </div>

        <div class="run-dialog-body">
          <div v-if="workflowPresets.length" class="preset-strip">
            <button
              v-for="preset in workflowPresets"
              :key="preset.id"
              class="preset-btn"
              :class="{ active: activePresetId === preset.id }"
              @click="applyPreset(preset)"
            >
              {{ preset.label }}
            </button>
          </div>

          <div v-for="param in visibleParameters" :key="param.name" class="compact-field dialog-field">
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

          <button v-if="advancedParameters.length" class="advanced-toggle" @click="showAdvancedParams = !showAdvancedParams">
            {{ showAdvancedParams ? 'Hide Advanced Parameters' : `Show Advanced Parameters (${advancedParameters.length})` }}
          </button>
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
const showAdvancedParams = ref(false)
const activePresetId = ref('')

const formValues = ref({})
const showFilePicker = ref(false)
const currentPickerParam = ref(null)
const tempFileSelection = ref(null)
const runtimeHealth = ref(null)
const manifestStatus = ref('')
const manifestScan = ref(null)
const inputDataDir = ref('')
const inputValidation = ref(null)

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
const hasInputSetup = computed(() => ['appam-smk', 'appam-paleoproteomics'].includes(workflow.value?.id))
const defaultInputDir = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return 'raw_ms'
  return 'raw'
})
const defaultTablePath = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return 'workflow_templates/appam-paleoproteomics/samples.tsv'
  return 'workflow_templates/appam-smk/samples.tsv'
})
const preparedTablePath = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return formValues.value.sample_table
  return formValues.value.sample_manifest
})
const inputSetupSubtitle = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return 'RAW/.d files and sample table'
  return 'FASTQ pairs and sample table'
})
const detectedSamples = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return manifestScan.value?.proteomics_samples || []
  return manifestScan.value?.fastq_samples || []
})
const defaultInputStatus = computed(() => {
  const count = detectedSamples.value.length
  if (!count) return 'No samples scanned'
  if (workflow.value?.id === 'appam-smk') {
    const complete = manifestScan.value?.counts?.complete_fastq_pairs || 0
    return `${complete}/${count} pairs ready`
  }
  return `${count} sample${count === 1 ? '' : 's'} ready`
})
const inputSetupStatus = computed(() => {
  if (manifestStatus.value) return manifestStatus.value
  if (!inputValidation.value) return ''
  if (inputValidation.value.ok) {
    const count = inputValidation.value.samples?.length || 0
    return `${count} sample${count === 1 ? '' : 's'} validated`
  }
  const firstError = (inputValidation.value.checks || []).find((check) => check.status === 'error')
  return compactCheckMessage(firstError)
})
const inputSetupState = computed(() => {
  if (inputValidation.value) return inputValidation.value.ok ? 'ok' : 'error'
  if (workflow.value?.id === 'appam-smk' && detectedSamples.value.length) {
    return (manifestScan.value?.counts?.complete_fastq_pairs || 0) === detectedSamples.value.length ? 'ok' : 'error'
  }
  return detectedSamples.value.length ? 'ok' : ''
})
const basicParameterNames = computed(() => {
  if (workflow.value?.id === 'appam-smk') {
    return new Set([
      'profile',
      'cores',
      'preprocess_method',
      'use_ancient_contigs',
      'enable_checkm2',
      'enable_gunc',
      'enable_prokka',
      'enable_eggnog',
      'enable_abricate',
      'enable_rgi',
      'enable_antismash',
    ])
  }
  if (workflow.value?.id === 'appam-paleoproteomics') {
    return new Set([
      'fasta_path',
      'cores',
      'match_between_runs',
      'include_contaminants',
    ])
  }
  return new Set((workflowTool.value?.parameters || []).map((param) => param.name))
})
const editableParameters = computed(() => (workflowTool.value?.parameters || []).filter((param) => param.name !== 'dry_run'))
const basicParameters = computed(() => editableParameters.value.filter((param) => basicParameterNames.value.has(param.name)))
const advancedParameters = computed(() => editableParameters.value.filter((param) => !basicParameterNames.value.has(param.name)))
const visibleParameters = computed(() => showAdvancedParams.value ? [...basicParameters.value, ...advancedParameters.value] : basicParameters.value)
const workflowPresets = computed(() => {
  if (workflow.value?.id === 'appam-smk') {
    return [
      {
        id: 'quick-validation',
        label: 'Quick validation',
        values: { dry_run: true, enable_antismash: false, enable_rgi: false, enable_eggnog: false, enable_abricate: false, cores: 4 },
      },
      {
        id: 'mag-recovery',
        label: 'MAG recovery',
        values: { dry_run: false, enable_checkm2: true, enable_gunc: true, enable_prokka: false, enable_eggnog: false, enable_abricate: false, enable_rgi: false, enable_antismash: false },
      },
      {
        id: 'full-annotation',
        label: 'Full annotation',
        values: { dry_run: false, enable_checkm2: true, enable_gunc: true, enable_prokka: true, enable_eggnog: true, enable_abricate: true, enable_rgi: false, enable_antismash: true },
      },
      {
        id: 'publication-run',
        label: 'Publication run',
        values: { dry_run: false, enable_checkm2: true, enable_gunc: true, enable_prokka: true, enable_eggnog: true, enable_abricate: true, enable_rgi: true, enable_antismash: true },
      },
    ]
  }
  if (workflow.value?.id === 'appam-paleoproteomics') {
    return [
      { id: 'quick-validation', label: 'Quick validation', values: { dry_run: true, cores: 4, match_between_runs: false } },
      { id: 'publication-run', label: 'Publication run', values: { dry_run: false, cores: 8, match_between_runs: true, include_contaminants: true } },
    ]
  }
  return []
})
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

function formatBytes(bytes) {
  const numeric = Number(bytes)
  if (!Number.isFinite(numeric) || numeric < 0) return ''
  if (numeric < 1024) return `${numeric} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let value = numeric / 1024
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value >= 10 ? value.toFixed(0) : value.toFixed(1)} ${units[unitIndex]}`
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

function compactCheckMessage(check) {
  if (!check) return 'Validation failed'
  if (check.name === 'sample_manifest' || check.name === 'sample_table') return 'Sample table not found'
  if (check.name === 'raw_data_dir') return 'Data folder not found'
  if (check.name === 'sample_rows') return 'No samples in table'
  if (check.name === 'sample_table_columns') return check.message || 'Sample table columns missing'
  if (/_R[12]$/i.test(check.name || '')) return `${check.name} missing`
  if (String(check.message || '').startsWith('Input missing')) return `${check.name} input missing`
  return check.message || 'Validation failed'
}

function applyPreset(preset) {
  activePresetId.value = preset.id
  formValues.value = {
    ...formValues.value,
    ...preset.values,
  }
  if (Object.prototype.hasOwnProperty.call(preset.values, 'dry_run')) {
    runDialogDryRun.value = Boolean(preset.values.dry_run)
  }
}

function applyWorkflowDefaults() {
  if (workflow.value?.id === 'appam-smk') {
    if (!formValues.value.raw_data_dir) {
      formValues.value.raw_data_dir = 'raw'
    }
    if (!formValues.value.sample_manifest) {
      formValues.value.sample_manifest = defaultTablePath.value
    }
    inputDataDir.value = formValues.value.raw_data_dir || defaultInputDir.value
    return
  }
  if (workflow.value?.id === 'appam-paleoproteomics') {
    if (!formValues.value.sample_table) {
      formValues.value.sample_table = defaultTablePath.value
    }
    if (!formValues.value.fasta_path) {
      formValues.value.fasta_path = 'workflow_templates/appam-paleoproteomics/reference.fasta'
    }
    inputDataDir.value = inputDataDir.value || defaultInputDir.value
  }
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
    applyWorkflowDefaults()
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

function workflowDataCandidates() {
  if (!workflow.value) return ['.']
  const candidates = [
    inputDataDir.value,
    formValues.value.raw_data_dir,
    defaultInputDir.value,
  ]
  if (workflow.value.id === 'appam-smk') {
    candidates.push('workflow_templates/appam-smk/raw_fastq', 'workflow_templates/appam-smk', '.')
  } else if (workflow.value.id === 'appam-paleoproteomics') {
    candidates.push('workflow_templates/appam-paleoproteomics/raw_ms', 'workflow_templates/appam-paleoproteomics', '.')
  }
  return [...new Set(candidates.map((value) => String(value || '').trim()).filter(Boolean))]
}

function readySampleCount(scan) {
  if (!scan) return 0
  if (workflow.value?.id === 'appam-paleoproteomics') {
    return scan.proteomics_samples?.length || 0
  }
  return scan.counts?.complete_fastq_pairs || 0
}

function parentPath(path) {
  const value = String(path || '').replace(/\\/g, '/')
  const index = value.lastIndexOf('/')
  if (index <= 0) return index === 0 ? '/' : '.'
  return value.slice(0, index)
}

function inferInputRootFromScan(scan) {
  if (!scan) return ''
  if (workflow.value?.id === 'appam-smk') {
    const parents = new Set()
    for (const sample of scan.fastq_samples || []) {
      if (!sample.forward_reads || !sample.reverse_reads) continue
      const forwardParent = parentPath(sample.forward_reads)
      const reverseParent = parentPath(sample.reverse_reads)
      if (forwardParent === reverseParent) {
        parents.add(forwardParent)
      }
    }
    return parents.size === 1 ? [...parents][0] : ''
  }
  if (workflow.value?.id === 'appam-paleoproteomics') {
    const parents = new Set((scan.proteomics_samples || []).map((sample) => parentPath(sample.input_path)))
    return parents.size === 1 ? [...parents][0] : ''
  }
  return ''
}

async function scanInputData(path) {
  const response = await fetch(`/api/pipeline/${projectId.value}/data/scan?path=${encodeURIComponent(path || '.')}`)
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.error || `Failed to scan ${path || '.'}`)
  }
  return payload
}

async function scanBestInputDir() {
  let firstError = null
  let lastSuccess = null
  for (const candidate of workflowDataCandidates()) {
    try {
      const scan = await scanInputData(candidate)
      lastSuccess = scan
      if (readySampleCount(scan) > 0) return scan
    } catch (error) {
      firstError ||= error
    }
  }
  if (lastSuccess) return lastSuccess
  throw firstError || new Error('No input directory found')
}

async function validatePreparedInputs({ throwOnError = false } = {}) {
  if (!hasInputSetup.value) return null
  const payload = {
    workflow_id: workflow.value.id,
  }
  if (workflow.value.id === 'appam-smk') {
    payload.sample_manifest = formValues.value.sample_manifest
    payload.raw_data_dir = formValues.value.raw_data_dir
  } else {
    payload.sample_table = formValues.value.sample_table
  }
  const response = await fetch(`/api/pipeline/${projectId.value}/data/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const result = await response.json().catch(() => ({}))
  if (!response.ok && result.error) {
    throw new Error(result.error)
  }
  inputValidation.value = result
  if (result.ok) {
    const count = result.samples?.length || 0
    manifestStatus.value = `${count} sample${count === 1 ? '' : 's'} ready`
  } else {
    const firstError = (result.checks || []).find((check) => check.status === 'error')
    manifestStatus.value = compactCheckMessage(firstError)
    if (throwOnError) {
      throw new Error(manifestStatus.value)
    }
  }
  return result
}

async function prepareInputTable({ overwrite = true } = {}) {
  if (!hasInputSetup.value) return null
  manifestStatus.value = ''
  inputValidation.value = null

  const scan = await scanBestInputDir()
  const inferredRoot = inferInputRootFromScan(scan)
  inputDataDir.value = inferredRoot || scan.root || inputDataDir.value || defaultInputDir.value

  const count = readySampleCount(scan)
  if (count < 1) {
    const label = workflow.value.id === 'appam-paleoproteomics' ? 'RAW/.d files' : 'complete FASTQ pairs'
    throw new Error(`No ${label} found in ${inputDataDir.value}`)
  }
  manifestScan.value = inferredRoot && inferredRoot !== scan.root ? await scanInputData(inferredRoot) : scan

  const body = {
    workflow_id: workflow.value.id,
    output_path: preparedTablePath.value || defaultTablePath.value,
    overwrite,
  }
  if (workflow.value.id === 'appam-smk') {
    formValues.value.raw_data_dir = inputDataDir.value
    body.raw_data_dir = inputDataDir.value
  } else {
    body.data_dir = inputDataDir.value
  }

  const response = await fetch(`/api/pipeline/${projectId.value}/data/create-manifest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(payload.error || 'Failed to prepare sample table')
  }

  if (workflow.value.id === 'appam-smk') {
    formValues.value.sample_manifest = payload.path
  } else {
    formValues.value.sample_table = payload.path
  }
  manifestScan.value = payload.scan || scan
  manifestStatus.value = `${payload.samples_written || count} sample${(payload.samples_written || count) === 1 ? '' : 's'} ready`
  await validatePreparedInputs({ throwOnError: true })
  return payload
}

async function handlePrepareInputs() {
  actionError.value = ''
  loadingState.value = true
  try {
    await prepareInputTable({ overwrite: true })
  } catch (error) {
    showActionError(error)
  } finally {
    loadingState.value = false
  }
}

async function handleValidateInputs() {
  actionError.value = ''
  loadingState.value = true
  try {
    await validatePreparedInputs({ throwOnError: true })
  } catch (error) {
    showActionError(error)
  } finally {
    loadingState.value = false
  }
}

async function handleOneClickDryRun() {
  actionError.value = ''
  loadingState.value = true
  try {
    await prepareInputTable({ overwrite: true })
  } catch (error) {
    showActionError(error)
    loadingState.value = false
    return
  }
  loadingState.value = false
  await handleRun(true)
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
  if (!preflightResult.ok) {
    const firstError = (preflightResult.checks || []).find((check) => check.status === 'error')
    throw new Error(firstError?.message || 'Preflight failed')
  }
  if (preflightResult.preflight_id) {
    payload._preflight_id = preflightResult.preflight_id
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
  showAdvancedParams.value = false
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

function openInputDirPicker() {
  currentPickerParam.value = { name: '__input_data_dir', type: 'directory' }
  tempFileSelection.value = inputDataDir.value || defaultInputDir.value
  showFilePicker.value = true
}

function closeFilePicker() {
  if (currentPickerParam.value && tempFileSelection.value !== null) {
    if (currentPickerParam.value.name === '__input_data_dir') {
      inputDataDir.value = tempFileSelection.value
      manifestStatus.value = ''
      manifestScan.value = null
      inputValidation.value = null
      if (workflow.value?.id === 'appam-smk') {
        formValues.value.raw_data_dir = tempFileSelection.value
      }
    } else {
      formValues.value[currentPickerParam.value.name] = tempFileSelection.value
    }
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
    activePresetId.value = ''
    showAdvancedParams.value = false
    manifestStatus.value = ''
    manifestScan.value = null
    inputDataDir.value = ''
    inputValidation.value = null
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

.workflow-input-card,
.workflow-graph-card,
.workflow-activity-card {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 22px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.05);
}

.workflow-input-card {
  margin: 14px 24px 0;
  overflow: hidden;
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

.panel-header.compact {
  align-items: center;
  padding-bottom: 14px;
}

.input-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.input-setup-row {
  display: grid;
  grid-template-columns: minmax(180px, 260px) auto minmax(0, 1fr);
  align-items: center;
  gap: 10px;
  padding: 0 18px 14px;
}

.input-setup-row.reference-row {
  padding-top: 0;
}

.file-picker-btn.compact {
  min-height: 36px;
  border-radius: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.setup-state,
.sample-state {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 9px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.14);
  color: #475569;
  font-size: 0.76rem;
  font-weight: 700;
  white-space: nowrap;
}

.setup-state.ok,
.sample-state.ok {
  background: rgba(55, 168, 102, 0.14);
  color: #166534;
}

.setup-state.error {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.sample-state.error {
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}

.setup-path {
  min-width: 0;
  color: #64748b;
  font-size: 0.78rem;
  overflow-wrap: anywhere;
}

.sample-table-wrap {
  max-height: 260px;
  margin: 0 18px 18px;
  overflow: auto;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: #fff;
}

.sample-table {
  width: 100%;
  min-width: 640px;
  border-collapse: collapse;
}

.sample-table th,
.sample-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  text-align: left;
  font-size: 0.82rem;
  vertical-align: top;
}

.sample-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f8fafc;
  color: #475569;
  font-size: 0.74rem;
  text-transform: uppercase;
}

.sample-table tbody tr:last-child td {
  border-bottom: none;
}

.compact-cell {
  max-width: 360px;
  color: #475569;
  overflow-wrap: anywhere;
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

.runtime-checks {
  display: grid;
  gap: 8px;
  max-height: 180px;
  overflow: auto;
  margin: -4px 18px 18px;
  padding-top: 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.14);
}

.runtime-check {
  display: grid;
  grid-template-columns: 12px minmax(110px, 180px) 1fr;
  align-items: start;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.84);
  color: #475569;
  font-size: 0.78rem;
}

.runtime-check .status-dot {
  margin-top: 4px;
}

.runtime-check strong {
  color: #0f172a;
}

.runtime-check.ok .status-dot { background: #37a866; }
.runtime-check.warn .status-dot { background: #ef8d27; }
.runtime-check.error .status-dot { background: #dc2626; }
.runtime-check.error {
  background: rgba(220, 38, 38, 0.06);
  color: #991b1b;
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

.preset-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-btn,
.advanced-toggle {
  min-height: 34px;
  padding: 0 11px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: #fff;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.preset-btn.active {
  background: rgba(47, 111, 237, 0.1);
  border-color: rgba(47, 111, 237, 0.22);
  color: #1d4ed8;
}

.advanced-toggle {
  width: 100%;
  min-height: 40px;
  background: rgba(148, 163, 184, 0.08);
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

.artifact-card {
  cursor: default;
}

.artifact-card:hover {
  transform: none;
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

.artifact-card-bottom {
  align-items: flex-start;
}

.artifact-card-bottom .mono {
  min-width: 0;
  overflow-wrap: anywhere;
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

  .workflow-input-card,
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

  .input-actions {
    justify-content: flex-start;
  }

  .input-setup-row {
    grid-template-columns: 1fr;
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
