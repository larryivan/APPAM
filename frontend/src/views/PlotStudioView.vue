<template>
  <div class="plot-studio">
    <div class="plot-studio__inner">
      <PageHeader eyebrow="Project" title="Plots" description="Analysis figures and custom visualizations">
        <template #meta>
          <span v-if="activeView === 'create'">{{ sourceMeta }}</span>
          <span v-else>{{ workflowFigures.length }} analysis · {{ customFigures.length }} custom</span>
        </template>
      </PageHeader>

      <nav class="plot-tabs" aria-label="Plot views">
        <router-link :to="viewRoute('analysis')" :class="{ active: activeView === 'analysis' }">
          <Icon name="images" :size="16" />
          <span>Analysis figures</span>
        </router-link>
        <router-link :to="viewRoute('create')" :class="{ active: activeView === 'create' }">
          <Icon name="chart-no-axes-combined" :size="16" />
          <span>Create your own</span>
        </router-link>
      </nav>

      <div v-if="contextRunId" class="plot-run-context">
        <span>
          <Icon name="activity" :size="15" />
          From {{ contextWorkflowLabel }} · run {{ shortRunId(contextRunId) }}
        </span>
        <router-link :to="resultContextRoute">Back to results</router-link>
      </div>

      <div v-if="activeView === 'create'" class="plot-builder">
        <div class="builder-controls">
          <section class="builder-section" :class="{ complete: sourceReady }">
            <header class="builder-section__header">
              <span class="step-number">1</span>
              <div>
                <h2>Choose data</h2>
                <p>CSV or tab-separated table</p>
              </div>
              <Icon v-if="sourceReady" name="circle-check" :size="18" class="step-check" />
            </header>

            <button v-if="!sourcePath" type="button" class="source-picker" @click="showFilePicker = true">
              <Icon name="file-spreadsheet" :size="21" />
              <span>
                <strong>Select a project table</strong>
                <small>CSV, TSV, TAB or TXT</small>
              </span>
              <Icon name="chevron-right" :size="16" />
            </button>

            <div v-else class="source-selected">
              <span class="source-icon"><Icon name="table" :size="19" /></span>
              <span class="source-copy">
                <strong :title="sourcePath">{{ sourceFileName }}</strong>
                <small v-if="sourceLoading">Reading table...</small>
                <small v-else>{{ sourceDetail }}</small>
              </span>
              <button type="button" title="Choose another table" aria-label="Choose another table" @click="showFilePicker = true">
                <Icon name="folder-open" :size="17" />
              </button>
            </div>

            <div v-if="sourceError" class="inline-state error" role="alert">
              <Icon name="triangle-alert" :size="16" />
              <span>{{ sourceError }}</span>
              <button v-if="sourcePath" type="button" @click="loadSource(sourcePath)">Retry</button>
            </div>
          </section>

          <section class="builder-section" :class="{ complete: Boolean(chartType) }">
            <header class="builder-section__header">
              <span class="step-number">2</span>
              <div>
                <h2>Choose the question</h2>
                <p>The chart follows your analytical goal</p>
              </div>
              <Icon v-if="chartType" name="circle-check" :size="18" class="step-check" />
            </header>

            <div class="plot-purpose-grid" role="radiogroup" aria-label="Chart purpose">
              <label
                v-for="option in plotTypes"
                :key="option.id"
                class="plot-purpose"
                :class="{ active: chartType === option.id }"
              >
                <input v-model="chartType" type="radio" name="plot-type" :value="option.id">
                <Icon :name="option.icon" :size="19" />
                <span>
                  <strong>{{ option.label }}</strong>
                  <small>{{ option.detail }}</small>
                </span>
                <Icon v-if="chartType === option.id" name="check" :size="15" class="purpose-check" />
              </label>
            </div>
          </section>

          <section class="builder-section" :class="{ complete: columnsReady }">
            <header class="builder-section__header">
              <span class="step-number">3</span>
              <div>
                <h2>Map columns</h2>
                <p>Numeric columns are detected automatically</p>
              </div>
              <Icon v-if="columnsReady" name="circle-check" :size="18" class="step-check" />
            </header>

            <div class="column-grid">
              <label>
                <span>{{ chartType === 'pie' ? 'Category' : 'Horizontal axis' }}</span>
                <select v-model="xColumn" :disabled="!sourceReady">
                  <option value="" disabled>Select a column</option>
                  <option v-for="field in xColumnOptions" :key="field" :value="field">{{ field }}</option>
                </select>
              </label>
              <label>
                <span>{{ chartType === 'pie' ? 'Value' : 'Vertical axis' }}</span>
                <select v-model="yColumn" :disabled="!sourceReady">
                  <option value="" disabled>Select a numeric column</option>
                  <option v-for="field in numericColumns" :key="field" :value="field">{{ field }}</option>
                </select>
              </label>
              <label v-if="chartType !== 'pie'" class="group-field">
                <span>Color by <small>Optional</small></span>
                <select v-model="groupColumn" :disabled="!sourceReady">
                  <option value="">Single series</option>
                  <option v-for="field in groupColumnOptions" :key="field" :value="field">{{ field }}</option>
                </select>
              </label>
            </div>
            <p v-if="groupCount > 12" class="field-warning">
              The first 12 groups are shown. Choose a column with fewer categories for a clearer figure.
            </p>
          </section>

          <section class="builder-section finish-section" :class="{ complete: chartReady }">
            <header class="builder-section__header">
              <span class="step-number">4</span>
              <div>
                <h2>Name the figure</h2>
                <p>Stored with its source and column mapping</p>
              </div>
              <Icon v-if="chartReady" name="circle-check" :size="18" class="step-check" />
            </header>
            <label class="title-field">
              <span>Figure title</span>
              <input
                v-model="figureTitle"
                type="text"
                maxlength="120"
                placeholder="Figure title"
                :disabled="!sourceReady"
                @input="titleTouched = true"
              >
            </label>
          </section>
        </div>

        <aside class="plot-preview" aria-label="Plot preview">
          <header class="preview-header">
            <div>
              <span>Preview</span>
              <strong>{{ chartReady ? activePlotLabel : 'Waiting for data' }}</strong>
            </div>
            <span v-if="chartReady" class="preview-status"><Icon name="circle-check" :size="14" /> Ready</span>
          </header>

          <div class="preview-stage" :aria-busy="sourceLoading">
            <div v-if="sourceLoading" class="preview-empty">
              <Icon name="rotate-ccw" :size="24" spin />
              <strong>Reading table</strong>
            </div>
            <div v-else-if="!chartReady" class="preview-empty">
              <Icon name="chart-no-axes-combined" :size="28" />
              <strong>{{ previewEmptyTitle }}</strong>
              <span>{{ previewEmptyDetail }}</span>
            </div>
            <div v-show="chartReady && !sourceLoading" ref="chartCanvas" class="chart-canvas"></div>
          </div>

          <footer class="preview-actions">
            <div class="save-feedback" aria-live="polite">
              <template v-if="saveMessage">
                <Icon name="circle-check" :size="15" />
                <button type="button" @click="openGallery">{{ saveMessage }}</button>
              </template>
              <template v-else-if="saveError">
                <Icon name="triangle-alert" :size="15" />
                <span>{{ saveError }}</span>
              </template>
              <template v-else-if="!canSave">
                <Icon name="eye" :size="15" />
                <span>View-only project</span>
              </template>
            </div>
            <button type="button" class="secondary-action" :disabled="!chartReady" @click="downloadPlot">
              <Icon name="download" :size="16" />
              <span>Download PNG</span>
            </button>
            <button
              type="button"
              class="primary-action"
              :disabled="!chartReady || saving || !canSave"
              :title="canSave ? 'Save figure and reproducibility record' : 'Editor access required'"
              @click="savePlot"
            >
              <Icon :name="saving ? 'rotate-ccw' : 'save'" :size="16" :spin="saving" />
              <span>{{ saving ? 'Saving' : 'Save to project' }}</span>
            </button>
          </footer>
        </aside>
      </div>

      <section v-else class="analysis-figures">
        <header class="gallery-toolbar">
          <div>
            <strong>{{ scopedRunId ? 'Run figures' : 'Analysis figures' }}</strong>
            <span>{{ scopedRunId ? `Run ${shortRunId(scopedRunId)}` : 'Generated by project analyses' }}</span>
          </div>
          <div class="gallery-toolbar-actions">
            <button v-if="scopedRunId" type="button" class="clear-scope" @click="clearRunScope">All figures</button>
            <button type="button" title="Refresh figures" aria-label="Refresh figures" :disabled="galleryLoading" @click="loadGallery(true)">
              <Icon name="rotate-ccw" :size="17" :spin="galleryLoading" />
            </button>
          </div>
        </header>

        <div v-if="galleryLoading" class="gallery-grid" aria-label="Loading figures">
          <div v-for="index in 6" :key="index" class="figure-skeleton"></div>
        </div>

        <div v-else-if="galleryError" class="gallery-state" role="alert">
          <Icon name="triangle-alert" :size="23" />
          <strong>Figures could not be loaded</strong>
          <button type="button" @click="loadGallery(true)">Try again</button>
        </div>

        <template v-else>
          <section v-if="showExampleFigure" class="example-output" aria-label="Example analysis figure">
            <div class="example-output__copy">
              <span class="example-label">Example output</span>
              <h2>MAG quality overview</h2>
              <p>Completeness and contamination place recovered genomes into high, medium and low quality groups.</p>
              <div class="example-legend" aria-label="Example quality groups">
                <span><i class="hq"></i>High quality</span>
                <span><i class="mq"></i>Medium quality</span>
                <span><i class="lq"></i>Low quality</span>
              </div>
              <router-link :to="viewRoute('create')">
                <Icon name="chart-no-axes-combined" :size="16" />
                Create your own
              </router-link>
            </div>
            <div class="example-output__figure">
              <div
                ref="exampleCanvas"
                class="example-chart"
                role="img"
                aria-label="Example scatter plot of MAG completeness and contamination"
              ></div>
              <span>Example data</span>
            </div>
          </section>

          <section v-for="section in figureSections" :key="section.id" class="figure-section">
            <header class="figure-section__header">
              <span class="figure-section__icon"><Icon :name="section.icon" :size="18" /></span>
              <div>
                <h2>{{ section.label }}</h2>
                <span>{{ section.figures.length }} {{ section.figures.length === 1 ? 'figure' : 'figures' }}</span>
              </div>
              <router-link v-if="section.id === 'custom'" :to="viewRoute('create')">Create new</router-link>
            </header>

            <div class="gallery-grid">
              <article v-for="figure in section.figures" :key="figure.id" class="figure-card">
                <button
                  v-if="figure.previewPath"
                  type="button"
                  class="figure-preview"
                  :aria-label="`Open ${figure.title}`"
                  @click="openFigure(figure)"
                >
                  <img :src="imageUrl(figure.previewPath)" :alt="figure.title" loading="lazy">
                </button>
                <div v-else class="figure-preview figure-placeholder">
                  <Icon name="file-text" :size="28" />
                  <span>{{ figureFormatLabel(figure) }}</span>
                </div>
                <div class="figure-info">
                  <div class="figure-title-line">
                    <strong :title="figure.title">{{ figure.title }}</strong>
                    <span>{{ figure.sampleId || figure.source }}</span>
                  </div>
                  <div class="figure-meta">
                    <span>{{ figure.workflowId ? workflowLabel(figure.workflowId) : 'Custom plot' }}</span>
                    <span>{{ formatDate(figure.createdAt) }}</span>
                  </div>
                  <div class="figure-actions">
                    <button
                      v-if="figure.previewPath"
                      type="button"
                      title="Open figure"
                      aria-label="Open figure"
                      @click="openFigure(figure)"
                    >
                      <Icon name="maximize-2" :size="15" />
                    </button>
                    <a
                      :href="downloadUrl(preferredDownload(figure))"
                      title="Download figure"
                      aria-label="Download figure"
                    >
                      <Icon name="download" :size="15" />
                    </a>
                  </div>
                </div>
              </article>
            </div>
          </section>

          <div v-if="scopedRunId && !workflowFigures.length" class="gallery-state compact">
            <strong>No figures for this run</strong>
            <button type="button" @click="clearRunScope">Show all figures</button>
          </div>
        </template>
      </section>
    </div>

    <FilePicker
      v-if="showFilePicker"
      :project-id="projectId"
      :extensions="tableExtensions"
      :model-value="sourcePath"
      @update:model-value="loadSource"
      @close="showFilePicker = false"
    />

    <Teleport to="body">
      <div
        v-if="selectedFigure"
        class="figure-viewer app-modal-viewport app-modal-backdrop"
        role="presentation"
        @click.self="closeFigure"
      >
        <section ref="figurePanel" class="figure-viewer__dialog app-modal" role="dialog" aria-modal="true" :aria-label="selectedFigure.title" tabindex="-1">
          <header class="figure-viewer__header app-modal-header">
            <div>
              <span>{{ selectedFigure.workflowId ? workflowLabel(selectedFigure.workflowId) : 'Custom plot' }}</span>
              <h3>{{ selectedFigure.title }}</h3>
            </div>
            <button type="button" class="app-modal-close" title="Close" aria-label="Close figure" @click="closeFigure">
              <Icon name="x" :size="17" />
            </button>
          </header>
          <div class="figure-viewer__body app-modal-body">
            <img :src="imageUrl(selectedFigure.previewPath)" :alt="selectedFigure.title">
          </div>
          <footer class="figure-viewer__footer app-modal-footer">
            <router-link v-if="selectedFigure.runId" :to="figureResultRoute(selectedFigure)">
              <Icon name="activity" :size="16" />
              <span>Source results</span>
            </router-link>
            <span class="figure-viewer__spacer"></span>
            <a
              v-for="file in selectedFigure.files"
              :key="file.path"
              :href="downloadUrl(file.path)"
              :title="`Download ${file.extension.replace('.', '').toUpperCase()}`"
            >
              <Icon name="download" :size="16" />
              <span>{{ file.extension.replace('.', '').toUpperCase() }}</span>
            </a>
          </footer>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useOverlay } from '@/lib/overlay.js'
