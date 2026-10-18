<template>
  <div class="report-center">
    <div class="report-center__inner">
      <PageHeader eyebrow="Project" title="Reports" description="Read, share and export analysis reports without leaving APPAM">
        <template #meta>
          <span>{{ project?.name || `Project ${projectId}` }}</span>
          <span>{{ reports.length }} {{ reports.length === 1 ? 'report' : 'reports' }}</span>
        </template>
        <template #actions>
          <button
            type="button"
            class="header-icon-button"
            title="Refresh reports"
            aria-label="Refresh reports"
            :disabled="loading"
            @click="loadReports"
          >
            <Icon name="rotate-ccw" :size="17" :spin="loading" />
          </button>
        </template>
      </PageHeader>

      <section
        class="report-shell"
        :class="{ 'report-shell--empty': !loading && !loadError && reports.length === 0 }"
        aria-label="Analysis reports"
      >
        <aside v-if="loading || loadError || reports.length" class="report-index">
          <header class="report-index__header">
            <div>
              <strong>Available reports</strong>
              <span>Newest first</span>
            </div>
            <span class="report-count">{{ reports.length }}</span>
          </header>

          <div v-if="loading" class="report-list" aria-label="Loading reports">
            <div v-for="index in 4" :key="index" class="report-list-skeleton"></div>
          </div>

          <div v-else-if="loadError" class="report-index-state" role="alert">
            <Icon name="triangle-alert" :size="20" />
            <strong>Reports could not be loaded</strong>
            <button type="button" @click="loadReports">Try again</button>
          </div>

          <div v-else-if="reports.length === 0" class="report-index-state">
            <Icon name="file-text" :size="22" />
            <strong>No reports yet</strong>
            <span>Completed analyses will appear here.</span>
          </div>

          <div v-else class="report-list">
            <button
              v-for="report in reports"
              :key="report.id"
              type="button"
              class="report-list-item"
              :class="{ active: selectedReport?.id === report.id }"
              @click="selectReport(report)"
            >
              <span class="report-list-icon"><Icon name="file-text" :size="17" /></span>
              <span class="report-list-copy">
                <strong>{{ report.title }}</strong>
                <span>{{ workflowLabel(report.workflowId) }} · {{ formatDate(report.createdAt) }}</span>
                <small :title="report.runId">Run {{ shortRunId(report.runId) }}</small>
              </span>
              <Icon name="chevron-right" :size="15" class="report-list-arrow" />
            </button>
          </div>
        </aside>

        <main class="report-viewer">
          <div v-if="!selectedReport" class="report-viewer-state">
            <Icon name="clipboard-list" :size="30" />
            <strong>{{ loading ? 'Loading reports' : 'No reports yet' }}</strong>
            <span>
              Reports are generated when an analysis completes. They collect the summary
              table, quality metrics and workflow figures for a single run.
            </span>
            <router-link v-if="!loading" :to="analysisHubRoute">Choose analysis</router-link>
          </div>

          <template v-else>
            <header class="report-viewer__header">
              <div class="report-viewer-copy">
                <span>{{ workflowLabel(selectedReport.workflowId) }}</span>
                <strong>{{ selectedReport.title }}</strong>
                <small>{{ formatDateTime(selectedReport.createdAt) }} · {{ formatBytes(selectedReport.size) }}</small>
              </div>
              <div class="report-viewer-actions">
                <router-link :to="analysisRoute(selectedReport)" title="Open source analysis">
                  <Icon name="activity" :size="16" />
                  <span>Results</span>
                </router-link>
                <router-link :to="plotsRoute(selectedReport)" title="View figures from this run">
                  <Icon name="images" :size="16" />
                  <span>Figures</span>
                </router-link>
                <!-- Some embedded browsers refuse sandboxed frames outright and
                     show nothing. The report is also served with a CSP sandbox,
                     so opening it on its own is equally isolated. -->
                <a
                  :href="reportUrl(selectedReport.path)"
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Open report in a new tab"
                >
                  <Icon name="external-link" :size="16" />
                  <span>Open</span>
                </a>
                <a :href="downloadUrl(selectedReport.path)" title="Download report">
                  <Icon name="download" :size="16" />
                  <span>Download</span>
                </a>
              </div>
            </header>

            <div class="report-frame-wrap" :aria-busy="frameLoading">
              <div v-if="frameLoading" class="report-frame-loading">
                <Icon name="rotate-ccw" :size="22" spin />
                <span>Opening report</span>
              </div>
              <iframe
                :key="selectedReport.id"
                class="report-frame"
                :src="reportUrl(selectedReport.path)"
                :title="selectedReport.title"
                sandbox="allow-scripts"
                referrerpolicy="no-referrer"
                @load="frameLoading = false"
              ></iframe>
            </div>

            <footer class="report-viewer__footer">
              <span class="mono" :title="selectedReport.path">{{ selectedReport.path }}</span>
              <span v-if="selectedReport.sha256" :title="selectedReport.sha256">SHA-256 {{ selectedReport.sha256.slice(0, 12) }}</span>
            </footer>
          </template>
        </main>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { withBase } from '@/lib/basePath.js'
