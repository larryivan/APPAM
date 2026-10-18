<template>
  <div class="system-performance">
    <div v-if="!systemInfo && error" class="performance-state is-error">
      <Icon name="triangle-alert" :size="20" />
      <p>{{ error }}</p>
      <button type="button" class="btn btn-secondary btn-sm" @click="fetchSystemInfo">Try again</button>
    </div>

    <div v-else-if="!systemInfo" class="performance-state">
      <Icon name="rotate-ccw" :size="20" spin />
      <p>Reading system status…</p>
    </div>

    <div v-else class="performance-content">
      <!-- Updates are continuous; only say something when they stop arriving. -->
      <p v-if="error" class="stale-notice" role="status" aria-live="polite">
        <Icon name="triangle-alert" :size="14" />
        Couldn't refresh. Showing values from {{ formatClock(lastUpdated) }}.
      </p>

      <section class="metric-grid" aria-label="Current usage">
        <article v-for="metric in metrics" :key="metric.key" class="metric" :class="`tone-${metric.tone}`">
          <header class="metric-label">
            <Icon :name="metric.icon" :size="14" />
            <span>{{ metric.label }}</span>
            <em v-if="metric.tone !== 'normal'">{{ metric.tone === 'critical' ? 'Critical' : 'High' }}</em>
          </header>
          <strong class="metric-value">{{ metric.value }}<small v-if="metric.unit">{{ metric.unit }}</small></strong>
          <div
            class="meter"
            role="meter"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuenow="Math.round(metric.percent ?? 0)"
            :aria-label="`${metric.label} usage`"
          >
            <span :style="{ width: meterWidth(metric.percent) }"></span>
          </div>
          <p class="metric-detail">{{ metric.detail }}</p>
        </article>
      </section>

      <div class="chart-grid">
        <section class="panel">
          <header class="panel-header">
            <h4>CPU and memory</h4>
            <ul class="chart-keys">
              <li v-for="series in UTILISATION_SERIES" :key="series.key">
                <i :style="{ background: `var(${series.color})` }"></i>{{ series.label }}
              </li>
            </ul>
          </header>
          <div class="chart-frame">
            <div ref="utilisationChart" class="chart"></div>
            <p v-if="history.length < 2" class="chart-empty">Collecting samples…</p>
          </div>
        </section>

        <section v-if="hasLoadAverage" class="panel">
          <header class="panel-header">
            <h4>Load average</h4>
            <ul class="chart-keys">
              <li v-for="series in LOAD_SERIES" :key="series.key">
                <i :style="{ background: `var(${series.color})` }"></i>{{ series.label }}
              </li>
            </ul>
          </header>
          <div class="chart-frame">
            <div ref="loadChart" class="chart"></div>
            <p v-if="history.length < 2" class="chart-empty">Collecting samples…</p>
          </div>
        </section>
      </div>

      <section class="panel">
        <header class="panel-header">
          <h4>Storage</h4>
          <span class="panel-meta">{{ disks.length }} {{ disks.length === 1 ? 'volume' : 'volumes' }}</span>
        </header>
        <ul v-if="disks.length" class="volume-list">
          <li v-for="disk in disks" :key="disk.mountpoint" class="volume" :class="`tone-${toneFor(disk.usage_percent)}`">
            <div class="volume-name">
              <strong :title="(disk.mountpoints || [disk.mountpoint]).join('\n')">{{ disk.mountpoint }}</strong>
              <span>{{ [disk.device, disk.file_system].filter(Boolean).join(' · ') }}</span>
            </div>
            <div
              class="meter"
              role="meter"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-valuenow="Math.round(disk.usage_percent)"
              :aria-label="`${disk.mountpoint} usage`"
            >
              <span :style="{ width: meterWidth(disk.usage_percent) }"></span>
            </div>
            <div class="volume-usage">
              <span>{{ formatPair(disk.used, disk.total) }}</span>
              <strong>{{ formatPercent(disk.usage_percent) }}%</strong>
            </div>
          </li>
        </ul>
        <p v-else class="panel-empty">No writable volumes were reported.</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import echarts from '../lib/echarts'

const POLL_INTERVAL_MS = 5000
// Five minutes of history at one sample every five seconds.
const MAX_HISTORY_POINTS = 60

const UTILISATION_SERIES = [
  { key: 'cpu', label: 'CPU', color: '--accent-500', area: true },
  { key: 'memory', label: 'Memory', color: '--gray-500' },
]
const LOAD_SERIES = [
  { key: 'load1', label: '1 min', color: '--accent-500', area: true },
  { key: 'load5', label: '5 min', color: '--gray-500' },
  { key: 'load15', label: '15 min', color: '--gray-300' },
]

