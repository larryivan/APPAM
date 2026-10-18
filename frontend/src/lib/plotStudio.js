import Papa from 'papaparse'

export const PLOT_TYPES = [
  { id: 'bar', label: 'Compare groups', detail: 'Bar chart', icon: 'chart-bar' },
  { id: 'line', label: 'Show a trend', detail: 'Line chart', icon: 'chart-line' },
  { id: 'scatter', label: 'Find a relationship', detail: 'Scatter plot', icon: 'chart-scatter' },
  { id: 'pie', label: 'Show composition', detail: 'Composition chart', icon: 'chart-pie' },
]

export const PLOT_TABLE_EXTENSIONS = ['.csv', '.tsv', '.tab', '.txt']

export const WORKFLOW_FIGURE_CATEGORIES = Object.freeze([
  { id: 'read-quality', label: 'Read quality', icon: 'chart-bar' },
  { id: 'authenticity', label: 'Ancient DNA authenticity', icon: 'activity' },
  { id: 'taxonomy', label: 'Taxonomy', icon: 'dna' },
  { id: 'mag-quality', label: 'MAG quality', icon: 'chart-scatter' },
  { id: 'proteomics', label: 'Proteomics', icon: 'target' },
  { id: 'other', label: 'Other analysis figures', icon: 'images' },
])

const FIGURE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp', '.svg', '.pdf'])
const PREVIEW_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp'])
const MISSING_VALUES = new Set(['', 'na', 'n/a', 'nan', 'null', 'none', '-'])
// A categorical ramp tuned to sit beside the interface neutrals: evenly spaced
// in hue, held to a similar lightness so no series shouts louder than another,
// and each step keeps >=3:1 contrast against the white plot ground.
const PLOT_COLORS = ['#2f62c4', '#2f7d6b', '#a9631f', '#a8434f', '#6a50a8', '#4c545c']
const CATEGORY_BY_ID = new Map(WORKFLOW_FIGURE_CATEGORIES.map((category) => [category.id, category]))
const WORKFLOW_FIGURE_SPECS = [
  { match: /\/reads_length\/length_hist$/i, title: 'Read length distribution', category: 'read-quality' },
  { match: /\/contig_stats\/pydamage_props$/i, title: 'PyDamage contig statistics', category: 'authenticity' },
  { match: /\/ani\/ani_hist$/i, title: 'GTDB closest-reference ANI', category: 'taxonomy' },
  { match: /\/rose\/phylum_rose$/i, title: 'Phylum composition', category: 'taxonomy' },
  { match: /\/rose\/genus_rose$/i, title: 'Genus composition', category: 'taxonomy' },
  { match: /\/rose\/species_topn_rose$/i, title: 'Top species composition', category: 'taxonomy' },
  { match: /\/checkm2\/checkm2_scatter$/i, title: 'CheckM2 completeness and contamination', category: 'mag-quality' },
  { match: /\/gunc\/gunc_css_box_jitter$/i, title: 'GUNC clade separation score', category: 'mag-quality' },
  { match: /(paleoproteomics|maxquant).*(qc|quality)/i, title: 'Paleoproteomics quality control', category: 'proteomics' },
]

function extension(path) {
  const match = String(path || '').toLowerCase().match(/(\.[^.\/]+)$/)
  return match?.[1] || ''
}

function isMissing(value) {
  return value === null
    || value === undefined
    || MISSING_VALUES.has(String(value).trim().toLowerCase())
}

export function numericValue(value) {
  if (isMissing(value)) return null
  const normalized = typeof value === 'string' ? value.trim().replace(/,/g, '') : value
  const number = Number(normalized)
  return Number.isFinite(number) ? number : null
}

export function detectNumericColumns(fields, rows) {
  return fields.filter((field) => {
    const values = rows.map((row) => row[field]).filter((value) => !isMissing(value))
    if (values.length === 0) return false
    const numericCount = values.filter((value) => numericValue(value) !== null).length
    return numericCount / values.length >= 0.8
  })
}

export function parsePlotTable(content, path = '') {
  const delimiter = ['.tsv', '.tab'].includes(extension(path)) ? '\t' : ''
  const parsed = Papa.parse(String(content || ''), {
    delimiter,
    header: true,
    skipEmptyLines: 'greedy',
    transformHeader: (header, index) => String(header || '').trim() || `Column ${index + 1}`,
  })
  const fields = (parsed.meta.fields || []).filter(Boolean)
  const rows = (parsed.data || []).filter((row) => (
    fields.some((field) => !isMissing(row[field]))
  ))

  if (fields.length < 2) throw new Error('Choose a table with at least two columns.')
  if (rows.length === 0) throw new Error('No data rows were found in this table.')

  const fatalError = (parsed.errors || []).find((error) => (
    !['TooFewFields', 'TooManyFields', 'UndetectableDelimiter'].includes(error.code)
  ))
  if (fatalError) throw new Error(fatalError.message || 'The table could not be parsed.')

  return {
    fields,
    rows,
    numericColumns: detectNumericColumns(fields, rows),
    delimiter: parsed.meta.delimiter,
  }
}