import { useRoute, useRouter } from 'vue-router'

import FilePicker from '@/components/FilePicker.vue'
import Icon from '@/components/ui/Icon.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import echarts from '@/lib/echarts.js'
import {
  PLOT_TABLE_EXTENSIONS,
  PLOT_TYPES,
  WORKFLOW_FIGURE_CATEGORIES,
  buildPlotOption,
  collectCustomFigures,
  collectWorkflowFigures,
  parsePlotTable,
  safePlotName,
  sortFigures,
} from '@/lib/plotStudio.js'
import { getWorkflowOption } from '@/lib/workflowUi.js'

const route = useRoute()
const router = useRouter()
const project = inject('appamProject', ref(null))

const projectId = computed(() => String(route.params.id || ''))
const activeView = computed(() => route.query.view === 'create' ? 'create' : 'analysis')
const contextRunId = computed(() => String(route.query.run || ''))
const scopedRunId = computed(() => activeView.value === 'analysis' ? contextRunId.value : '')
const contextWorkflowId = computed(() => String(route.query.workflow || ''))
const contextWorkflowLabel = computed(() => workflowLabel(contextWorkflowId.value))
const plotTypes = PLOT_TYPES
const tableExtensions = PLOT_TABLE_EXTENSIONS
const showFilePicker = ref(false)
const sourcePath = ref('')
const sourceLoading = ref(false)
const sourceError = ref('')
const sourceTruncated = ref(false)
const sourceDigest = ref('')
const fields = ref([])
const numericColumns = ref([])
const rows = ref([])
const chartType = ref('bar')
const xColumn = ref('')
const yColumn = ref('')
const groupColumn = ref('')
const figureTitle = ref('')
const titleTouched = ref(false)
const chartCanvas = ref(null)
const exampleCanvas = ref(null)
const saving = ref(false)
const saveMessage = ref('')
const saveError = ref('')
const figures = ref([])
const galleryLoading = ref(false)
const galleryError = ref('')
let chartInstance = null
let chartResizeObserver = null
let exampleChartInstance = null
let exampleResizeObserver = null
let sourceController = null
let galleryController = null
let galleryLoaded = false