const systemInfo = ref(null)
const error = ref(null)
const lastUpdated = ref(null)
const history = ref([])

const utilisationChart = ref(null)
const loadChart = ref(null)
let utilisationChartInstance = null
let loadChartInstance = null
let resizeObserver = null
let updateInterval = null
let componentActive = false
let requestInFlight = false

const fetchSystemInfo = async () => {
  if (requestInFlight) return
  requestInFlight = true

  try {
    const response = await fetch('/api/system/info')
    const data = await response.json().catch(() => ({}))
    if (!response.ok || !data.success) {
      throw new Error(data.error || data.message || 'System status is unavailable')
    }
    if (!componentActive) return

    systemInfo.value = data.data
    error.value = null
    lastUpdated.value = new Date()
    recordSample(data.data)
  } catch (err) {
    if (componentActive) error.value = err.message
  } finally {
    requestInFlight = false
  }
}

const recordSample = (info) => {
  const load = info.load || {}
  history.value = [
    ...history.value,
    {
      time: formatClock(lastUpdated.value),
      cpu: info.cpu?.usage_percent ?? 0,
      memory: info.memory?.usage_percent ?? 0,
      load1: load.load_1min ?? null,
      load5: load.load_5min ?? null,
      load15: load.load_15min ?? null,
    },
  ].slice(-MAX_HISTORY_POINTS)
}

// Derived state

const cores = computed(() => systemInfo.value?.cpu?.logical_cores || 0)
const disks = computed(() => systemInfo.value?.disk || [])
const hasLoadAverage = computed(() => systemInfo.value?.load?.load_5min != null)

const metrics = computed(() => {
  const info = systemInfo.value
  if (!info) return []
  const cpu = info.cpu || {}
  const memory = info.memory || {}
  const load = info.load || {}

  const storage = disks.value.reduce(
    (sum, disk) => ({ used: sum.used + disk.used, total: sum.total + disk.total, free: sum.free + disk.free }),
    { used: 0, total: 0, free: 0 },
  )
  const storagePercent = storage.used + storage.free > 0 ? (storage.used / (storage.used + storage.free)) * 100 : null
  const perCoreLoad = cores.value && load.load_1min != null ? load.load_1min / cores.value : null

  return [
    {
      key: 'cpu',
      label: 'CPU',
      icon: 'cpu',
      value: formatPercent(cpu.usage_percent),
      unit: '%',
      percent: cpu.usage_percent,
      detail: [
        cores.value ? `${cores.value} cores` : '',
        cpu.frequency?.current ? `${(cpu.frequency.current / 1000).toFixed(1)} GHz` : '',
      ].filter(Boolean).join(' · ') || '—',
    },
    {
      key: 'memory',
      label: 'Memory',
      icon: 'memory-stick',
      value: formatPercent(memory.usage_percent),
      unit: '%',
      percent: memory.usage_percent,
      detail: memory.total ? `${formatPair(memory.used, memory.total)} used` : '—',
    },
    {
      key: 'storage',
      label: 'Storage',
      icon: 'hard-drive',
      value: formatPercent(storagePercent),
      unit: storagePercent == null ? '' : '%',
      percent: storagePercent,
      detail: storage.total ? `${formatBytes(storage.free)} free` : '—',
    },
    {
      key: 'load',
      label: 'Load · 1 min',
      icon: 'activity',
      value: load.load_1min != null ? load.load_1min.toFixed(2) : '—',
      unit: '',
      percent: perCoreLoad == null ? null : perCoreLoad * 100,
      detail: perCoreLoad == null ? '—' : `${perCoreLoad.toFixed(2)} per core`,
    },
  ].map((metric) => ({ ...metric, tone: toneFor(metric.percent) }))
})

// Charts