import { collectWorkflowReports } from '@/lib/resultArtifacts.js'
import { getWorkflowOption } from '@/lib/workflowUi.js'

const route = useRoute()
const router = useRouter()
const project = inject('appamProject', ref(null))

const projectId = computed(() => String(route.params.id || ''))
const reports = ref([])
const loading = ref(false)
const loadError = ref('')
const frameLoading = ref(false)
let loadController = null

const selectedReport = computed(() => {
  const requestedPath = String(route.query.path || '')
  const requestedRun = String(route.query.run || '')
  const requestedWorkflow = String(route.query.workflow || '')
  return reports.value.find((report) => report.path === requestedPath && (!requestedRun || report.runId === requestedRun))
    || reports.value.find((report) => requestedRun && report.runId === requestedRun)
    || reports.value.find((report) => requestedWorkflow && report.workflowId === requestedWorkflow)
    || reports.value[0]
    || null
})

const analysisHubRoute = computed(() => ({
  name: 'Overview',
  params: { id: projectId.value },
  hash: '#analysis-workflows',
}))

function workflowLabel(workflowId) {
  return getWorkflowOption(workflowId)?.shortLabel || 'Analysis'
}

function reportQuery(report) {
  return {
    path: report.path,
    run: report.runId,
    workflow: report.workflowId,
  }
}

function selectReport(report) {
  if (!report || selectedReport.value?.id === report.id) return
  router.replace({ name: 'ReportCenter', params: { id: projectId.value }, query: reportQuery(report) })
}

function analysisRoute(report) {
  if (!report?.workflowId) return analysisHubRoute.value
  return {
    name: 'WorkflowView',
    params: { id: projectId.value, workflowId: report.workflowId },
    query: { tab: 'results', run: report.runId },
  }
}

function plotsRoute(report) {
  return {
    name: 'PlotStudio',
    params: { id: projectId.value },
    query: { view: 'analysis', run: report.runId, workflow: report.workflowId },
  }
}

function reportUrl(path) {
  return withBase(`/api/filemanager/${projectId.value}/report?path=${encodeURIComponent(path)}`)
}

function downloadUrl(path) {
  return withBase(`/api/filemanager/${projectId.value}/download?path=${encodeURIComponent(path)}`)
}

function shortRunId(runId) {
  return runId ? runId.slice(0, 8) : 'unknown'
}

function parseDate(value) {
  if (!value) return null
  const date = new Date(String(value).replace(' ', 'T'))
  return Number.isNaN(date.getTime()) ? null : date
}

function formatDate(value) {
  return parseDate(value)?.toLocaleDateString() || 'Date unavailable'
}

function formatDateTime(value) {
  return parseDate(value)?.toLocaleString() || 'Date unavailable'
}