const visibleFigures = computed(() => {
  if (!scopedRunId.value) return figures.value
  return figures.value.filter((figure) => figure.runId === scopedRunId.value)
})
const workflowFigures = computed(() => visibleFigures.value.filter((figure) => figure.source === 'Workflow'))
const customFigures = computed(() => visibleFigures.value.filter((figure) => figure.source !== 'Workflow'))
const figureSections = computed(() => {
  const sections = WORKFLOW_FIGURE_CATEGORIES
    .map((category) => ({
      ...category,
      figures: workflowFigures.value.filter((figure) => figure.category === category.id),
    }))
    .filter((section) => section.figures.length)
  if (customFigures.value.length) {
    sections.push({
      id: 'custom',
      label: 'Your plots',
      icon: 'chart-no-axes-combined',
      figures: customFigures.value,
    })
  }
  return sections
})
const showExampleFigure = computed(() => (
  activeView.value === 'analysis'
  && !galleryLoading.value
  && !galleryError.value
  && workflowFigures.value.length === 0
))
const selectedFigure = computed(() => {
  const requested = String(route.query.figure || '')
  if (!requested) return null
  return figures.value.find((figure) => (
    figure.id === requested
    || figure.previewPath === requested
    || figure.files.some((file) => file.path === requested)
  )) || null
})
const resultContextRoute = computed(() => {
  if (!contextWorkflowId.value) {
    return {
      name: 'ReportCenter',
      params: { id: projectId.value },
      query: { run: contextRunId.value },
    }
  }
  return {
    name: 'WorkflowView',
    params: { id: projectId.value, workflowId: contextWorkflowId.value },
    query: { tab: 'results', run: contextRunId.value },
  }
})