const cssValue = (name, fallback) => {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

const chartTheme = () => ({
  text: cssValue('--gray-500', '#677079'),
  ink: cssValue('--gray-800', '#232930'),
  axis: cssValue('--border-color', '#dfe2e6'),
  grid: cssValue('--border-color-light', '#eaecef'),
  surface: cssValue('--surface-1', '#ffffff'),
  font: cssValue('--font-family-base', 'Inter, sans-serif'),
  accentRgb: cssValue('--accent-rgb', '47, 98, 196'),
})

const lineChartOption = ({ seriesList, yAxis, valueFormatter, extraSeries = {} }) => {
  const theme = chartTheme()
  return {
    animation: false,
    textStyle: { fontFamily: theme.font },
    grid: { left: 4, right: 12, top: 12, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'axis',
      valueFormatter,
      backgroundColor: theme.surface,
      borderColor: theme.axis,
      textStyle: { color: theme.ink, fontSize: 12 },
      axisPointer: { lineStyle: { color: theme.axis } },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: history.value.map((sample) => sample.time),
      axisLabel: { color: theme.text, fontSize: 11, hideOverlap: true },
      axisLine: { lineStyle: { color: theme.axis } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      splitNumber: 2,
      axisLabel: { color: theme.text, fontSize: 11 },
      splitLine: { lineStyle: { color: theme.grid } },
      ...yAxis,
    },
    series: seriesList.map((series, index) => {
      const color = cssValue(series.color, theme.text)
      return {
        name: series.label,
        type: 'line',
        data: history.value.map((sample) => sample[series.key]),
        smooth: 0.3,
        showSymbol: false,
        symbolSize: 5,
        lineStyle: { color, width: 1.75 },
        itemStyle: { color },
        areaStyle: series.area
          ? {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: `rgba(${theme.accentRgb}, 0.14)` },
                { offset: 1, color: `rgba(${theme.accentRgb}, 0)` },
              ]),
            }
          : undefined,
        ...(index === 0 ? extraSeries : {}),
      }
    }),
  }
}

const updateCharts = () => {
  if (!componentActive) return
  ensureCharts()

  utilisationChartInstance?.setOption(lineChartOption({
    seriesList: UTILISATION_SERIES,
    yAxis: { max: 100, interval: 50, axisLabel: { color: chartTheme().text, fontSize: 11, formatter: '{value}%' } },
    valueFormatter: (value) => (value == null ? '—' : `${Number(value).toFixed(1)}%`),
  }), true)

  if (loadChartInstance && cores.value) {
    const theme = chartTheme()
    loadChartInstance.setOption(lineChartOption({
      seriesList: LOAD_SERIES,
      // Keep the core count in view: load above it means work is queueing.
      yAxis: { max: ({ max }) => Math.ceil(Math.max(max, cores.value) * 1.15) },
      valueFormatter: (value) => (value == null ? '—' : Number(value).toFixed(2)),
      extraSeries: {
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: theme.text, type: 'dashed', width: 1, opacity: 0.6 },
          label: { formatter: `${cores.value} cores`, position: 'insideEndTop', color: theme.text, fontSize: 11 },
          data: [{ yAxis: cores.value }],
        },
      },
    }), true)
  }
}

const ensureCharts = () => {
  if (utilisationChart.value && !utilisationChartInstance) {
    utilisationChartInstance = echarts.init(utilisationChart.value)
    resizeObserver?.observe(utilisationChart.value)
  }
  if (loadChart.value && !loadChartInstance) {
    loadChartInstance = echarts.init(loadChart.value)
    resizeObserver?.observe(loadChart.value)
  }
}

watch(history, () => nextTick(updateCharts))

// Formatting

const formatClock = (date) => date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

const formatPercent = (value) => (value == null || Number.isNaN(value) ? '—' : Number(value).toFixed(1))

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

const byteUnit = (bytes) => (bytes > 0 ? Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), BYTE_UNITS.length - 1) : 0)

const scaledBytes = (bytes, unit) => {
  const value = bytes / 1024 ** unit
  return value >= 100 || unit === 0 ? Math.round(value).toString() : String(parseFloat(value.toFixed(1)))
}

const formatBytes = (bytes = 0) => {
  const unit = byteUnit(bytes)
  return `${scaledBytes(bytes, unit)} ${BYTE_UNITS[unit]}`
}

// "1.1 of 1.8 TB" reads faster than "1.1 TB / 1.8 TB"; keep both units when they differ.
const formatPair = (used = 0, total = 0) => {
  const unit = byteUnit(total)
  if (byteUnit(used) === unit || used === 0) return `${scaledBytes(used, unit)} of ${formatBytes(total)}`
  return `${formatBytes(used)} of ${formatBytes(total)}`
}

const toneFor = (percent) => {
  if (percent == null) return 'normal'
  if (percent >= 90) return 'critical'
  if (percent >= 70) return 'elevated'
  return 'normal'
}

const meterWidth = (percent) => `${Math.min(100, Math.max(0, percent ?? 0))}%`

// Lifecycle

