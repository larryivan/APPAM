<template>
  <div v-if="workflow && workflowTool" class="workflow-view">
    <header class="workflow-hero">
      <div class="workflow-hero-copy">
        <div class="workflow-kicker">Analysis</div>
        <h1>{{ workflow.title }}</h1>
        <p>{{ workflow.description }}</p>
        <div class="workflow-hero-meta">
          <span class="hero-pill">{{ project?.name || `Project ${projectId}` }}</span>
          <div class="hero-status" :class="statusClass">
            <span class="status-dot"></span>
            <span>{{ statusText }}</span>
          </div>
        </div>
      </div>
      <div class="workflow-hero-actions">
        <button class="hero-btn primary" @click="handleOneClickRun" :disabled="disableRunActions || !hasReadyInputs">
          {{ startButtonLabel }}
        </button>
        <button class="hero-btn secondary" @click="openRunDialog" :disabled="disableRunActions">
          Options
        </button>
        <button
          v-if="activeWorkflowRun"
          class="hero-btn danger"
          @click="handleCancel"
          :disabled="!activeWorkflowRun || !['queued', 'starting', 'running'].includes(activeWorkflowRun.status)"
        >
          Stop
        </button>
        <details v-if="canResumeRun || canRetryRun || displayRun?.id" class="workflow-more">
          <summary class="hero-btn subtle icon-only" aria-label="More actions">···</summary>
          <div class="workflow-more-menu" @click="closeMoreMenu">
            <button v-if="canResumeRun" class="more-menu-item" @click="handleResume">Resume</button>
            <button v-if="canRetryRun" class="more-menu-item" @click="handleRetry">Retry</button>
            <button v-if="displayRun?.id" class="more-menu-item" @click="handleProvenanceExport">Export run record</button>
          </div>
        </details>
      </div>
    </header>

    <div v-if="actionError" class="workflow-banner error">
      <div class="workflow-banner-copy">
        <strong>{{ actionError }}</strong>
        <span v-if="actionErrorHint">{{ actionErrorHint }}</span>
      </div>
      <details v-if="actionErrorDetails" class="error-details">
        <summary>Technical details</summary>
        <pre>{{ actionErrorDetails }}</pre>
      </details>
    </div>

    <div v-if="busyByOtherJob" class="workflow-banner warning">
      Another task is active in this project: <strong>{{ currentProjectTask.tool }}</strong>. Workflow execution is locked until it finishes.
    </div>

    <section v-if="hasInputSetup" class="workflow-input-card">
      <div class="panel-header compact">
        <div>
          <h2>Data</h2>
          <p>{{ inputSetupSubtitle }}. Samples are detected and validated automatically.</p>
        </div>
        <div class="input-actions">
          <button class="hero-btn subtle" @click="handleRescanInputs" :disabled="loadingState">
            Rescan
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

      <div v-if="!detectedSamples.length" class="quick-upload">
        <DragDropUpload
          :project-id="projectId"
          :current-path="quickUploadPath"
          @upload-complete="handleQuickUploadComplete"
          @upload-error="handleQuickUploadError"
        />
        <p><router-link :to="{ name: 'FileManager', params: { id: projectId } }">Browse all project files</router-link></p>
      </div>

      <details v-if="detectedSamples.length" class="sample-review">
        <summary>
          Review {{ detectedSamples.length }} detected sample{{ detectedSamples.length === 1 ? '' : 's' }}
        </summary>
        <div class="sample-table-wrap">
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
      </details>
    </section>

    <section v-if="workflowRuns.length || displayRun" class="workflow-activity-card">
      <div class="panel-header tabs">
        <div class="tab-buttons">
          <button :class="{ active: activeTab === 'results' }" @click="activeTab = 'results'">Results</button>
          <button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">History</button>
          <button :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">Details</button>
        </div>
        <div class="activity-meta">
          <span v-if="displayRun" class="mono">{{ displayRun.id }}</span>
        </div>
      </div>

      <div v-if="activeTab === 'logs'" class="activity-panel">
        <div v-if="logLines.length === 0" class="empty-activity">
          <p>No run details yet.</p>
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

      <div v-else class="activity-panel result-panel">
        <div v-if="!hasParsedResults" class="empty-activity">
          <p>No parsed results yet.</p>
          <span>Completed workflow artifacts and summaries will appear here.</span>
        </div>
        <template v-else>
          <section v-if="primaryResultReport || resultFigures.length" class="result-destinations" aria-label="Explore analysis results">
            <div class="result-destinations__copy">
              <span class="result-destinations__icon"><Icon name="layout-dashboard" :size="19" /></span>
              <span>
                <strong>Explore this run</strong>
                <small>Reports and figures stay linked to the source analysis.</small>
              </span>
            </div>
            <div class="result-destinations__actions">
              <router-link v-if="primaryResultReport" :to="reportCenterRoute(primaryResultReport)">
                <Icon name="clipboard-list" :size="16" />
                <span>Open report</span>
              </router-link>
              <router-link v-if="resultFigures.length" :to="resultFiguresRoute">
                <Icon name="images" :size="16" />
                <span>{{ resultFigures.length }} {{ resultFigures.length === 1 ? 'figure' : 'figures' }}</span>
              </router-link>
            </div>
          </section>

          <div v-if="resultMetricCards.length" class="result-metric-grid">
            <article v-for="metric in resultMetricCards" :key="metricKey(metric)" class="result-metric">
              <span>{{ humanizeMetric(metric.metric_name) }}</span>
              <strong>{{ displayMetric(metric) }}</strong>
              <small>{{ metricNote(metric) }}</small>
            </article>
          </div>

          <section v-for="group in artifactGroups" :key="group.kind" class="artifact-group">
            <header>
              <h4>{{ group.label }}</h4>
              <span>{{ group.items.length }}</span>
            </header>
            <div class="artifact-list">
              <div v-for="artifact in group.items" :key="artifact.id || artifact.path" class="artifact-row">
                <div class="artifact-copy">
                  <strong>{{ artifact.label || artifactFileName(artifact) }}</strong>
                  <span class="mono">{{ artifact.project_path || artifactFileName(artifact) }}</span>
                </div>
                <span class="artifact-size">{{ formatBytes(artifact.size_bytes) }}</span>
                <div class="artifact-actions">
                  <button
                    v-if="isPlotTableArtifact(artifact)"
                    type="button"
                    title="Create a plot from this table"
                    @click="plotArtifact(artifact)"
                  >
                    <Icon name="chart-no-axes-combined" :size="15" />
                  </button>
                  <button
                    type="button"
                    :title="artifactOpenTitle(artifact)"
                    :disabled="!artifact.project_path"
                    @click="openArtifactPreview(artifact)"
                  >
                    <Icon :name="artifactOpenIcon(artifact)" :size="15" />
                  </button>
                  <button
                    type="button"
                    title="Download result"
                    :disabled="!artifact.project_path"
                    @click="downloadArtifact(artifact)"
                  >
                    <Icon name="download" :size="15" />
                  </button>
                </div>
              </div>
            </div>
          </section>
        </template>
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

    <FilePreviewModal
      :show-modal="artifactPreviewOpen"
      :file-name="artifactPreviewName"
      :preview-data="artifactPreviewData"
      :project-id="projectId"
      :file-path="artifactPreviewPath"
      @close="closeArtifactPreview"
      @download="downloadPreviewArtifact"
    />

    <Modal
      :open="showRunDialog"
      eyebrow="Run analysis"
      :title="workflow.title"
      subtitle="Review inputs and options."
      size="lg"
      @close="closeRunDialog"
    >
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
              <label :for="param.name">{{ parameterLabel(param.name) }}</label>
              <span v-if="showAdvancedParams" class="field-tag">{{ param.type }}</span>
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
              :min="param.minimum"
              :max="param.maximum"
              class="compact-input"
              :placeholder="param.default ?? ''"
            />
          </div>

          <details class="run-technical-options">
            <summary>Technical run options</summary>
            <label class="run-mode-toggle">
              <input v-model="runDialogDryRun" type="checkbox" />
              <span>Validate the workflow graph without running analysis</span>
            </label>
          </details>

          <button v-if="advancedParameters.length" class="advanced-toggle" @click="showAdvancedParams = !showAdvancedParams">
            {{ showAdvancedParams ? 'Hide advanced parameters' : `Show advanced parameters (${advancedParameters.length})` }}
          </button>
        </div>

      <template #footer>
        <button class="hero-btn secondary" @click="closeRunDialog">Cancel</button>
        <button class="hero-btn primary" @click="handleRunConfirm" :disabled="loadingState">
          {{ runDialogDryRun ? 'Validate setup' : 'Start analysis' }}
        </button>
      </template>
    </Modal>
  </div>

  <div v-else class="workflow-loading">
    <p>Loading workflow definition...</p>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FilePicker from '@/components/FilePicker.vue'