const sourceReady = computed(() => rows.value.length > 0 && fields.value.length > 1)
const columnsReady = computed(() => Boolean(
  sourceReady.value
  && xColumn.value
  && yColumn.value
  && numericColumns.value.includes(yColumn.value)
  && (chartType.value !== 'scatter' || numericColumns.value.includes(xColumn.value))
))
const chartReady = computed(() => columnsReady.value && rows.value.length > 0)
const canSave = computed(() => ['editor', 'owner', 'admin'].includes(project.value?.access_role))
const sourceFileName = computed(() => sourcePath.value.split('/').pop() || 'Project table')
const sourceDetail = computed(() => {
  if (!sourceReady.value) return 'No rows loaded'
  const prefix = sourceTruncated.value ? 'First ' : ''
  return `${prefix}${rows.value.length.toLocaleString()} rows · ${fields.value.length} columns`
})
const sourceMeta = computed(() => sourcePath.value ? sourceFileName.value : 'No table selected')
const activePlotLabel = computed(() => PLOT_TYPES.find((option) => option.id === chartType.value)?.detail || 'Plot')
const xColumnOptions = computed(() => chartType.value === 'scatter' ? numericColumns.value : fields.value)
const groupColumnOptions = computed(() => fields.value.filter((field) => field !== xColumn.value && field !== yColumn.value))
const groupCount = computed(() => {
  if (!groupColumn.value) return 0
  return new Set(rows.value.map((row) => String(row[groupColumn.value] ?? 'Missing'))).size
})
const previewEmptyTitle = computed(() => sourcePath.value ? 'Select chart columns' : 'Choose a table to begin')
const previewEmptyDetail = computed(() => (
  sourcePath.value ? 'The preview updates automatically.' : 'Project tables remain unchanged.'
))

function viewRoute(view) {
  const query = { ...route.query, view }
  if (view !== 'analysis') delete query.figure
  return { name: 'PlotStudio', params: { id: projectId.value }, query }
}

function shortRunId(runId) {
  return String(runId || '').slice(0, 8) || 'unknown'
}

function clearRunScope() {
  const query = { ...route.query, view: 'analysis' }
  delete query.run
  delete query.workflow
  delete query.figure
  router.replace({ name: 'PlotStudio', params: { id: projectId.value }, query })
}

function syncSourceQuery(path) {
  if (String(route.query.source || '') === path) return
  router.replace({
    name: 'PlotStudio',
    params: { id: projectId.value },
    query: { ...route.query, view: 'create', source: path },
  })
}

function resetSource() {
  fields.value = []
  numericColumns.value = []
  rows.value = []
  sourceDigest.value = ''
  xColumn.value = ''
  yColumn.value = ''
  groupColumn.value = ''
}

function chooseDefaultColumns() {
  const firstNumeric = numericColumns.value[0] || ''
  const firstCategory = fields.value.find((field) => !numericColumns.value.includes(field)) || fields.value[0] || ''
  xColumn.value = chartType.value === 'scatter' ? firstNumeric : firstCategory
  yColumn.value = numericColumns.value.find((field) => field !== xColumn.value) || firstNumeric
  groupColumn.value = ''
  titleTouched.value = false
  updateAutomaticTitle()
}

function updateAutomaticTitle() {
  if (!titleTouched.value && xColumn.value && yColumn.value) {
    figureTitle.value = `${yColumn.value} by ${xColumn.value}`
  }
}

async function loadSource(path, { syncRoute = true } = {}) {
  if (!path) return
  sourceController?.abort()
  const controller = new AbortController()
  sourceController = controller
  showFilePicker.value = false
  sourcePath.value = path
  if (syncRoute) syncSourceQuery(path)
  sourceLoading.value = true
  sourceError.value = ''
  saveMessage.value = ''
  saveError.value = ''
  resetSource()
  try {
    const response = await fetch(
      `/api/filemanager/${projectId.value}/plot-table?path=${encodeURIComponent(path)}`,
      { signal: controller.signal },
    )
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'The table could not be read.')
    const parsed = parsePlotTable(payload.content || '', path)
    if (controller.signal.aborted || sourcePath.value !== path) return
    fields.value = parsed.fields
    numericColumns.value = parsed.numericColumns
    rows.value = parsed.rows
    sourceTruncated.value = payload.complete !== true
    sourceDigest.value = String(payload.sha256 || '')
    chooseDefaultColumns()
    if (!numericColumns.value.length) {
      sourceError.value = 'No numeric columns were detected. Choose a table containing measurements.'
    }
  } catch (error) {
    if (error?.name === 'AbortError') return
    sourceError.value = error instanceof Error ? error.message : 'The table could not be read.'
  } finally {
    if (sourceController === controller) {
      sourceController = null
      sourceLoading.value = false
    }
  }
}

function normalizeColumnsForType() {
  if (!sourceReady.value) return
  if (chartType.value === 'scatter' && !numericColumns.value.includes(xColumn.value)) {
    xColumn.value = numericColumns.value[0] || ''
  }
  if (!numericColumns.value.includes(yColumn.value) || (chartType.value === 'scatter' && yColumn.value === xColumn.value)) {
    yColumn.value = numericColumns.value.find((field) => field !== xColumn.value) || numericColumns.value[0] || ''
  }
  if (chartType.value === 'pie') groupColumn.value = ''
  updateAutomaticTitle()
}

function initChart() {
  if (!chartCanvas.value || chartInstance) return
  chartInstance = echarts.init(chartCanvas.value, null, { renderer: 'canvas' })
  chartResizeObserver = new ResizeObserver(() => chartInstance?.resize())
  chartResizeObserver.observe(chartCanvas.value)
}

function disposeExampleChart() {
  exampleResizeObserver?.disconnect()
  exampleResizeObserver = null
  exampleChartInstance?.dispose()
  exampleChartInstance = null
}