function categoryValue(value) {
  return isMissing(value) ? 'Missing' : String(value)
}

function average(values) {
  const numbers = values.map(numericValue).filter((value) => value !== null)
  if (!numbers.length) return null
  return numbers.reduce((total, value) => total + value, 0) / numbers.length
}

function baseOption(title) {
  return {
    animation: false,
    backgroundColor: '#ffffff',
    color: PLOT_COLORS,
    textStyle: {
      color: '#4c545c',
      fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    },
    title: {
      text: title,
      top: 14,
      left: 'center',
      textStyle: { color: '#12161a', fontSize: 16, fontWeight: 600 },
    },
    aria: { enabled: true },
  }
}

function groupedRows(rows, groupColumn) {
  if (!groupColumn) return [['Series', rows]]
  const groups = new Map()
  for (const row of rows) {
    const key = categoryValue(row[groupColumn])
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(row)
  }
  return [...groups.entries()].slice(0, 12)
}

function buildCartesianSeries(type, rows, xColumn, yColumn, groupColumn) {
  const validRows = rows.filter((row) => numericValue(row[yColumn]) !== null)
  const categories = [...new Set(validRows.map((row) => categoryValue(row[xColumn])))]
  const series = groupedRows(validRows, groupColumn).map(([group, groupRows]) => {
    const values = new Map()
    for (const row of groupRows) {
      const category = categoryValue(row[xColumn])
      if (!values.has(category)) values.set(category, [])
      values.get(category).push(row[yColumn])
    }
    return {
      name: groupColumn ? group : yColumn,
      type,
      data: categories.map((category) => average(values.get(category) || [])),
      connectNulls: false,
      showSymbol: type === 'line' && categories.length <= 80,
      symbolSize: 7,
      barMaxWidth: 38,
      lineStyle: type === 'line' ? { width: 2 } : undefined,
      itemStyle: { borderRadius: type === 'bar' ? [3, 3, 0, 0] : 0 },
    }
  })
  return { categories, series }
}

function buildScatterSeries(rows, xColumn, yColumn, groupColumn) {
  const validRows = rows.filter((row) => (
    numericValue(row[xColumn]) !== null && numericValue(row[yColumn]) !== null
  ))
  return groupedRows(validRows, groupColumn).map(([group, groupRows]) => ({
    name: groupColumn ? group : `${xColumn} / ${yColumn}`,
    type: 'scatter',
    symbolSize: 9,
    data: groupRows.map((row) => [numericValue(row[xColumn]), numericValue(row[yColumn])]),
  }))
}

function buildPieSeries(rows, xColumn, yColumn) {
  const totals = new Map()
  for (const row of rows) {
    const value = numericValue(row[yColumn])
    if (value === null) continue
    const category = categoryValue(row[xColumn])
    totals.set(category, (totals.get(category) || 0) + value)
  }
  const sorted = [...totals.entries()].sort((left, right) => right[1] - left[1])
  const visible = sorted.slice(0, 19).map(([name, value]) => ({ name, value }))
  if (sorted.length > 19) {
    visible.push({
      name: 'Other',
      value: sorted.slice(19).reduce((total, [, value]) => total + value, 0),
    })
  }
  return visible
}