import FilePreviewModal from '@/components/FilePreviewModal.vue'
import DragDropUpload from '@/components/DragDropUpload.vue'
import Icon from '@/components/ui/Icon.vue'
import Modal from '@/components/ui/Modal.vue'
import { collectWorkflowFigures } from '@/lib/plotStudio.js'
import {
  collectWorkflowReports,
  isPlotTableArtifact,
  isPreviewFigureArtifact,
  isReportArtifact,
} from '@/lib/resultArtifacts.js'
import { describeWorkflowError, parameterLabel } from '@/lib/workflowUi.js'
import {
  getWorkflowDefinition,
  initWorkflowFormValues,
} from '@/lib/workflowDefinitions'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => String(route.params.id || ''))
const workflow = computed(() => getWorkflowDefinition(String(route.params.workflowId || '')))

const workflowTool = ref(null)
const project = ref(null)
const currentProjectTask = ref({ status: 'not_found' })
const workflowRuns = ref([])
const displayRun = ref(null)
const logText = ref('')
const loadingState = ref(false)
const activeTab = ref('history')
const actionError = ref('')
const actionErrorHint = ref('')
const actionErrorDetails = ref('')
const showRunDialog = ref(false)
const runDialogDryRun = ref(false)
const showAdvancedParams = ref(false)
const activePresetId = ref('')

const formValues = ref({})
const showFilePicker = ref(false)
const currentPickerParam = ref(null)
const tempFileSelection = ref(null)
const manifestStatus = ref('')
const manifestScan = ref(null)
const inputDataDir = ref('')
const inputValidation = ref(null)
const refreshingState = ref(false)
const logOffset = ref(0)
const logJobId = ref(null)
const logEof = ref(false)
const artifactPreviewOpen = ref(false)
const artifactPreviewName = ref('')
const artifactPreviewPath = ref('')
const artifactPreviewData = ref({})

let refreshTimer = null
let disposed = false

function scheduleRefresh(delay = 0) {
  if (disposed) return
  if (refreshTimer) window.clearTimeout(refreshTimer)
  refreshTimer = window.setTimeout(async () => {
    // The component can unmount while refreshAll() is in flight; without this
    // the finally block below would start a poll loop nothing can ever clear.
    if (disposed) return
    try {
      await refreshAll()
    } catch (error) {
      console.error('Workflow refresh failed:', error)
    } finally {
      if (!disposed) {
        const active = Boolean(activeWorkflowRun.value)
        scheduleRefresh(active ? 4000 : 12000)
      }
    }
  }, delay)
}

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
  if (!displayRun.value && currentProjectTask.value.status === 'not_found') return 'Not started'
  return humanizeStatus(displayRun.value?.status || currentProjectTask.value.status || 'not_found')
})