async function renderExampleChart() {
  if (!showExampleFigure.value) return
  await nextTick()
  if (!exampleCanvas.value) return
  if (!exampleChartInstance) {
    exampleChartInstance = echarts.init(exampleCanvas.value, null, { renderer: 'canvas' })
    exampleResizeObserver = new ResizeObserver(() => exampleChartInstance?.resize())
    exampleResizeObserver.observe(exampleCanvas.value)
  }
  const option = buildPlotOption({
    type: 'scatter',
    title: '',
    xColumn: 'Completeness (%)',
    yColumn: 'Contamination (%)',
    groupColumn: 'Quality',
  }, [
    { 'Completeness (%)': 98.2, 'Contamination (%)': 1.1, Quality: 'High quality' },
    { 'Completeness (%)': 96.4, 'Contamination (%)': 2.6, Quality: 'High quality' },
    { 'Completeness (%)': 93.8, 'Contamination (%)': 3.4, Quality: 'High quality' },
    { 'Completeness (%)': 91.7, 'Contamination (%)': 1.8, Quality: 'High quality' },
    { 'Completeness (%)': 86.3, 'Contamination (%)': 3.2, Quality: 'Medium quality' },
    { 'Completeness (%)': 78.5, 'Contamination (%)': 5.9, Quality: 'Medium quality' },
    { 'Completeness (%)': 72.8, 'Contamination (%)': 4.4, Quality: 'Medium quality' },
    { 'Completeness (%)': 64.2, 'Contamination (%)': 7.1, Quality: 'Medium quality' },
    { 'Completeness (%)': 58.7, 'Contamination (%)': 8.8, Quality: 'Low quality' },
    { 'Completeness (%)': 52.4, 'Contamination (%)': 6.7, Quality: 'Low quality' },
  ])
  option.color = ['#009e73', '#e69f00', '#94a3b8']
  option.title = { show: false }
  option.grid = { top: 24, right: 24, bottom: 64, left: 62, containLabel: true }
  option.xAxis = { ...option.xAxis, min: 48, max: 102 }
  option.yAxis = { ...option.yAxis, min: 0, max: 11 }
  if (option.series[0]) {
    option.series[0].markLine = {
      silent: true,
      symbol: 'none',
      label: { show: false },
      lineStyle: { color: '#94a3b8', type: 'dashed', width: 1 },
      data: [{ xAxis: 90 }, { yAxis: 5 }],
    }
  }
  exampleChartInstance.setOption(option, true)
  exampleChartInstance.resize()
}

async function renderChart() {
  if (activeView.value !== 'create' || !chartReady.value) return
  await nextTick()
  initChart()
  chartInstance?.setOption(buildPlotOption({
    type: chartType.value,
    title: figureTitle.value,
    xColumn: xColumn.value,
    yColumn: yColumn.value,
    groupColumn: groupColumn.value,
  }, rows.value), true)
  chartInstance?.resize()
}

function chartDataUrl() {
  if (!chartInstance || !chartReady.value) return ''
  return chartInstance.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' })
}

function downloadPlot() {
  const url = chartDataUrl()
  if (!url) return
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${safePlotName(figureTitle.value)}.png`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

async function responseError(response, fallback) {
  const payload = await response.json().catch(() => ({}))
  return payload.error || fallback
}

async function savePlot() {
  const dataUrl = chartDataUrl()
  if (!dataUrl || saving.value) return
  saving.value = true
  saveMessage.value = ''
  saveError.value = ''
  const generatedAt = new Date()
  const stamp = generatedAt.toISOString().replace(/[-:.]/g, '').replace('T', '-').replace('Z', '')
  const baseName = `${safePlotName(figureTitle.value)}-${stamp}`
  const imageName = `${baseName}.png`
  const configPath = `/plots/${baseName}.appam-plot.json`
  try {
    const blob = await fetch(dataUrl).then((response) => response.blob())
    const formData = new FormData()
    formData.append('file', blob, imageName)
    formData.append('path', '/plots')
    formData.append('filename', imageName)
    formData.append('chunkNumber', '1')
    formData.append('totalChunks', '1')
    const uploadResponse = await fetch(`/api/filemanager/${projectId.value}/upload-chunk`, {
      method: 'POST',
      body: formData,
    })
    if (!uploadResponse.ok) throw new Error(await responseError(uploadResponse, 'The figure could not be saved.'))

    const configResponse = await fetch(`/api/filemanager/${projectId.value}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: configPath,
        content: JSON.stringify({
          schema: 'appam.plot.v1',
          title: figureTitle.value,
          source_path: sourcePath.value,
          source_sha256: sourceDigest.value || null,
          chart_type: chartType.value,
          columns: { x: xColumn.value, y: yColumn.value, group: groupColumn.value || null },
          row_count: rows.value.length,
          source_complete: !sourceTruncated.value,
          generated_at: generatedAt.toISOString(),
        }, null, 2),
      }),
    })
    if (!configResponse.ok) throw new Error(await responseError(configResponse, 'The figure was saved without its configuration.'))
    saveMessage.value = `Saved in plots/${imageName}`
    galleryLoaded = false
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : 'The figure could not be saved.'
  } finally {
    saving.value = false
  }
}

function openGallery() {
  router.push({ name: 'PlotStudio', params: { id: projectId.value }, query: { view: 'analysis' } })
}

async function loadGallery(force = false) {
  if (galleryLoaded && !force) return
  galleryController?.abort()
  const controller = new AbortController()
  galleryController = controller
  galleryLoading.value = true
  galleryError.value = ''
  try {
    const [runsResponse, customResponse] = await Promise.all([
      fetch(`/api/pipeline/${projectId.value}/workflow-runs?limit=40&include_results=true`, { signal: controller.signal }),
      fetch(`/api/filemanager/${projectId.value}/list?path=${encodeURIComponent('/plots')}`, { signal: controller.signal }),
    ])
    const runsPayload = await runsResponse.json().catch(() => ({}))
    if (!runsResponse.ok) throw new Error(runsPayload.error || 'Figures could not be loaded.')
    const customPayload = customResponse.ok ? await customResponse.json().catch(() => ({})) : { items: [] }
    if (controller.signal.aborted) return
    figures.value = sortFigures([
      ...collectCustomFigures(customPayload.items || []),
      ...collectWorkflowFigures(runsPayload.workflow_runs || []),
    ])
    galleryLoaded = true
  } catch (error) {
    if (error?.name === 'AbortError') return
    galleryError.value = error instanceof Error ? error.message : 'Figures could not be loaded.'
  } finally {
    if (galleryController === controller) {
      galleryController = null
      galleryLoading.value = false
    }
  }
}