export function buildPlotOption({ type, title, xColumn, yColumn, groupColumn = '' }, rows) {
  const chartTitle = String(title || '').trim() || `${yColumn} by ${xColumn}`
  const option = baseOption(chartTitle)

  if (type === 'pie') {
    return {
      ...option,
      tooltip: { trigger: 'item' },
      legend: { type: 'scroll', bottom: 12, left: 'center' },
      series: [{
        name: yColumn,
        type: 'pie',
        radius: ['34%', '64%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#ffffff', borderWidth: 2 },
        label: { color: '#4c545c', formatter: '{b}\n{d}%' },
        data: buildPieSeries(rows, xColumn, yColumn),
      }],
    }
  }

  if (type === 'scatter') {
    const series = buildScatterSeries(rows, xColumn, yColumn, groupColumn)
    return {
      ...option,
      tooltip: { trigger: 'item' },
      legend: { show: Boolean(groupColumn), type: 'scroll', bottom: 8 },
      grid: { top: 68, right: 28, bottom: groupColumn ? 66 : 44, left: 62, containLabel: true },
      xAxis: {
        type: 'value',
        name: xColumn,
        nameLocation: 'middle',
        nameGap: 30,
        splitLine: { lineStyle: { color: '#eef0f2' } },
      },
      yAxis: {
        type: 'value',
        name: yColumn,
        nameLocation: 'middle',
        nameGap: 44,
        splitLine: { lineStyle: { color: '#eef0f2' } },
      },
      series,
    }
  }

  const { categories, series } = buildCartesianSeries(type, rows, xColumn, yColumn, groupColumn)
  return {
    ...option,
    tooltip: { trigger: 'axis', axisPointer: { type: type === 'bar' ? 'shadow' : 'line' } },
    legend: { show: Boolean(groupColumn), type: 'scroll', bottom: 8 },
    grid: { top: 68, right: 28, bottom: groupColumn ? 72 : 54, left: 62, containLabel: true },
    xAxis: {
      type: 'category',
      name: xColumn,
      nameLocation: 'middle',
      nameGap: 34,
      data: categories,
      axisLabel: { hideOverlap: true, color: '#677079' },
      axisLine: { lineStyle: { color: '#ccd1d6' } },
    },
    yAxis: {
      type: 'value',
      name: yColumn,
      nameLocation: 'middle',
      nameGap: 44,
      splitLine: { lineStyle: { color: '#eef0f2' } },
    },
    series,
  }
}

export function safePlotName(title) {
  const slug = String(title || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64)
  return slug || 'appam-plot'
}

function figureTitle(value) {
  return String(value || 'Figure')
    .replace(/\.[^.]+$/, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function workflowFigureMetadata(path, label) {
  const stem = String(path || '').replace(/\.[^.]+$/, '')
  const spec = WORKFLOW_FIGURE_SPECS.find((candidate) => candidate.match.test(stem))
  const category = CATEGORY_BY_ID.get(spec?.category || 'other') || CATEGORY_BY_ID.get('other')
  const suppliedLabel = String(label || '').trim()
  const title = spec?.title
    || (!/^(visualization plot|figure|plot|image)$/i.test(suppliedLabel) && suppliedLabel)
    || figureTitle(stem.split('/').pop())
  const segments = String(path || '').split('/').filter(Boolean)
  const visualizationIndex = segments.findIndex((segment) => segment.toLowerCase() === 'visualization')
  const sampleCandidate = visualizationIndex >= 0 ? String(segments[visualizationIndex + 1] || '') : ''
  const sampleId = /^(report|figures?|plots?)$/i.test(sampleCandidate) ? '' : sampleCandidate
  return {
    title,
    category: category.id,
    categoryLabel: category.label,
    categoryIcon: category.icon,
    sampleId,
  }
}

export function collectWorkflowFigures(runs) {
  const groups = new Map()
  for (const run of runs || []) {
    for (const artifact of run.artifacts || []) {
      const path = String(artifact.project_path || '')
      const ext = extension(path)
      if (!path || !FIGURE_EXTENSIONS.has(ext)) continue
      if (artifact.kind !== 'visualization' && !/(visualization|figures?|plots?)/i.test(path)) continue
      const stem = path.replace(/\.[^.]+$/, '')
      const key = `${run.id}:${stem}`
      if (!groups.has(key)) {
        const metadata = workflowFigureMetadata(path, artifact.label)
        groups.set(key, {
          id: key,
          ...metadata,
          source: 'Workflow',
          workflowId: run.workflow_id,
          runId: run.id,
          createdAt: run.finished_at || run.completed_at || run.created_at,
          previewPath: '',
          files: [],
        })
      }
      const figure = groups.get(key)
      figure.files.push({ path, extension: ext, size: artifact.size_bytes || 0 })
      if (!figure.previewPath && PREVIEW_EXTENSIONS.has(ext)) figure.previewPath = path
    }
  }
  return [...groups.values()]
}

export function collectCustomFigures(items) {
  return (items || [])
    .filter((item) => !item.is_dir && FIGURE_EXTENSIONS.has(extension(item.name)))
    .map((item) => {
      const path = `/plots/${item.name}`
      const ext = extension(path)
      return {
        id: `custom:${path}`,
        title: figureTitle(item.name),
        source: 'Plot studio',
        category: 'custom',
        categoryLabel: 'Your plots',
        categoryIcon: 'chart-no-axes-combined',
        sampleId: '',
        workflowId: '',
        runId: '',
        createdAt: item.mtime ? new Date(item.mtime * 1000).toISOString() : '',
        previewPath: PREVIEW_EXTENSIONS.has(ext) ? path : '',
        files: [{ path, extension: ext, size: item.size || 0 }],
      }
    })
}

export function sortFigures(figures) {
  return [...figures].sort((left, right) => (
    new Date(right.createdAt || 0).getTime() - new Date(left.createdAt || 0).getTime()
  ))
}