const disableRunActions = computed(() => {
  if (loadingState.value || !workflowTool.value) return true
  if (busyByOtherJob.value) return true
  return ['queued', 'starting', 'running'].includes(activeWorkflowRun.value?.status)
})
const startButtonLabel = computed(() => {
  if (!hasReadyInputs.value) return 'Add data to continue'
  return loadingState.value ? 'Preparing analysis...' : 'Start analysis'
})
const canRetryRun = computed(() => Boolean(displayRun.value && ['failed', 'canceled'].includes(displayRun.value.status)))
const canResumeRun = computed(() => Boolean(displayRun.value && ['failed', 'canceled'].includes(displayRun.value.status)))
const hasInputSetup = computed(() => ['appam-smk', 'appam-paleoproteomics'].includes(workflow.value?.id))
const defaultInputDir = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return 'raw_ms'
  return 'raw'
})
const defaultTablePath = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return 'workflow_templates/appam-paleoproteomics/samples.tsv'
  return 'workflow_templates/appam-smk/samples.tsv'
})
const quickUploadPath = computed(() => {
  const current = String(inputDataDir.value || '').trim()
  return current && current !== '.' ? current : defaultInputDir.value
})
const preparedTablePath = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return formValues.value.sample_table
  return formValues.value.sample_manifest
})
const inputSetupSubtitle = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return 'RAW or Bruker .d files'
  return 'Paired FASTQ files'
})
const detectedSamples = computed(() => {
  if (workflow.value?.id === 'appam-paleoproteomics') return manifestScan.value?.proteomics_samples || []
  return manifestScan.value?.fastq_samples || []
})
const hasReadyInputs = computed(() => {
  if (!detectedSamples.value.length) return false
  if (workflow.value?.id === 'appam-smk') {
    return (manifestScan.value?.counts?.complete_fastq_pairs || 0) > 0
  }
  return true
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
      'enable_bin_refinement',
      'enable_checkm1',
      'enable_checkm2',
      'enable_gunc',
      'enable_gtdbtk',
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
      'maxquant_mode',
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
        id: 'recommended',
        label: 'Recommended',
        values: {},
      },
      {
        id: 'quick-validation',
        label: 'Quick validation',
        values: { dry_run: true, use_ancient_contigs: false, enable_bin_refinement: false, enable_checkm1: false, enable_checkm2: false, enable_gunc: false, enable_gtdbtk: false, enable_prokka: false, enable_antismash: false, enable_rgi: false, enable_eggnog: false, enable_abricate: false, enable_variants: false, enable_visualization: true, cores: 4 },
      },
      {
        id: 'mag-recovery',
        label: 'MAG recovery',
        values: { dry_run: false, use_ancient_contigs: false, enable_bin_refinement: false, enable_checkm1: false, enable_checkm2: true, enable_gunc: true, enable_gtdbtk: true, enable_prokka: false, enable_eggnog: false, enable_abricate: false, enable_rgi: false, enable_antismash: false, enable_variants: false, enable_visualization: true },
      },
      {
        id: 'full-annotation',
        label: 'Full annotation',
        values: { dry_run: false, use_ancient_contigs: false, enable_bin_refinement: false, enable_checkm1: false, enable_checkm2: true, enable_gunc: true, enable_gtdbtk: true, enable_prokka: true, enable_eggnog: true, enable_abricate: true, enable_rgi: false, enable_antismash: true, enable_variants: false, enable_visualization: true },
      },
      {
        id: 'publication-run',
        label: 'Publication run',
        values: { dry_run: false, input_hash_mode: 'sha256', require_database_manifest: true, use_ancient_contigs: false, enable_bin_refinement: false, enable_checkm1: false, enable_checkm2: true, enable_gunc: true, enable_gtdbtk: true, enable_prokka: true, enable_eggnog: false, enable_abricate: false, enable_rgi: false, enable_antismash: false, enable_variants: false, enable_visualization: true },
      },
    ]
  }
  if (workflow.value?.id === 'appam-paleoproteomics') {
    return [
      { id: 'recommended', label: 'Recommended', values: {} },
      { id: 'quick-validation', label: 'Quick validation', values: { dry_run: true, cores: 4, match_between_runs: false, maxquant_mode: 'batch' } },
      { id: 'publication-run', label: 'Publication run', values: { dry_run: false, input_hash_mode: 'sha256', cores: 8, match_between_runs: false, include_contaminants: true, maxquant_mode: 'batch' } },
    ]
  }
  return []
})
const hasParsedResults = computed(() => Boolean(
  displayRun.value && (
    (displayRun.value.artifacts || []).length > 0
    || (displayRun.value.metrics || []).length > 0
  )
))

// 'counts' are per-module file tallies for operators (did each module write
// output?). They stay in the run record but are not results, so they never
// take a headline slot.
const HEADLINE_EXCLUDED_GROUPS = new Set(['counts'])

// Read as a sentence: how much was analysed, what was recovered, how good it
// is, what it is, and whether it is ancient.
const OVERVIEW_ORDER = Object.freeze([
  'samples',
  'mags_recovered',
  'high_quality_mags',
  'medium_quality_mags',
  'median_completeness',
  'median_contamination',
  'genera',
  'damage_supported_contigs',
])