function imageUrl(path) {
  return `/api/filemanager/${projectId.value}/image?path=${encodeURIComponent(path)}`
}

function downloadUrl(path) {
  return `/api/filemanager/${projectId.value}/download?path=${encodeURIComponent(path)}`
}

function preferredDownload(figure) {
  return figure.files.find((file) => file.extension === '.pdf')?.path
    || figure.files.find((file) => file.extension === '.png')?.path
    || figure.files[0]?.path
    || figure.previewPath
}

function workflowLabel(workflowId) {
  return getWorkflowOption(workflowId)?.shortLabel || 'Analysis'
}

function figureFormatLabel(figure) {
  const formats = [...new Set((figure.files || []).map((file) => file.extension.replace('.', '').toUpperCase()))]
  return formats.length ? `${formats.join(' / ')} figure` : 'Figure file'
}

function openFigure(figure) {
  if (!figure?.previewPath) return
  router.push({
    name: 'PlotStudio',
    params: { id: projectId.value },
    query: { ...route.query, view: 'analysis', figure: figure.previewPath },
  })
}

function closeFigure() {
  const query = { ...route.query }
  delete query.figure
  router.replace({ name: 'PlotStudio', params: { id: projectId.value }, query })
}

const figurePanel = ref(null)
useOverlay(() => Boolean(selectedFigure.value), { onClose: closeFigure, panelRef: figurePanel })

function figureResultRoute(figure) {
  const workflowId = figure.workflowId || contextWorkflowId.value
  if (!workflowId) {
    return {
      name: 'ReportCenter',
      params: { id: projectId.value },
      query: { run: figure.runId },
    }
  }
  return {
    name: 'WorkflowView',
    params: { id: projectId.value, workflowId },
    query: { tab: 'results', run: figure.runId },
  }
}

function formatDate(value) {
  if (!value) return 'Date unavailable'
  const date = new Date(String(value).replace(' ', 'T'))
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleDateString()
}

watch(chartType, normalizeColumnsForType)
watch([xColumn, yColumn], updateAutomaticTitle)
watch([chartType, xColumn, yColumn, groupColumn, figureTitle, rows], renderChart)
watch(activeView, async (view) => {
  if (view === 'analysis') {
    await loadGallery()
  } else {
    await nextTick()
    initChart()
    renderChart()
  }
}, { immediate: true })
watch(showExampleFigure, (show) => {
  if (show) renderExampleChart()
  else disposeExampleChart()
}, { immediate: true })
watch(
  () => route.query.source,
  (path) => {
    const requestedPath = String(path || '')
    if (requestedPath && requestedPath !== sourcePath.value) loadSource(requestedPath, { syncRoute: false })
  },
  { immediate: true },
)
watch(projectId, () => {
  sourceController?.abort()
  galleryController?.abort()
  sourcePath.value = ''
  resetSource()
  figures.value = []
  galleryLoaded = false
  if (activeView.value === 'analysis') loadGallery(true)
})

onMounted(() => {
  if (activeView.value === 'create') initChart()
})

onBeforeUnmount(() => {
  sourceController?.abort()
  galleryController?.abort()
  chartResizeObserver?.disconnect()
  chartInstance?.dispose()
  chartInstance = null
  disposeExampleChart()
})
</script>

<style scoped>
.plot-studio {
  width: 100%;
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--surface-0);
}

.plot-studio__inner {
  width: min(1440px, 100%);
  min-width: 0;
  margin: 0 auto;
  padding: 20px 24px 36px;
}

.plot-run-context {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-height: 38px;
  margin: -4px 0 16px;
  padding: 7px 10px;
  border: 1px solid var(--primary-100);
  border-radius: 6px;
  background: var(--primary-50);
  color: var(--gray-600);
  font-size: var(--text-xs);
}