function formatBytes(bytes) {
  const numeric = Number(bytes)
  if (!Number.isFinite(numeric) || numeric <= 0) return 'Size unavailable'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = numeric
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value >= 10 || index === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[index]}`
}

async function syncSelectedReport() {
  const report = selectedReport.value
  if (!report) return
  const queryMatches = String(route.query.path || '') === report.path
    && String(route.query.run || '') === report.runId
    && String(route.query.workflow || '') === report.workflowId
  if (!queryMatches) {
    await router.replace({ name: 'ReportCenter', params: { id: projectId.value }, query: reportQuery(report) })
  }
}

async function loadReports() {
  loadController?.abort()
  const controller = new AbortController()
  loadController = controller
  loading.value = true
  loadError.value = ''
  try {
    const response = await fetch(
      `/api/pipeline/${projectId.value}/workflow-runs?limit=100&include_results=true`,
      { signal: controller.signal },
    )
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'Reports could not be loaded.')
    if (controller.signal.aborted) return
    reports.value = collectWorkflowReports(payload.workflow_runs || [])
    await syncSelectedReport()
  } catch (error) {
    if (error?.name === 'AbortError') return
    loadError.value = error instanceof Error ? error.message : 'Reports could not be loaded.'
  } finally {
    if (loadController === controller) {
      loadController = null
      loading.value = false
    }
  }
}

watch(selectedReport, (report, previous) => {
  if (report?.id !== previous?.id) frameLoading.value = Boolean(report)
})

watch(projectId, () => {
  reports.value = []
  loadReports()
}, { immediate: true })

onBeforeUnmount(() => loadController?.abort())
</script>

<style scoped>
.report-center {
  width: 100%;
  height: 100%;
  min-width: 0;
  overflow: hidden;
  background: var(--surface-0);
}

.report-center__inner {
  display: flex;
  flex-direction: column;
  width: min(1480px, 100%);
  height: 100%;
  min-width: 0;
  margin: 0 auto;
  padding: 22px 26px 26px;
}

.header-icon-button {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--surface-1);
  color: var(--gray-600);
  cursor: pointer;
}

.header-icon-button:hover:not(:disabled) {
  border-color: var(--border-color-dark);
  background: var(--surface-2);
  color: var(--primary-700);
}

.header-icon-button:disabled {
  cursor: wait;
  opacity: 0.6;
}

.report-shell {
  display: grid;
  flex: 1 1 auto;
  grid-template-columns: 286px minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-1);
}

.report-shell--empty {
  grid-template-columns: minmax(0, 1fr);
}

.report-index {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  border-right: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.report-index__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 62px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color-light);
}

.report-index__header > div,
.report-list-copy,
.report-viewer-copy {
  display: grid;
  min-width: 0;
  gap: 2px;
}

.report-index__header strong {
  color: var(--gray-800);
  font-size: var(--text-sm);
}

.report-index__header span,
.report-list-copy span,
.report-list-copy small,
.report-viewer-copy span,
.report-viewer-copy small {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.report-count {
  min-width: 26px;
  padding: 3px 7px;
  border-radius: 999px;
  background: var(--surface-3);
  color: var(--gray-600) !important;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.report-list {
  min-height: 0;
  overflow-y: auto;
  padding: 6px;
  scrollbar-width: thin;
  scrollbar-color: var(--gray-300) transparent;
}

.report-list-item {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 16px;
  width: 100%;
  min-width: 0;
  align-items: center;
  gap: 9px;
  padding: 10px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-600);
  text-align: left;
  cursor: pointer;
}

.report-list-item:hover {
  background: var(--surface-2);
}

.report-list-item.active {
  border-color: var(--primary-200);
  background: var(--primary-50);
  color: var(--primary-700);
}

.report-list-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border: 1px solid var(--border-color-light);
  border-radius: 6px;
  background: var(--surface-1);
}

.report-list-copy strong {
  overflow: hidden;
  color: var(--gray-800);
  font-size: var(--text-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-list-copy span,
.report-list-copy small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-list-item.active .report-list-copy strong {
  color: var(--primary-800);
}

.report-list-arrow {
  opacity: 0;
}

.report-list-item.active .report-list-arrow {
  opacity: 1;
}

.report-list-skeleton {
  height: 76px;
  margin-bottom: 5px;
  border-radius: 6px;
  background: var(--surface-2);
  animation: report-pulse 1.2s ease-in-out infinite alternate;
}

.report-index-state,
.report-viewer-state {
  display: grid;
  min-height: 0;
  place-content: center;
  justify-items: center;
  gap: 8px;
  padding: 22px;
  color: var(--gray-400);
  text-align: center;
}

.report-index-state {
  flex: 1 1 auto;
}

.report-index-state strong,
.report-viewer-state strong {
  color: var(--gray-700);
  font-size: var(--text-sm);
}

.report-index-state span,
.report-viewer-state span {
  max-width: 48ch;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.report-index-state button,
.report-viewer-state a {
  border: 0;
  background: transparent;
  color: var(--primary-700);
  font: inherit;
  font-size: var(--text-sm);
  cursor: pointer;
}

.report-viewer {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  background: #f7f9fc;
}

.report-viewer-state {
  flex: 1 1 auto;
}

.report-viewer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 62px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.report-viewer-copy strong {
  overflow: hidden;
  color: var(--gray-900);
  font-size: var(--text-base);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-viewer-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 6px;
}

.report-viewer-actions a {
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

.report-viewer-actions a:hover {
  border-color: var(--border-color-dark);
  background: var(--surface-2);
  color: var(--primary-700);
}

.report-frame-wrap {
  position: relative;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: #ffffff;
}

.report-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: #ffffff;
}

.report-frame-loading {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 9px;
  background: var(--surface-1);
  color: var(--gray-500);
  font-size: var(--text-sm);
}

.report-viewer__footer {
  display: flex;
  min-height: 34px;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 7px 12px;
  border-top: 1px solid var(--border-color-light);
  background: var(--surface-1);
  color: var(--gray-500);
  font-size: 11px;
}

.report-viewer__footer span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@keyframes report-pulse {
  to { opacity: 0.45; }
}

@media (max-width: 900px) {
  .report-center {
    overflow-y: auto;
  }

  .report-center__inner {
    height: auto;
    min-height: 100%;
    padding: 16px 18px 28px;
  }

  .report-shell {
    grid-template-columns: minmax(0, 1fr);
    overflow: visible;
  }

  .report-index {
    border-right: 0;
    border-bottom: 1px solid var(--border-color-light);
  }

  .report-list {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
    max-height: none;
    overflow: visible;
  }

  .report-frame-wrap {
    height: 70vh;
    min-height: 560px;
  }
}

@media (max-width: 620px) {
  .report-center__inner {
    padding: 14px 12px 24px;
  }

  .report-center__inner :deep(.page-header) {
    position: relative;
    padding-right: 46px;
  }

  .report-center__inner :deep(.page-header__actions) {
    position: absolute;
    top: 0;
    right: 0;
    width: auto;
  }

  .report-viewer__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .report-viewer-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
  }

  .report-viewer-actions a {
    justify-content: center;
    padding: 0 6px;
  }

  .report-viewer__footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }

  .report-frame-wrap {
    height: 68vh;
    min-height: 500px;
  }
}
</style>