const resultMetricCards = computed(() => {
  const priority = ['overview', 'maxquant', 'paleoproteomics_qc', 'checkm2', 'gunc', 'gtdbtk', 'abricate', 'rgi', 'antismash']
  const metrics = (displayRun.value?.metrics || []).filter((metric) => !HEADLINE_EXCLUDED_GROUPS.has(metric.metric_group))
  const rank = (list, value) => {
    const index = list.indexOf(value)
    return index === -1 ? list.length : index
  }
  metrics.sort((left, right) => (
    rank(priority, left.metric_group) - rank(priority, right.metric_group)
    || rank(OVERVIEW_ORDER, left.metric_name) - rank(OVERVIEW_ORDER, right.metric_name)
  ))
  const seen = new Set()
  return metrics.filter((metric) => {
    const key = metricKey(metric)
    if (seen.has(key)) return false
    seen.add(key)
    return (metric.metric_value !== null && metric.metric_value !== undefined) || metric.metric_text
  }).slice(0, 8)
})

const artifactGroups = computed(() => {
  const labels = {
    summary: 'Summary',
    report: 'Reports',
    quality: 'Quality control',
    taxonomy: 'Taxonomy',
    annotation: 'Annotations',
    maxquant: 'MaxQuant tables',
    spectra: 'Spectra',
    damage: 'Damage analysis',
    fasta: 'Sequences',
    visualization: 'Visualizations',
    variants: 'Variants',
    config: 'Configuration',
  }
  const order = Object.keys(labels)
  const groups = new Map()
  for (const artifact of displayRun.value?.artifacts || []) {
    const kind = artifact.kind || 'files'
    if (!groups.has(kind)) groups.set(kind, [])
    groups.get(kind).push(artifact)
  }
  return [...groups.entries()]
    .map(([kind, items]) => ({ kind, label: labels[kind] || humanizeMetric(kind), items }))
    .sort((left, right) => {
      const leftRank = order.indexOf(left.kind)
      const rightRank = order.indexOf(right.kind)
      return (leftRank === -1 ? order.length : leftRank) - (rightRank === -1 ? order.length : rightRank)
    })
})

const resultReports = computed(() => collectWorkflowReports(displayRun.value ? [displayRun.value] : []))
const primaryResultReport = computed(() => resultReports.value[0] || null)
const resultFigures = computed(() => collectWorkflowFigures(displayRun.value ? [displayRun.value] : []))
const resultFiguresRoute = computed(() => ({
  name: 'PlotStudio',
  params: { id: projectId.value },
  query: {
    view: 'analysis',
    run: displayRun.value?.id || '',
    workflow: workflow.value?.id || '',
  },
}))

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

const METRIC_LABELS = Object.freeze({
  samples: 'Samples',
  mags_recovered: 'MAGs recovered',
  high_quality_mags: 'High-quality MAGs',
  medium_quality_mags: 'Medium-quality MAGs',
  median_completeness: 'Median completeness',
  median_contamination: 'Median contamination',
  genera: 'Genera',
  damage_supported_contigs: 'Damage-supported contigs',
})

// One line of context under each overview number, so a headline figure is
// never read without its basis.
const METRIC_NOTES = Object.freeze({
  samples: 'Paired libraries in this run',
  mags_recovered: 'Bins with a quality assessment',
  high_quality_mags: 'Completeness ≥90%, contamination ≤5%',
  medium_quality_mags: 'Completeness ≥50%, contamination ≤10%',
  median_completeness: 'CheckM2, across all MAGs',
  median_contamination: 'CheckM2, across all MAGs',
  genera: 'Distinct GTDB genera',
})

function humanizeMetric(value) {
  if (METRIC_LABELS[value]) return METRIC_LABELS[value]
  return String(value || 'Result')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function metricNote(metric) {
  if (metric.metric_name === 'damage_supported_contigs' && metric.payload) {
    const { supported, total, qvalue_max: q, accuracy_min: a } = metric.payload
    return `${supported} of ${total} contigs · q ≤ ${q}, accuracy ≥ ${a}`
  }
  return METRIC_NOTES[metric.metric_name] || metric.sample_id || humanizeMetric(metric.metric_group)
}

function metricKey(metric) {
  return [metric.id, metric.metric_group, metric.metric_name, metric.sample_id].filter(Boolean).join(':')
}

function displayMetric(metric) {
  if (metric.metric_value !== null && metric.metric_value !== undefined && metric.metric_value !== '') {
    const numeric = Number(metric.metric_value)
    const value = Number.isFinite(numeric)
      ? (Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(2))
      : String(metric.metric_value)
    return `${value}${metric.unit || ''}`
  }
  return metric.metric_text || 'Recorded'
}

function artifactFileName(artifact) {
  const path = String(artifact?.project_path || artifact?.path || '')
  return path.split('/').pop() || 'Result file'
}

function resetLogState() {
  logText.value = ''
  logOffset.value = 0
  logJobId.value = null
  logEof.value = false
}

async function openArtifactPreview(artifact) {
  if (!artifact?.project_path) return
  if (isReportArtifact(artifact)) {
    await router.push(reportCenterRoute({
      path: artifact.project_path,
      runId: displayRun.value?.id || '',
      workflowId: workflow.value?.id || '',
    }))
    return
  }
  if (isPreviewFigureArtifact(artifact)) {
    await router.push({
      ...resultFiguresRoute.value,
      query: { ...resultFiguresRoute.value.query, figure: artifact.project_path },
    })
    return
  }
  actionError.value = ''
  try {
    const path = artifact.project_path
    const response = await fetch(`/api/filemanager/${projectId.value}/preview?path=${encodeURIComponent(path)}`)
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'Result preview is unavailable.')
    artifactPreviewName.value = artifactFileName(artifact)
    artifactPreviewPath.value = path
    artifactPreviewData.value = { ...payload, editable: false }
    artifactPreviewOpen.value = true
  } catch (error) {
    showActionError(error)
  }
}

function reportCenterRoute(report) {
  return {
    name: 'ReportCenter',
    params: { id: projectId.value },
    query: {
      path: report?.path || report?.project_path || '',
      run: report?.runId || displayRun.value?.id || '',
      workflow: report?.workflowId || workflow.value?.id || '',
    },
  }
}