.plot-run-context span,
.plot-run-context a {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.plot-run-context a {
  flex-shrink: 0;
  color: var(--primary-700);
  font-weight: var(--font-semibold);
}

.plot-tabs {
  display: flex;
  gap: 22px;
  margin: -4px 0 22px;
  border-bottom: 1px solid var(--border-color-light);
}

.plot-tabs a {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  gap: 7px;
  border-bottom: 2px solid transparent;
  color: var(--gray-500);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
}

.plot-tabs a:hover {
  color: var(--gray-800);
}

.plot-tabs a.active {
  border-bottom-color: var(--primary-600);
  color: var(--primary-700);
}

.plot-builder {
  display: grid;
  grid-template-columns: minmax(330px, 430px) minmax(0, 1fr);
  gap: 26px;
  align-items: start;
}

.builder-controls {
  min-width: 0;
}

.builder-section {
  padding: 0 0 22px;
  margin-bottom: 22px;
  border-bottom: 1px solid var(--border-color-light);
}

.builder-section__header {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  align-items: start;
  gap: 10px;
  margin-bottom: 14px;
}

.step-number {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border: 1px solid var(--border-color);
  border-radius: 50%;
  background: var(--surface-1);
  color: var(--gray-500);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.builder-section.complete .step-number {
  border-color: var(--primary-200);
  background: var(--primary-50);
  color: var(--primary-700);
}

.builder-section__header h2 {
  margin: 1px 0 2px;
  color: var(--gray-900);
  font-size: var(--text-base);
}

.builder-section__header p {
  margin: 0;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.step-check {
  margin-top: 4px;
  color: var(--success-600);
}

.source-picker,
.source-selected {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  width: 100%;
  min-height: 66px;
  align-items: center;
  gap: 11px;
  padding: 11px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--gray-600);
  text-align: left;
}

.source-picker {
  cursor: pointer;
}

.source-picker:hover {
  border-color: var(--primary-300);
  background: var(--primary-50);
  color: var(--primary-700);
}

.source-picker span,
.source-copy {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.source-picker strong,
.source-selected strong {
  overflow: hidden;
  color: var(--gray-800);
  font-size: var(--text-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-picker small,
.source-selected small {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.source-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--primary-600);
}

.source-selected > button,
.gallery-toolbar > button,
.gallery-toolbar-actions > button:not(.clear-scope) {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--gray-600);
  cursor: pointer;
}

.inline-state {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-top: 10px;
  color: var(--gray-600);
  font-size: var(--text-xs);
}

.inline-state.error {
  color: var(--error-600);
}

.inline-state span {
  flex: 1;
}

.inline-state button,
.gallery-state button,
.gallery-state a {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--primary-700);
  font: inherit;
  font-weight: var(--font-semibold);
  text-decoration: none;
  cursor: pointer;
}

.plot-purpose-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.plot-purpose {
  position: relative;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 62px;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--gray-500);
  cursor: pointer;
}

.plot-purpose:hover {
  border-color: var(--border-color-dark);
}

.plot-purpose.active {
  border-color: var(--primary-300);
  background: var(--primary-50);
  color: var(--primary-700);
}

.plot-purpose input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.plot-purpose > span {
  display: grid;
  min-width: 0;
  gap: 1px;
}

.plot-purpose strong {
  overflow: hidden;
  color: var(--gray-800);
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plot-purpose small {
  color: var(--gray-500);
  font-size: 11px;
}

.purpose-check {
  color: var(--primary-600);
}

.column-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 11px;
}

.column-grid label,
.title-field {
  display: grid;
  min-width: 0;
  gap: 6px;
}

.column-grid label > span,
.title-field > span {
  color: var(--gray-600);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.column-grid label > span small {
  margin-left: 4px;
  color: var(--gray-400);
  font-weight: var(--font-normal);
}

.column-grid select,
.title-field input {
  width: 100%;
  height: var(--control-height);
  min-width: 0;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--gray-800);
  font: inherit;
  font-size: var(--text-sm);
}

.column-grid select:focus,
.title-field input:focus {
  border-color: var(--primary-400);
  outline: 2px solid var(--primary-100);
  outline-offset: 0;
}

.column-grid select:disabled,
.title-field input:disabled {
  background: var(--surface-2);
  color: var(--gray-400);
}

.group-field {
  grid-column: 1 / -1;
}

.field-warning {
  margin: 9px 0 0;
  color: var(--warning-600);
  font-size: var(--text-xs);
  line-height: 1.45;
}

.finish-section {
  margin-bottom: 0;
  border-bottom: 0;
}

.plot-preview {
  position: sticky;
  top: 0;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  box-shadow: var(--shadow-sm);
}

.preview-header {
  display: flex;
  min-height: 58px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color-light);
}

.preview-header > div {
  display: grid;
  gap: 1px;
}

.preview-header > div > span {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.preview-header strong {
  color: var(--gray-800);
  font-size: var(--text-sm);
}

.preview-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--success-600);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.preview-stage {
  position: relative;
  height: clamp(390px, 57vh, 560px);
  min-width: 0;
  background: #ffffff;
}

.chart-canvas {
  width: 100%;
  height: 100%;
}

.preview-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 7px;
  padding: 24px;
  color: var(--gray-400);
  text-align: center;
}

.preview-empty strong {
  color: var(--gray-700);
  font-size: var(--text-sm);
}

.preview-empty span {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.preview-actions {
  display: flex;
  min-height: 58px;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--border-color-light);
  background: #fbfcfe;
}

.preview-actions > button {
  display: inline-flex;
  flex: 0 0 auto;
  min-height: 36px;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 12px;
  border-radius: var(--radius-base);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  white-space: nowrap;
  cursor: pointer;
}

.preview-actions > button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.secondary-action {
  border: 1px solid var(--border-color);
  background: var(--surface-1);
  color: var(--gray-700);
}

.primary-action {
  border: 1px solid var(--primary-600);
  background: var(--primary-600);
  color: white;
}

.save-feedback {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 6px;
  margin-right: auto;
  overflow: hidden;
  color: var(--success-600);
  font-size: var(--text-xs);
}

.save-feedback button,
.save-feedback span {
  overflow: hidden;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.save-feedback button {
  cursor: pointer;
}

.analysis-figures {
  min-width: 0;
}

.example-output {
  display: grid;
  grid-template-columns: minmax(260px, 0.72fr) minmax(420px, 1.28fr);
  min-height: 360px;
  margin: 4px 0 30px;
  overflow: hidden;
  border-top: 1px solid var(--border-color-light);
  border-bottom: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.example-output__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 32px;
}

.example-label {
  color: var(--primary-600);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
}

.example-output__copy h2 {
  margin: 6px 0 8px;
  color: var(--gray-900);
  font-size: var(--text-xl);
}

.example-output__copy p {
  max-width: 42ch;
  margin: 0;
  color: var(--gray-600);
  font-size: var(--text-sm);
  line-height: 1.6;
}

.example-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 18px;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.example-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.example-legend i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--gray-400);
}