const poll = () => {
  if (componentActive && !document.hidden) fetchSystemInfo()
}

onMounted(() => {
  componentActive = true
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      utilisationChartInstance?.resize()
      loadChartInstance?.resize()
    })
  }
  fetchSystemInfo()
  updateInterval = setInterval(poll, POLL_INTERVAL_MS)
})

onUnmounted(() => {
  componentActive = false
  clearInterval(updateInterval)
  updateInterval = null
  resizeObserver?.disconnect()
  resizeObserver = null
  utilisationChartInstance?.dispose()
  loadChartInstance?.dispose()
  utilisationChartInstance = null
  loadChartInstance = null
})
</script>

<style scoped>
.system-performance {
  container-type: inline-size;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--surface-0);
}

.performance-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-3);
  padding: var(--spacing-8);
  color: var(--gray-500);
  font-size: var(--text-sm);
  text-align: center;
}

.performance-state p {
  margin: 0;
}

.performance-state.is-error {
  color: var(--error-600);
}

.performance-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.stale-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 8px 12px;
  border: var(--border-width) solid rgb(187 70 70 / 0.2);
  border-radius: var(--radius-base);
  background: var(--error-50);
  color: var(--error-600);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
}

/* Current usage */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  padding: 14px 16px 16px;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
}

.metric-label {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  color: var(--gray-500);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.metric-label span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-label em {
  margin-left: auto;
  font-style: normal;
  font-weight: var(--font-semibold);
}

.metric-value {
  color: var(--gray-900);
  font-size: 1.625rem;
  font-weight: var(--font-semibold);
  letter-spacing: var(--tracking-tight);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.metric-value small {
  margin-left: 2px;
  color: var(--gray-400);
  font-size: var(--text-base);
  font-weight: var(--font-medium);
}

.metric-detail {
  margin: 0;
  overflow: hidden;
  color: var(--gray-500);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Meters: ink while healthy, colour only when something needs attention. */
.meter {
  height: 4px;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: var(--gray-100);
}

.meter span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--gray-700);
  transition: width var(--transition-slow);
}

.tone-elevated .metric-label em,
.tone-elevated .volume-usage strong {
  color: var(--warning-600);
}

.tone-elevated .meter span {
  background: var(--warning-500);
}

.tone-critical .metric-label em,
.tone-critical .volume-usage strong {
  color: var(--error-600);
}

.tone-critical .meter span {
  background: var(--error-500);
}

/* Panels */
.chart-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 300px), 1fr));
  gap: 12px;
}

.panel {
  min-width: 0;
  padding: 14px 16px 12px;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-3);
  margin-bottom: 8px;
}

.panel-header h4 {
  margin: 0;
  color: var(--gray-800);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.panel-meta {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.chart-keys {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 4px 12px;
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.chart-keys li {
  display: flex;
  align-items: center;
  gap: 6px;
}

.chart-keys i {
  width: 10px;
  height: 2px;
  border-radius: var(--radius-full);
}

.chart-frame {
  position: relative;
}

.chart {
  width: 100%;
  height: clamp(170px, 24vh, 260px);
}

.chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  color: var(--gray-400);
  font-size: var(--text-xs);
  pointer-events: none;
}

/* Storage */
.volume-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.volume {
  display: grid;
  grid-template-columns: minmax(0, 240px) minmax(80px, 1fr) auto;
  align-items: center;
  gap: var(--spacing-4);
  padding: 10px 0;
}

.volume + .volume {
  border-top: var(--border-width) solid var(--border-color-light);
}

.volume-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.volume-name strong,
.volume-name span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.volume-name strong {
  color: var(--gray-800);
  font-family: var(--font-family-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.volume-name span {
  color: var(--gray-400);
  font-size: 11px;
}

.volume-usage {
  display: flex;
  align-items: baseline;
  gap: 10px;
  color: var(--gray-500);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.volume-usage strong {
  min-width: 3.5em;
  color: var(--gray-800);
  font-weight: var(--font-semibold);
  text-align: right;
}

.panel-empty {
  margin: 0;
  padding: 8px 0 4px;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

/* Sized by the monitor window, which the user can drag narrower than the page. */
@container (max-width: 640px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@container (max-width: 420px) {
  .performance-content {
    padding: 12px;
  }

  .volume {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .volume .meter {
    grid-column: 1 / -1;
    grid-row: 2;
  }
}

@media (prefers-reduced-motion: reduce) {
  .meter span {
    transition: none;
  }
}
</style>