function plotArtifact(artifact) {
  if (!artifact?.project_path) return
  router.push({
    name: 'PlotStudio',
    params: { id: projectId.value },
    query: {
      view: 'create',
      source: artifact.project_path,
      run: displayRun.value?.id || '',
      workflow: workflow.value?.id || '',
    },
  })
}

function artifactOpenTitle(artifact) {
  if (isReportArtifact(artifact)) return 'Open interactive report'
  if (isPreviewFigureArtifact(artifact)) return 'Open analysis figure'
  return 'Preview result'
}

function artifactOpenIcon(artifact) {
  if (isReportArtifact(artifact)) return 'clipboard-list'
  if (isPreviewFigureArtifact(artifact)) return 'maximize-2'
  return 'eye'
}

function closeArtifactPreview() {
  artifactPreviewOpen.value = false
  artifactPreviewName.value = ''
  artifactPreviewPath.value = ''
  artifactPreviewData.value = {}
}

function downloadProjectPath(path) {
  if (!path) return
  const anchor = document.createElement('a')
  anchor.href = `/api/filemanager/${projectId.value}/download?path=${encodeURIComponent(path)}`
  anchor.download = String(path).split('/').pop() || 'result'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

function downloadArtifact(artifact) {
  downloadProjectPath(artifact?.project_path)
}

function downloadPreviewArtifact(payload) {
  downloadProjectPath(payload?.filePath || artifactPreviewPath.value)
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
    skipped: 'Skipped',
    interrupted: 'Interrupted',
    not_found: 'Ready',
    blocked: 'Project Busy',
  }
  return mapping[status] || 'Ready'
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
  const preservedInputs = {}
  for (const name of ['sample_manifest', 'raw_data_dir', 'sample_table', 'fasta_path']) {
    if (formValues.value[name]) preservedInputs[name] = formValues.value[name]
  }
  activePresetId.value = preset.id
  formValues.value = {
    ...initWorkflowFormValues(workflowTool.value?.parameters || []),
    ...preservedInputs,
    ...preset.values,
  }
  applyWorkflowDefaults()
  runDialogDryRun.value = Boolean(preset.values.dry_run)
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

async function inspectHistoryRun(run) {
  displayRun.value = run
  activeTab.value = 'logs'
  await fetchDisplayRunDetail(run.id)
  fetchLogsForRun(displayRun.value, { reset: true })
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
    `/api/pipeline/${projectId.value}/workflow-runs?workflow_id=${encodeURIComponent(workflow.value.id)}&limit=20&include_results=false`,
  )
  const payload = await response.json()
  if (!response.ok) return
  const cachedDetails = new Map(
    workflowRuns.value
      .filter((run) => Object.prototype.hasOwnProperty.call(run, 'artifacts'))
      .map((run) => [run.id, run])
  )
  workflowRuns.value = (payload.workflow_runs || []).map((summary) => {
    const cached = cachedDetails.get(summary.id)
    if (!cached) return summary
    return {
      ...cached,
      ...summary,
      artifacts: cached.artifacts,
      metrics: cached.metrics,
      events: cached.events,
    }
  })
}

async function fetchDisplayRunDetail(runId = '') {
  const targetId = String(
    runId
    || route.query.run
    || currentProjectTask.value.workflow_run_id
    || displayRun.value?.id
    || workflowRuns.value[0]?.id
    || ''
  )
  if (!targetId) return null
  const cached = workflowRuns.value.find((run) => run.id === targetId)
  const isActive = ['queued', 'starting', 'running'].includes(cached?.status)
  if (cached && !isActive && Object.prototype.hasOwnProperty.call(cached, 'artifacts')) {
    displayRun.value = cached
    return cached
  }
  const response = await fetch(`/api/pipeline/${projectId.value}/workflow-runs/${encodeURIComponent(targetId)}`)
  if (!response.ok) return null
  const detail = await response.json()
  const index = workflowRuns.value.findIndex((run) => run.id === detail.id)
  if (index >= 0) {
    workflowRuns.value[index] = detail
  } else {
    workflowRuns.value.unshift(detail)
  }
  displayRun.value = detail
  return detail
}

async function fetchLogsForRun(run, { reset = false } = {}) {
  const jobId = run?.job_id
  if (!jobId) {
    resetLogState()
    return
  }
  const jobChanged = logJobId.value !== jobId
  if (jobChanged || reset) {
    logText.value = ''
    logOffset.value = 0
    logEof.value = false
    logJobId.value = jobId
  }
  const terminal = !['queued', 'starting', 'running'].includes(run?.status)
  if (!reset && !jobChanged && terminal && logEof.value) return

  const query = jobChanged || reset
    ? 'tail=262144&limit=262144'
    : `offset=${logOffset.value}&limit=65536`
  const response = await fetch(`/api/jobs/${jobId}/logs?${query}`)
  const payload = await response.json()
  if (!response.ok) return
  if (payload.reset || jobChanged || reset) {
    logText.value = payload.content || ''
  } else if (payload.content) {
    logText.value += payload.content
  }
  if (logText.value.length > 524288) {
    logText.value = logText.value.slice(-524288)
  }
  logOffset.value = Number(payload.offset) || 0
  logEof.value = Boolean(payload.eof)
}