.example-legend i.hq { background: #009e73; }
.example-legend i.mq { background: #e69f00; }
.example-legend i.lq { background: #94a3b8; }

.example-output__copy > a {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  gap: 7px;
  margin-top: 24px;
  padding: 0 12px;
  border: 1px solid var(--primary-600);
  border-radius: var(--radius-base);
  background: var(--primary-600);
  color: white;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  text-decoration: none;
}

.example-output__figure {
  position: relative;
  min-width: 0;
  min-height: 360px;
  border-left: 1px solid var(--border-color-light);
  background: #ffffff;
}

.example-output__figure > span {
  position: absolute;
  top: 12px;
  right: 14px;
  color: var(--gray-400);
  font-size: 11px;
  font-weight: var(--font-medium);
}

.example-chart {
  width: 100%;
  height: 100%;
  min-height: 360px;
}

.figure-section + .figure-section {
  margin-top: 30px;
  padding-top: 24px;
  border-top: 1px solid var(--border-color-light);
}

.figure-section__header {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  margin-bottom: 13px;
}

.figure-section__icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--primary-700);
}

.figure-section__header > div {
  display: grid;
  gap: 1px;
}

.figure-section__header h2 {
  margin: 0;
  color: var(--gray-900);
  font-size: var(--text-base);
}

.figure-section__header span,
.figure-section__header a {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.figure-section__header a {
  color: var(--primary-700);
  font-weight: var(--font-semibold);
  text-decoration: none;
}

.gallery-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 15px;
}

.gallery-toolbar > div:first-child {
  display: grid;
  gap: 2px;
}

.gallery-toolbar strong {
  color: var(--gray-900);
  font-size: var(--text-base);
}

.gallery-toolbar span {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.gallery-toolbar > .gallery-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 7px;
}

.gallery-toolbar-actions .clear-scope {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--surface-1);
  color: var(--gray-600);
  font-size: var(--text-xs);
  cursor: pointer;
}

.gallery-toolbar-actions .clear-scope:hover {
  border-color: var(--border-color-dark);
  background: var(--surface-2);
  color: var(--primary-700);
}

.gallery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(260px, 100%), 1fr));
  gap: 14px;
}

.figure-card {
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-1);
}

.figure-preview {
  display: grid;
  width: 100%;
  aspect-ratio: 16 / 10;
  place-items: center;
  overflow: hidden;
  border-bottom: 1px solid var(--border-color-light);
  background: #ffffff;
}

button.figure-preview {
  padding: 0;
  color: inherit;
  cursor: zoom-in;
}

button.figure-preview:hover img {
  transform: scale(1.015);
}

.figure-preview img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  transition: transform var(--transition-base);
}

.figure-placeholder {
  gap: 7px;
  color: var(--gray-400);
  font-size: var(--text-xs);
}

.figure-info {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px 12px;
  padding: 11px 12px;
}

.figure-title-line {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.figure-title-line strong {
  overflow: hidden;
  color: var(--gray-800);
  font-size: var(--text-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.figure-title-line span,
.figure-meta {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.figure-meta {
  display: flex;
  grid-column: 1;
  flex-wrap: wrap;
  gap: 4px 10px;
}

.figure-actions {
  display: flex;
  grid-row: 1 / 3;
  grid-column: 2;
  align-items: center;
  gap: 5px;
}

.figure-actions a,
.figure-actions button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--gray-600);
  background: var(--surface-1);
  cursor: pointer;
}

.figure-actions a:hover,
.figure-actions button:hover {
  border-color: var(--border-color-dark);
  background: var(--surface-2);
  color: var(--primary-700);
}

.gallery-state {
  display: grid;
  min-height: 280px;
  place-content: center;
  justify-items: center;
  gap: 8px;
  color: var(--gray-400);
  text-align: center;
}

.gallery-state strong {
  color: var(--gray-700);
  font-size: var(--text-sm);
}

.gallery-state.compact {
  min-height: 110px;
  margin-top: 20px;
  border-top: 1px solid var(--border-color-light);
}

.gallery-state button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--primary-700);
  font: inherit;
  font-size: var(--text-sm);
  cursor: pointer;
}

.figure-viewer__dialog {
  width: min(1120px, calc(100vw - 40px));
  height: min(820px, calc(100vh - 40px));
  min-width: 0;
  overflow: hidden;
}

.figure-viewer__header > div {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.figure-viewer__header span {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.figure-viewer__header h3 {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.figure-viewer__body {
  display: grid;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  place-items: center;
  overflow: hidden;
  padding: 18px;
  background: #f7f9fc;
}

.figure-viewer__body img {
  display: block;
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.figure-viewer__footer a {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--surface-1);
  color: var(--gray-700);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.figure-viewer__footer a:hover {
  border-color: var(--border-color-dark);
  background: var(--surface-2);
  color: var(--primary-700);
}

.figure-viewer__spacer {
  flex: 1 1 auto;
}

.figure-skeleton {
  aspect-ratio: 16 / 12;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
  background: var(--surface-2);
  animation: figure-pulse 1.2s ease-in-out infinite alternate;
}

@keyframes figure-pulse {
  to { opacity: 0.45; }
}

@media (max-width: 1050px) {
  .plot-builder {
    grid-template-columns: minmax(280px, 380px) minmax(0, 1fr);
    gap: 18px;
  }
}

@media (max-width: 860px) {
  .plot-studio__inner {
    padding: 16px 18px 30px;
  }

  .plot-builder {
    grid-template-columns: minmax(0, 1fr);
  }

  .plot-preview {
    position: static;
  }

  .preview-stage {
    height: min(68vw, 500px);
    min-height: 360px;
  }

  .example-output {
    grid-template-columns: minmax(0, 1fr);
  }

  .example-output__copy {
    padding: 24px;
  }

  .example-output__figure {
    border-top: 1px solid var(--border-color-light);
    border-left: 0;
  }
}

@media (max-width: 520px) {
  .plot-studio__inner {
    padding: 14px 12px 24px;
  }

  .plot-tabs {
    gap: 16px;
  }

  .plot-tabs a {
    min-width: 0;
    font-size: var(--text-xs);
  }

  .plot-run-context {
    align-items: flex-start;
    flex-direction: column;
  }

  .plot-purpose-grid,
  .column-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .group-field {
    grid-column: auto;
  }

  .preview-stage {
    height: 390px;
    min-height: 390px;
  }

  .preview-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .save-feedback {
    grid-column: 1 / -1;
    min-height: 18px;
  }

  .preview-actions > button {
    width: 100%;
    padding-inline: 8px;
  }

  .figure-viewer__dialog {
    width: calc(100vw - 20px);
    height: calc(100vh - 20px);
  }

  .example-output__copy {
    padding: 20px 16px;
  }

  .example-output__figure,
  .example-chart {
    min-height: 320px;
  }

  .figure-viewer__footer {
    flex-wrap: wrap;
  }

  .figure-viewer__spacer {
    display: none;
  }
}
</style>