function syncDisplayRun() {
  if (!workflowTool.value) {
    displayRun.value = null
    return
  }
  if (route.query.run) {
    const selected = workflowRuns.value.find((run) => run.id === route.query.run)
    if (selected) {
      displayRun.value = selected
      return
    }
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
  if (refreshingState.value) return
  refreshingState.value = true
  try {
    if (!workflowTool.value) {
      await Promise.all([fetchProject(), fetchWorkflowTool()])
    }
    await fetchCurrentTask()
    await fetchWorkflowRuns()
    syncDisplayRun()
    await fetchDisplayRunDetail()
    await fetchLogsForRun(displayRun.value)
  } finally {
    refreshingState.value = false
  }
}

function showActionError(error) {
  const described = describeWorkflowError(error)
  actionError.value = described.message
  actionErrorHint.value = described.hint
  actionErrorDetails.value = described.details
}

watch(actionError, (value) => {
  if (!value) {
    actionErrorHint.value = ''
    actionErrorDetails.value = ''
  }
}, { flush: 'sync' })

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
  const count = readySampleCount(scan)
  if (count < 1) {
    const current = String(inputDataDir.value || '').trim()
    inputDataDir.value = current && current !== '.' ? current : defaultInputDir.value
    manifestScan.value = scan
    const label = workflow.value.id === 'appam-paleoproteomics' ? 'RAW/.d files' : 'complete FASTQ pairs'
    throw new Error(`No ${label} found in ${inputDataDir.value}`)
  }
  inputDataDir.value = inferredRoot || scan.root || inputDataDir.value || defaultInputDir.value
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

async function refreshDetectedInputs() {
  const scan = await scanBestInputDir()
  const inferredRoot = inferInputRootFromScan(scan)
  const nextScan = inferredRoot && inferredRoot !== scan.root
    ? await scanInputData(inferredRoot)
    : scan
  const count = readySampleCount(nextScan)
  if (count) {
    inputDataDir.value = inferredRoot || scan.root || inputDataDir.value || defaultInputDir.value
  } else {
    const current = String(inputDataDir.value || '').trim()
    inputDataDir.value = current && current !== '.' ? current : defaultInputDir.value
  }
  manifestScan.value = nextScan
  manifestStatus.value = count
    ? `${count} sample${count === 1 ? '' : 's'} detected`
    : defaultInputStatus.value
  return manifestScan.value
}

async function handleRescanInputs() {
  actionError.value = ''
  loadingState.value = true
  try {
    await refreshDetectedInputs()
  } catch (error) {
    showActionError(error)
  } finally {
    loadingState.value = false
  }
}

async function handleQuickUploadComplete() {
  await handleRescanInputs()
}

function handleQuickUploadError(payload) {
  const error = payload?.error
  showActionError(error || new Error('One or more files could not be uploaded.'))
}

async function handleOneClickRun() {
  actionError.value = ''
  loadingState.value = true
  try {
    await prepareInputTable({ overwrite: true })
    await runWorkflow(false)
    activeTab.value = 'logs'
  } catch (error) {
    showActionError(error)
  } finally {
    loadingState.value = false
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
  const response = await fetch(`/api/pipeline/${projectId.value}/run/${workflowTool.value.id}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const result = await response.json()
  if (!response.ok) {
    const firstError = (result.preflight?.checks || []).find((check) => check.status === 'error')
    const details = Array.isArray(result.details) ? result.details[0] : ''
    throw new Error(firstError?.message || details || result.error || 'Failed to start analysis')
  }
  showRunDialog.value = false
  await refreshAll()
  scheduleRefresh(4000)
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

async function handleRun(forceDryRun) {
  if (loadingState.value) return
  actionError.value = ''
  loadingState.value = true
  try {
    await runWorkflow(forceDryRun)
  } catch (error) {
    showActionError(error)
  } finally {
    loadingState.value = false
  }
}

function closeMoreMenu(event) {
  event.currentTarget.closest('details')?.removeAttribute('open')
}

function openRunDialog() {
  actionError.value = ''
  runDialogDryRun.value = false
  showAdvancedParams.value = false
  activePresetId.value = 'recommended'
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
    resetLogState()
    activePresetId.value = ''
    showAdvancedParams.value = false
    manifestStatus.value = ''
    manifestScan.value = null
    inputDataDir.value = ''
    inputValidation.value = null
    actionError.value = ''
    activeTab.value = ['logs', 'history', 'results'].includes(route.query.tab) ? route.query.tab : 'history'
    await refreshAll()
    if (hasInputSetup.value && !activeWorkflowRun.value) {
      await refreshDetectedInputs().catch(() => {})
    }
    if (!route.query.tab) {
      if (displayRun.value?.status === 'completed') activeTab.value = 'results'
      else if (['queued', 'starting', 'running'].includes(displayRun.value?.status)) activeTab.value = 'logs'
    }
  },
  { immediate: true },
)

watch(
  () => [route.query.tab, route.query.run],
  () => {
    if (['logs', 'history', 'results'].includes(route.query.tab)) {
      activeTab.value = route.query.tab
    }
    syncDisplayRun()
    fetchDisplayRunDetail().then(() => {
      if (activeTab.value === 'logs') {
        fetchLogsForRun(displayRun.value, { reset: true })
      }
    })
  },
)

onMounted(() => {
  scheduleRefresh(12000)
})

onUnmounted(() => {
  disposed = true
  if (refreshTimer) {
    window.clearTimeout(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
.workflow-view {
  height: 100%;
  background: var(--surface-0);
  color: var(--gray-900);
  overflow-y: auto;
}

.workflow-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 20px;
  padding: 18px 24px 16px;
  border-bottom: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.workflow-kicker {
  display: inline-flex;
  align-items: center;
  color: var(--gray-500);
  font-size: 11px;
  font-weight: var(--font-medium);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.workflow-hero h1 {
  margin: 4px 0 5px;
  font-size: 24px;
  line-height: 1.2;
  letter-spacing: 0;
}

.workflow-hero p {
  max-width: 720px;
  margin: 0;
  color: var(--gray-500);
  font-size: var(--text-sm);
  line-height: 1.5;
}

.workflow-hero-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}

.hero-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  border: 1px solid var(--border-color-light);
  font-size: var(--text-xs);
  color: var(--gray-600);
}

.hero-pill.subtle {
  background: rgba(255, 255, 255, 0.7);
  color: #475569;
}

.workflow-hero-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-shrink: 0;
  gap: 8px;
}

.hero-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  border: 1px solid var(--border-color-light);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--gray-600);
}

.hero-status.running,
.status-value.running {
  color: #975a16;
}

.hero-status.starting,
.status-value.starting {
  color: var(--accent-700);
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
  min-height: var(--control-height);
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-base);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
}

.hero-btn:hover:not(:disabled) {
  filter: brightness(0.97);
}

.hero-btn:disabled {
  opacity: 1;
  background: var(--gray-200);
  border-color: var(--gray-200);
  color: var(--gray-400);
  cursor: not-allowed;
}

.hero-btn.primary {
  background: var(--primary-600);
  color: #fff;
}

.hero-btn.primary:hover:not(:disabled) {
  background: var(--primary-700);
  filter: none;
}

.hero-btn.secondary {
  background: var(--surface-1);
  color: var(--gray-900);
  border: 1px solid var(--border-color);
}

.hero-btn.subtle {
  background: transparent;
  color: var(--gray-600);
  border-color: var(--border-color-light);
}

.hero-btn.icon-only {
  min-width: 38px;
  padding: 0 12px;
  font-size: 1.1rem;
  line-height: 1;
}

.hero-btn.danger {
  background: var(--error-50);
  color: var(--error-600);
  border-color: rgba(170, 57, 57, 0.2);
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
  background: var(--accent-50);
  color: var(--accent-700);
}

.workflow-more-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 20;
  min-width: 180px;
  padding: 6px;
  display: grid;
  gap: 6px;
  border-radius: var(--radius-md);
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-md);
}

.more-menu-item {
  min-height: 34px;
  padding: 0 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--gray-700);
  font-weight: var(--font-medium);
  text-align: left;
  cursor: pointer;
}

.more-menu-item:hover:not(:disabled) {
  background: var(--accent-50);
}

.more-menu-item:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.workflow-banner {
  margin: 14px 24px 0;
  padding: 13px 15px;
  border-radius: var(--radius-base);
  font-weight: var(--font-medium);
}

.workflow-banner.error {
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.16);
  color: #b91c1c;
}

.workflow-banner-copy {
  display: grid;
  gap: 3px;
}

.workflow-banner-copy span {
  font-size: var(--text-sm);
  font-weight: 500;
}

.error-details {
  margin-top: 9px;
  border-top: 1px solid rgba(220, 38, 38, 0.14);
}

.error-details summary {
  width: fit-content;
  padding-top: 8px;
  font-size: var(--text-xs);
  cursor: pointer;
}

.error-details pre {
  max-height: 180px;
  margin: 8px 0 0;
  padding: 10px;
  overflow: auto;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  color: #7f1d1d;
  font-family: var(--font-family-mono);
  font-size: var(--text-xs);
  font-weight: 500;
  line-height: 1.45;
  white-space: pre-wrap;
}

.workflow-banner.warning {
  background: rgba(124, 58, 237, 0.08);
  border: 1px solid rgba(124, 58, 237, 0.14);
  color: #6d28d9;
}

.workflow-input-card,
.workflow-activity-card {
  background: var(--surface-1);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
  box-shadow: none;
}

.workflow-input-card {
  margin: 14px 24px 0;
  overflow: hidden;
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
  color: var(--gray-500);
  font-size: var(--text-sm);
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
  grid-template-columns: minmax(180px, 320px) auto;
  align-items: center;
  gap: 10px;
  padding: 0 18px 14px;
}

.sample-review {
  margin: 0 18px 16px;
  border-top: 1px solid var(--border-color);
}

.quick-upload {
  margin: 0 18px 16px;
}

.quick-upload > p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: var(--text-xs);
}

.quick-upload a {
  margin-left: 5px;
  color: var(--accent-700);
  font-weight: 700;
  text-decoration: none;
}

.sample-review summary {
  width: fit-content;
  padding: 12px 0;
  color: #475569;
  font-size: var(--text-sm);
  font-weight: 700;
  cursor: pointer;
}

.sample-review .sample-table-wrap {
  margin: 0 0 2px;
}

.input-setup-row.reference-row {
  padding-top: 0;
}

.file-picker-btn.compact {
  min-height: 36px;
  border-radius: var(--radius-base);
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
  background: var(--surface-3);
  color: #475569;
  font-size: var(--text-xs);
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

.sample-table-wrap {
  max-height: 260px;
  margin: 0 18px 18px;
  overflow: auto;
  border-radius: var(--radius-base);
  border: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.sample-table {
  width: 100%;
  min-width: 640px;
  border-collapse: collapse;
}

.sample-table th,
.sample-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-color-light);
  text-align: left;
  font-size: var(--text-sm);
  vertical-align: top;
}

.sample-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--surface-2);
  color: var(--gray-600);
  font-size: var(--text-xs);
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

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}

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
  font-size: var(--text-sm);
}

.field-tag {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: var(--surface-3);
  color: #64748b;
  font-size: var(--text-xs);
  font-weight: 700;
}

.field-help {
  margin: 0;
  color: #64748b;
  font-size: var(--text-xs);
  line-height: 1.45;
}

.compact-input,
.file-picker-btn {
  width: 100%;
  min-height: var(--control-height);
  border-radius: var(--radius-base);
  border: 1px solid var(--border-color);
  background: var(--surface-1);
  padding: 0 11px;
  font-size: var(--text-sm);
  color: var(--gray-900);
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








.run-dialog-body {
  display: grid;
  gap: var(--spacing-5);
}

.dialog-field {
  padding: 0 0 14px;
  border-bottom: 1px solid var(--border-color-light);
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
  border-radius: var(--radius-base);
  border: 1px solid var(--border-color);
  background: var(--surface-1);
  color: var(--gray-600);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
}

.preset-btn.active {
  background: var(--accent-50);
  border-color: var(--accent-200);
  color: var(--accent-700);
}

.advanced-toggle {
  width: 100%;
  min-height: 40px;
  background: var(--surface-2);
}

.run-mode-toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 0 14px;
  border-radius: var(--radius-base);
  background: var(--primary-50);
  border: 1px solid var(--primary-100);
  font-weight: 600;
  color: #1e3a8a;
}

.run-technical-options {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--surface-2);
}

.run-technical-options > summary {
  padding: 11px 13px;
  color: #64748b;
  font-size: var(--text-sm);
  font-weight: 700;
  cursor: pointer;
}

.run-technical-options .run-mode-toggle {
  margin: 0 10px 10px;
  border-radius: 8px;
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
  gap: 2px;
  padding: 3px;
  border-radius: var(--radius-base);
  background: var(--surface-2);
}

.tab-buttons button {
  min-height: 34px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  border: 0;
  background: transparent;
  color: #64748b;
  font-weight: 700;
  cursor: pointer;
}

.tab-buttons button.active {
  background: var(--surface-1);
  color: var(--primary-700);
  box-shadow: var(--shadow-xs);
}

.activity-meta {
  padding-top: 2px;
  color: #64748b;
  font-size: var(--text-sm);
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
  border-radius: var(--radius-base);
  background: #0f172a;
  color: #dbe4f0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  box-shadow: inset 0 0 0 1px var(--border-color-dark);
}

.log-row {
  display: grid;
  grid-template-columns: 40px 1fr;
  gap: 12px;
  line-height: 1.5;
  font-size: var(--text-sm);
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
  border-radius: var(--radius-base);
  background: var(--surface-1);
  border: 1px solid var(--border-color-light);
  cursor: pointer;
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.history-card:hover {
  border-color: var(--border-color-dark);
  background: var(--surface-2);
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
  font-size: var(--text-sm);
}

.result-panel {
  display: grid;
  gap: 22px;
}

.result-destinations {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px 14px;
  border: 1px solid var(--accent-200);
  border-radius: 6px;
  background: rgba(239, 246, 255, 0.72);
}

.result-destinations__copy,
.result-destinations__copy > span:last-child {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.result-destinations__copy > span:last-child {
  display: grid;
  gap: 2px;
}

.result-destinations__icon {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  place-items: center;
  border-radius: 6px;
  background: #ffffff;
  color: var(--primary-700);
}

.result-destinations__copy strong {
  color: var(--gray-900);
  font-size: var(--text-sm);
}

.result-destinations__copy small {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.result-destinations__actions {
  display: flex;
  flex-shrink: 0;
  gap: 7px;
}

.result-destinations__actions a {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  gap: 7px;
  padding: 0 11px;
  border: 1px solid var(--accent-200);
  border-radius: 6px;
  background: #ffffff;
  color: var(--primary-700);
  font-size: var(--text-xs);
  font-weight: 650;
}

.result-destinations__actions a:hover {
  border-color: var(--primary-400);
  background: var(--primary-50);
}

.result-metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.result-metric {
  min-width: 0;
  min-height: 92px;
  display: grid;
  align-content: start;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: #fff;
}

.result-metric span,
.result-metric small {
  overflow-wrap: anywhere;
  color: #64748b;
  font-size: var(--text-xs);
}

.result-metric strong {
  overflow-wrap: anywhere;
  color: #172033;
  font-size: 1.08rem;
}

.artifact-group {
  min-width: 0;
}

.artifact-group > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.artifact-group h4 {
  margin: 0;
  color: #172033;
  font-size: var(--text-sm);
}

.artifact-group > header span {
  color: #64748b;
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
}

.artifact-list {
  border-top: 1px solid var(--border-color);
}

.artifact-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(76px, auto);
  align-items: center;
  gap: 14px;
  min-height: 58px;
  padding: 9px 4px;
  border-bottom: 1px solid var(--border-color);
}

.artifact-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.artifact-copy strong {
  overflow-wrap: anywhere;
  color: #1e293b;
  font-size: var(--text-sm);
}

.artifact-copy span {
  min-width: 0;
  overflow: hidden;
  color: #64748b;
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.artifact-size {
  color: #64748b;
  font-size: var(--text-xs);
  white-space: nowrap;
}

.artifact-actions {
  display: flex;
  justify-content: flex-end;
  gap: 5px;
}

.artifact-actions button {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-color);
  border-radius: 5px;
  background: #fff;
  color: #475569;
  cursor: pointer;
}

.artifact-actions button:hover:not(:disabled) {
  border-color: var(--accent-500);
  color: var(--accent-700);
}

.artifact-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

@media (max-width: 820px) {
  .result-metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 520px) {
  .result-metric-grid {
    grid-template-columns: 1fr;
  }

  .artifact-row {
    grid-template-columns: minmax(0, 1fr) 70px;
  }

  .artifact-size {
    display: none;
  }

  .result-destinations {
    align-items: stretch;
    flex-direction: column;
  }

  .result-destinations__actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .result-destinations__actions a {
    justify-content: center;
  }
}

.history-state {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: var(--text-xs);
  font-weight: 700;
  background: var(--surface-3);
}

.history-state.starting { background: var(--accent-50); color: var(--accent-700); }
.history-state.running { background: var(--accent-50); color: var(--accent-700); }
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
  font-size: var(--text-sm);
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
  .workflow-activity-card {
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
}
</style>
