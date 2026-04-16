import dagre from '@dagrejs/dagre'
import { Position } from '@vue-flow/core'

const APPAM_STAGE_COLORS = {
  orange: {
    accent: '#ef8d27',
    soft: 'rgba(239, 141, 39, 0.14)',
  },
  green: {
    accent: '#37a866',
    soft: 'rgba(55, 168, 102, 0.14)',
  },
  blue: {
    accent: '#2f6fed',
    soft: 'rgba(47, 111, 237, 0.14)',
  },
  neutral: {
    accent: '#6b7280',
    soft: 'rgba(107, 114, 128, 0.12)',
  },
}

const WORKFLOWS = {
  'appam-smk': {
    id: 'appam-smk',
    toolId: 'workflow-appam-smk',
    layoutMode: 'manual',
    title: 'APPAM-SMK Workflow',
    subtitle: 'Ancient metagenomics recovery and authentication',
    description:
      'Ancient metagenomics workflow from reads QC through damage-aware MAG reconstruction, taxonomic classification, and reporting.',
    outputRoot: 'workflow_runs/appam-smk',
    canvas: { width: 1520, height: 860 },
    outputs: [
      'workflow_runs/appam-smk/results/preprocess',
      'workflow_runs/appam-smk/results/megahit',
      'workflow_runs/appam-smk/results/pydamage',
      'workflow_runs/appam-smk/results/metawrap',
      'workflow_runs/appam-smk/results/gtdbtk',
    ],
    nodes: [
      {
        id: 'input-fastq',
        kind: 'input',
        title: 'FASTQ',
        subtitle: 'paired-end ancient reads',
        x: 44,
        y: 352,
        w: 132,
        h: 118,
        description: 'Input paired-end FASTQ files referenced by the APPAM-SMK sample manifest.',
      },
      {
        id: 'qc-trim',
        title: 'Adapter / QC',
        subtitle: 'read preprocessing',
        description: 'Initial read QC and trimming. APPAM-SMK currently runs AdapterRemoval or fastp; FastQC and MultiQC remain companion tools.',
        x: 242,
        y: 92,
        w: 302,
        h: 164,
        branch: 'orange',
        trackStatus: true,
        rules: ['fastp_preprocess', 'fastqc', 'adapter_removal', 'collapse_to_single_end'],
        tools: [
          { label: 'FastQC', tone: 'soft' },
          { label: 'MultiQC', tone: 'soft' },
          { label: 'AdapterRemoval', tone: 'orange' },
        ],
      },
      {
        id: 'adna-filter',
        title: 'aDNA Filtering',
        subtitle: 'read-level authenticity',
        description: 'Read-level authentication and host/environment filtering branch. These modules are currently available as tools and planned for tighter workflow integration.',
        x: 258,
        y: 352,
        w: 258,
        h: 156,
        branch: 'orange',
        optional: true,
        tools: [
          { label: 'bwa', tone: 'orange' },
          { label: 'PMDtools', tone: 'orange' },
          { label: 'bedtools', tone: 'orange' },
        ],
      },
      {
        id: 'read-taxonomy',
        title: 'Taxonomic Classification',
        subtitle: 'read-based profiling',
        description: 'Optional read-based taxonomic profiling and visualization branch for rapid sample inspection.',
        x: 258,
        y: 566,
        w: 258,
        h: 134,
        branch: 'orange',
        optional: true,
        tools: [
          { label: 'KrakenUniq', tone: 'orange' },
          { label: 'Krona', tone: 'orange' },
        ],
      },
      {
        id: 'read-report',
        kind: 'output',
        title: 'HTML / TSV',
        subtitle: 'read branch reports',
        x: 286,
        y: 784,
        w: 228,
        h: 110,
        description: 'Read-based branch reports and visual summaries.',
      },
      {
        id: 'assembly',
        title: 'Assembly',
        subtitle: 'de novo reconstruction',
        description: 'Assemble preprocessed reads into contigs. MEGAHIT is the tracked workflow rule; SPAdes remains available for comparison.',
        x: 642,
        y: 94,
        w: 282,
        h: 132,
        branch: 'green',
        trackStatus: true,
        rules: ['megahit'],
        tools: [
          { label: 'MEGAHIT', tone: 'green' },
          { label: 'SPAdes', tone: 'soft' },
        ],
      },
      {
        id: 'assembly-eval',
        title: 'Assembly Evaluation',
        subtitle: 'continuity and QC',
        description: 'Assembly continuity and quality summary. calN50 and QUAST are displayed as evaluation companions.',
        x: 690,
        y: 320,
        w: 198,
        h: 126,
        branch: 'green',
        optional: true,
        tools: [
          { label: 'calN50', tone: 'soft' },
          { label: 'QUAST', tone: 'soft' },
        ],
      },
      {
        id: 'alignment-validation',
        title: 'Alignment & aDNA Validation',
        subtitle: 'contig authentication',
        description: 'Map reads back to contigs, call variants if needed, and detect ancient damage signatures with PyDamage.',
        x: 1072,
        y: 82,
        w: 382,
        h: 182,
        branch: 'green',
        trackStatus: true,
        rules: ['bowtie2_index', 'bowtie2_align', 'index_bam', 'freebayes', 'bcftools', 'pydamage'],
        tools: [
          { label: 'Bowtie2', tone: 'soft' },
          { label: 'Samtools', tone: 'soft' },
          { label: 'FreeBayes', tone: 'soft' },
          { label: 'BCFtools', tone: 'soft' },
          { label: 'PyDamage', tone: 'green' },
        ],
      },
      {
        id: 'filter-contigs',
        title: 'Filter Contigs',
        subtitle: 'ancient vs modern split',
        description: 'Split contigs into ancient and modern partitions using PyDamage-derived authenticity thresholds.',
        x: 1110,
        y: 360,
        w: 320,
        h: 162,
        branch: 'green',
        trackStatus: true,
        rules: ['split_contigs_by_pydamage'],
        tools: [
          { label: 'SeqKit', tone: 'green' },
          { label: 'Ancient contigs', tone: 'soft' },
          { label: 'Modern contigs', tone: 'soft' },
        ],
      },
      {
        id: 'binning',
        title: 'Binning / Refinement / Evaluation',
        subtitle: 'MAG recovery',
        description: 'Recover candidate MAGs with multiple binning engines, refine them with metaWRAP, and assess quality with CheckM and GUNC.',
        x: 1020,
        y: 644,
        w: 492,
        h: 182,
        branch: 'green',
        trackStatus: true,
        rules: ['metawrap_binning', 'metawrap_bin_refinement', 'checkm', 'gunc'],
        tools: [
          { label: 'MetaBAT2', tone: 'soft' },
          { label: 'MaxBin2', tone: 'soft' },
          { label: 'CONCOCT', tone: 'soft' },
          { label: 'metaWRAP', tone: 'green' },
          { label: 'CheckM', tone: 'soft' },
          { label: 'GUNC', tone: 'soft' },
        ],
      },
      {
        id: 'taxonomy-annotation',
        title: 'Species / Genome Annotation',
        subtitle: 'classification and interpretation',
        description: 'Classify refined MAGs with GTDB-Tk and connect downstream annotation tools for proteins, pathways, ARGs, virulence factors, and BGCs.',
        x: 1608,
        y: 646,
        w: 294,
        h: 216,
        branch: 'green',
        trackStatus: true,
        rules: ['gtdbtk_classify'],
        tools: [
          { label: 'GTDB-Tk', tone: 'soft' },
          { label: 'PROKKA', tone: 'soft' },
          { label: 'eggNOG-mapper', tone: 'green' },
          { label: 'RGI', tone: 'green' },
          { label: 'ABRicate', tone: 'green' },
          { label: 'antiSMASH', tone: 'green' },
        ],
      },
      {
        id: 'mag-report',
        kind: 'output',
        title: 'HTML / TSV',
        subtitle: 'MAG reports',
        x: 1658,
        y: 914,
        w: 220,
        h: 112,
        description: 'Final metagenomics reports, tables, and workflow output bundles.',
      },
    ],
    edges: [
      { id: 'e1', from: 'input-fastq', to: 'qc-trim', color: 'orange', fromAnchor: 'right', toAnchor: 'left' },
      { id: 'e2', from: 'qc-trim', to: 'assembly', color: 'green', fromAnchor: 'right', toAnchor: 'left' },
      { id: 'e3', from: 'assembly', to: 'assembly-eval', color: 'green', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'e4', from: 'assembly', to: 'alignment-validation', color: 'green', fromAnchor: 'right', toAnchor: 'left' },
      { id: 'e5', from: 'alignment-validation', to: 'filter-contigs', color: 'green', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'e6', from: 'filter-contigs', to: 'binning', color: 'green', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'e7', from: 'binning', to: 'taxonomy-annotation', color: 'green', fromAnchor: 'right', toAnchor: 'left' },
      { id: 'e8', from: 'taxonomy-annotation', to: 'mag-report', color: 'green', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'e9', from: 'qc-trim', to: 'adna-filter', color: 'orange', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'e10', from: 'adna-filter', to: 'read-taxonomy', color: 'orange', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'e11', from: 'read-taxonomy', to: 'read-report', color: 'orange', fromAnchor: 'bottom', toAnchor: 'top' },
    ],
  },
  'appam-paleoproteomics': {
    id: 'appam-paleoproteomics',
    toolId: 'workflow-appam-paleoproteomics',
    layoutMode: 'manual',
    title: 'APPAM Paleoproteomics Workflow',
    subtitle: 'Raw conversion, mzML standardization, and MaxQuant search',
    description:
      'Snakemake workflow for Thermo RAW and Bruker .d conversion, mzML standardization, mqpar generation, and MaxQuant batch search.',
    outputRoot: 'workflow_runs/appam-paleoproteomics',
    canvas: { width: 1640, height: 660 },
    outputs: [
      'workflow_runs/appam-paleoproteomics/results/mzml',
      'workflow_runs/appam-paleoproteomics/results/maxquant',
      'workflow_runs/appam-paleoproteomics/generated',
    ],
    nodes: [
      {
        id: 'input-raw',
        kind: 'input',
        title: '.RAW / .d',
        subtitle: 'vendor raw data',
        x: 420,
        y: 24,
        w: 140,
        h: 112,
        description: 'Thermo RAW files and Bruker .d folders listed in the workflow sample sheet.',
      },
      {
        id: 'thermo-convert',
        title: 'Thermo Conversion',
        subtitle: 'RAW -> mzML',
        description: 'Convert Thermo RAW files to initial mzML using ThermoRawFileParser.',
        x: 530,
        y: 214,
        w: 320,
        h: 144,
        branch: 'blue',
        trackStatus: true,
        rules: ['thermo_raw_to_mzml'],
        tools: [
          { label: 'ThermoRawFileParser', tone: 'blue' },
          { label: 'mzML', tone: 'soft' },
        ],
      },
      {
        id: 'bruker-convert',
        title: 'Bruker Conversion',
        subtitle: '.d -> mzML',
        description: 'Convert Bruker timsTOF datasets using timsconvert before standardization.',
        x: 120,
        y: 214,
        w: 320,
        h: 144,
        branch: 'blue',
        trackStatus: true,
        rules: ['bruker_d_to_mzml'],
        tools: [
          { label: 'timsconvert', tone: 'blue' },
          { label: 'mzML', tone: 'soft' },
        ],
      },
      {
        id: 'mzml-standardize',
        title: 'mzML Standardization',
        subtitle: 'OpenMS normalization',
        description: 'Convert intermediate mzML files to a final MaxQuant-compatible mzML set using OpenMS FileConverter.',
        x: 320,
        y: 458,
        w: 344,
        h: 162,
        branch: 'green',
        trackStatus: true,
        rules: ['finalize_raw_mzml', 'finalize_bruker_mzml'],
        tools: [
          { label: 'OpenMS FileConverter', tone: 'green' },
          { label: 'final mzML', tone: 'soft' },
        ],
      },
      {
        id: 'mqpar',
        title: 'mqpar Generation',
        subtitle: 'templated search config',
        description: 'Render a run-specific mqpar.xml from the sample sheet and workflow template.',
        x: 286,
        y: 704,
        w: 270,
        h: 132,
        branch: 'green',
        trackStatus: true,
        rules: ['render_mqpar'],
        tools: [
          { label: 'render_mqpar', tone: 'green' },
          { label: 'mqpar.xml', tone: 'soft' },
        ],
      },
      {
        id: 'maxquant',
        title: 'MaxQuant Search',
        subtitle: 'batch peptide/protein ID',
        description: 'Run MaxQuantCmd on the generated mqpar.xml to produce proteinGroups and other standard search outputs.',
        x: 616,
        y: 686,
        w: 300,
        h: 180,
        branch: 'green',
        trackStatus: true,
        rules: ['run_maxquant'],
        tools: [
          { label: 'dotnet', tone: 'soft' },
          { label: 'MaxQuant', tone: 'green' },
          { label: 'proteinGroups.txt', tone: 'soft' },
        ],
      },
      {
        id: 'proteomics-report',
        kind: 'output',
        title: 'mzML / TXT',
        subtitle: 'search outputs',
        x: 494,
        y: 962,
        w: 190,
        h: 114,
        description: 'Standardized mzML files, mqpar.xml, proteinGroups.txt, and MaxQuant result tables.',
      },
    ],
    edges: [
      { id: 'p1', from: 'input-raw', to: 'thermo-convert', color: 'blue', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'p2', from: 'input-raw', to: 'bruker-convert', color: 'blue', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'p3', from: 'thermo-convert', to: 'mzml-standardize', color: 'green', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'p4', from: 'bruker-convert', to: 'mzml-standardize', color: 'green', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'p5', from: 'mzml-standardize', to: 'mqpar', color: 'green', fromAnchor: 'bottom', toAnchor: 'top' },
      { id: 'p6', from: 'mqpar', to: 'maxquant', color: 'green', fromAnchor: 'right', toAnchor: 'left' },
      { id: 'p7', from: 'maxquant', to: 'proteomics-report', color: 'green', fromAnchor: 'bottom', toAnchor: 'top' },
    ],
  },
}

const WORKFLOW_LAYOUTS = {
  'appam-smk': {
    rankdir: 'LR',
    ranksep: 190,
    nodesep: 74,
    marginx: 36,
    marginy: 36,
  },
  'appam-paleoproteomics': {
    rankdir: 'TB',
    ranksep: 92,
    nodesep: 56,
    marginx: 36,
    marginy: 36,
  },
}

function anchorPoint(node, anchor = 'right') {
  if (anchor === 'left') {
    return { x: node.x, y: node.y + node.h / 2 }
  }
  if (anchor === 'top') {
    return { x: node.x + node.w / 2, y: node.y }
  }
  if (anchor === 'bottom') {
    return { x: node.x + node.w / 2, y: node.y + node.h }
  }
  return { x: node.x + node.w, y: node.y + node.h / 2 }
}

function buildCurvedPath(start, end) {
  const isVertical = Math.abs(start.x - end.x) < Math.abs(start.y - end.y)
  if (isVertical) {
    const dy = Math.max(60, Math.abs(end.y - start.y) * 0.45)
    return `M ${start.x} ${start.y} C ${start.x} ${start.y + dy}, ${end.x} ${end.y - dy}, ${end.x} ${end.y}`
  }
  const dx = Math.max(70, Math.abs(end.x - start.x) * 0.42)
  return `M ${start.x} ${start.y} C ${start.x + dx} ${start.y}, ${end.x - dx} ${end.y}, ${end.x} ${end.y}`
}

function collectRuleMentions(logText = '') {
  const patterns = [
    /(?:^|\n)(?:local)?rule\s+([A-Za-z0-9_:-]+):/g,
    /(?:^|\n)checkpoint\s+([A-Za-z0-9_:-]+):/g,
  ]
  const found = []
  for (const pattern of patterns) {
    let match
    while ((match = pattern.exec(logText)) !== null) {
      found.push(match[1])
    }
  }
  return found
}

function statusFromJob(status) {
  if (status === 'running') return 'running'
  if (status === 'queued') return 'queued'
  if (status === 'completed') return 'completed'
  if (status === 'failed' || status === 'error') return 'failed'
  if (status === 'canceled') return 'canceled'
  return 'pending'
}

function estimateNodeSize(node) {
  const width = node.w || (node.kind === 'input' || node.kind === 'output' ? 164 : 260)
  const titleLines = node.title.length > 20 ? 2 : 1
  const subtitleLines = node.subtitle.length > 24 ? 2 : 1
  const chipRows = node.tools?.length
    ? Math.max(1, Math.ceil(node.tools.length / (width >= 300 ? 3 : width >= 220 ? 2 : 1)))
    : 0

  let minHeight = node.h || 108

  if (node.kind === 'input' || node.kind === 'output') {
    minHeight = Math.max(minHeight, 108)
  } else {
    minHeight = Math.max(
      minHeight,
      82 + (titleLines * 18) + (subtitleLines * 18) + (chipRows * 34) + (node.optional ? 18 : 14),
    )
  }

  return { width, height: minHeight }
}

function inferAnchor(fromNode, toNode, kind = 'source') {
  const fromCenterX = fromNode.x + (fromNode.w || 0) / 2
  const fromCenterY = fromNode.y + (fromNode.h || 0) / 2
  const toCenterX = toNode.x + (toNode.w || 0) / 2
  const toCenterY = toNode.y + (toNode.h || 0) / 2

  const dx = toCenterX - fromCenterX
  const dy = toCenterY - fromCenterY

  if (Math.abs(dx) >= Math.abs(dy)) {
    if (kind === 'source') return dx >= 0 ? 'right' : 'left'
    return dx >= 0 ? 'left' : 'right'
  }

  if (kind === 'source') return dy >= 0 ? 'bottom' : 'top'
  return dy >= 0 ? 'top' : 'bottom'
}

export function stageLabelFromState(state = 'pending') {
  const labels = {
    pending: 'Pending',
    queued: 'Queued',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    canceled: 'Canceled',
    optional: 'Optional',
    idle: 'Idle',
  }
  return labels[state] || 'Pending'
}

export function getWorkflowDefinition(workflowId) {
  return WORKFLOWS[workflowId] || null
}

export function getWorkflowDefinitionByToolId(toolId) {
  return Object.values(WORKFLOWS).find((workflow) => workflow.toolId === toolId) || null
}

export function buildWorkflowGraph(workflow) {
  const nodesById = Object.fromEntries(workflow.nodes.map((node) => [node.id, node]))
  return workflow.edges.map((edge) => {
    const from = nodesById[edge.from]
    const to = nodesById[edge.to]
    const path = buildCurvedPath(
      anchorPoint(from, edge.fromAnchor),
      anchorPoint(to, edge.toAnchor || 'left'),
    )
    return {
      ...edge,
      path,
      colorToken: APPAM_STAGE_COLORS[edge.color || 'neutral'],
    }
  })
}

export function buildWorkflowFlowElements(workflow, nodeStates = {}, selectedNodeId = null) {
  const layoutConfig = WORKFLOW_LAYOUTS[workflow.id] || {
    rankdir: 'LR',
    ranksep: 180,
    nodesep: 68,
    marginx: 32,
    marginy: 32,
  }

  const sizedNodes = workflow.nodes.map((node) => ({
    ...node,
    ...estimateNodeSize(node),
  }))

  let positionedNodes = sizedNodes
  let sourcePosition = Position.Right
  let targetPosition = Position.Left

  if (workflow.layoutMode !== 'manual') {
    const graph = new dagre.graphlib.Graph()
    graph.setDefaultEdgeLabel(() => ({}))
    graph.setGraph({
      rankdir: layoutConfig.rankdir,
      ranksep: layoutConfig.ranksep,
      nodesep: layoutConfig.nodesep,
      marginx: layoutConfig.marginx,
      marginy: layoutConfig.marginy,
      ranker: 'tight-tree',
    })

    sizedNodes.forEach((node) => {
      graph.setNode(node.id, {
        width: node.width,
        height: node.height,
      })
    })

    workflow.edges.forEach((edge) => {
      graph.setEdge(edge.from, edge.to, {
        weight: edge.color === 'green' ? 3 : 1,
      })
    })

    dagre.layout(graph)

    positionedNodes = sizedNodes.map((node) => {
      const position = graph.node(node.id) || {
        x: node.x + node.width / 2,
        y: node.y + node.height / 2,
      }
      return {
        ...node,
        x: position.x - node.width / 2,
        y: position.y - node.height / 2,
      }
    })

    const isVertical = layoutConfig.rankdir === 'TB' || layoutConfig.rankdir === 'BT'
    sourcePosition = isVertical ? Position.Bottom : Position.Right
    targetPosition = isVertical ? Position.Top : Position.Left
  }

  const nodesById = Object.fromEntries(positionedNodes.map((node) => [node.id, node]))

  const nodes = positionedNodes.map((node) => {
    const state = nodeStates[node.id] || (node.optional
      ? 'optional'
      : node.kind === 'input' || node.kind === 'output'
        ? 'idle'
        : 'pending')

    return {
      id: node.id,
      type: 'workflow-stage',
      position: {
        x: node.x,
        y: node.y,
      },
      sourcePosition,
      targetPosition,
      draggable: false,
      connectable: false,
      selectable: false,
      data: {
        ...node,
        selected: selectedNodeId === node.id,
        state,
        stateLabel: stageLabelFromState(state),
        colorToken: APPAM_STAGE_COLORS[node.branch || 'neutral'],
      },
      style: {
        width: `${node.width}px`,
        height: `${node.height}px`,
      },
    }
  })

  const edges = workflow.edges.map((edge) => {
    const fromNode = nodesById[edge.from]
    const toNode = nodesById[edge.to]
    const sourceAnchor = edge.fromAnchor || inferAnchor(fromNode, toNode, 'source')
    const targetAnchor = edge.toAnchor || inferAnchor(fromNode, toNode, 'target')

    return {
      id: edge.id,
      source: edge.from,
      target: edge.to,
      sourceHandle: `source-${sourceAnchor}`,
      targetHandle: `target-${targetAnchor}`,
      type: 'workflow-status',
      selectable: false,
      focusable: false,
      data: {
        state: edgeState(edge, nodeStates),
        color: edge.color || 'neutral',
        colorToken: APPAM_STAGE_COLORS[edge.color || 'neutral'],
        routePoints: edge.via || [],
      },
    }
  })

  const bounds = nodes.reduce((acc, node) => {
    const width = Number.parseFloat(node.style.width) || 0
    const height = Number.parseFloat(node.style.height) || 0
    return {
      width: Math.max(acc.width, node.position.x + width),
      height: Math.max(acc.height, node.position.y + height),
    }
  }, { width: 0, height: 0 })

  return {
    nodes,
    edges,
    bounds: {
      width: bounds.width + layoutConfig.marginx,
      height: bounds.height + layoutConfig.marginy,
    },
  }
}

export function initWorkflowFormValues(parameters = []) {
  const initialValues = {}
  parameters.forEach((param) => {
    if (param.type === 'file' || param.type === 'directory') {
      initialValues[param.name] = param.multiple ? [] : ''
      return
    }
    if (param.type === 'flag') {
      initialValues[param.name] = Boolean(param.default)
      return
    }
    if (param.options?.length) {
      initialValues[param.name] = param.default && param.options.includes(param.default)
        ? param.default
        : param.options[0]
      return
    }
    initialValues[param.name] = param.default ?? ''
  })
  return initialValues
}

export function inferWorkflowRuntimeState(workflow, job, logText = '') {
  const stateByNode = {}
  workflow.nodes.forEach((node) => {
    if (node.optional) {
      stateByNode[node.id] = 'optional'
    } else if (node.kind === 'input' || node.kind === 'output') {
      stateByNode[node.id] = 'idle'
    } else {
      stateByNode[node.id] = 'pending'
    }
  })

  const trackedNodes = workflow.nodes.filter((node) => node.trackStatus)
  const mentions = collectRuleMentions(logText)
  const seenStageIds = []
  let currentRule = null

  for (const ruleName of mentions) {
    const matchedNode = trackedNodes.find((node) => node.rules?.includes(ruleName))
    if (!matchedNode) continue
    currentRule = ruleName
    if (seenStageIds.at(-1) !== matchedNode.id) {
      seenStageIds.push(matchedNode.id)
    }
  }

  const jobStatus = job?.status || 'not_found'
  let currentStageId = seenStageIds.at(-1) || trackedNodes[0]?.id || null

  if (jobStatus === 'completed') {
    trackedNodes.forEach((node) => {
      stateByNode[node.id] = 'completed'
    })
  } else if (seenStageIds.length > 0) {
    seenStageIds.slice(0, -1).forEach((nodeId) => {
      stateByNode[nodeId] = 'completed'
    })
    if (currentStageId) {
      stateByNode[currentStageId] = statusFromJob(jobStatus)
    }
  } else if (jobStatus === 'queued' && trackedNodes[0]) {
    stateByNode[trackedNodes[0].id] = 'queued'
  } else if ((jobStatus === 'running' || jobStatus === 'failed' || jobStatus === 'canceled') && trackedNodes[0]) {
    stateByNode[trackedNodes[0].id] = statusFromJob(jobStatus)
  }

  if (jobStatus !== 'not_found') {
    const firstNode = workflow.nodes[0]
    const lastNode = workflow.nodes.at(-1)
    if (firstNode) stateByNode[firstNode.id] = 'completed'
    if (jobStatus === 'completed' && lastNode) stateByNode[lastNode.id] = 'completed'
  }

  const completedCount = trackedNodes.filter((node) => stateByNode[node.id] === 'completed').length
  const progress = {
    completed: completedCount,
    total: trackedNodes.length,
  }

  return {
    stateByNode,
    currentStageId,
    currentRule,
    progress,
  }
}

export function runtimeStateFromWorkflowRun(workflow, workflowRun) {
  const stateByNode = {}
  workflow.nodes.forEach((node) => {
    if (node.optional) {
      stateByNode[node.id] = 'optional'
    } else if (node.kind === 'input' || node.kind === 'output') {
      stateByNode[node.id] = 'idle'
    } else {
      stateByNode[node.id] = 'pending'
    }
  })

  if (!workflowRun) {
    return {
      stateByNode,
      currentStageId: null,
      currentRule: null,
      progress: {
        completed: 0,
        total: workflow.nodes.filter((node) => node.trackStatus).length,
      },
    }
  }

  const trackedNodes = workflow.nodes.filter((node) => node.trackStatus)
  const stageStates = new Map((workflowRun.stage_states || []).map((stage) => [stage.stage_id, stage]))

  for (const node of trackedNodes) {
    const stageState = stageStates.get(node.id)
    if (stageState?.status) {
      stateByNode[node.id] = stageState.status
    }
  }

  if (workflowRun.status === 'completed') {
    for (const node of trackedNodes) {
      stateByNode[node.id] = 'completed'
    }
  }

  if (workflow.nodes[0]) {
    stateByNode[workflow.nodes[0].id] = workflowRun.status === 'not_found' ? 'idle' : 'completed'
  }
  if (workflowRun.status === 'completed' && workflow.nodes.at(-1)) {
    stateByNode[workflow.nodes.at(-1).id] = 'completed'
  }

  const progress = {
    completed: trackedNodes.filter((node) => stateByNode[node.id] === 'completed').length,
    total: trackedNodes.length,
  }

  return {
    stateByNode,
    currentStageId: workflowRun.current_stage_id || null,
    currentRule: workflowRun.current_rule || null,
    progress,
  }
}

export function edgeState(edge, nodeStates = {}) {
  const fromState = nodeStates[edge.from]
  const toState = nodeStates[edge.to]
  if (toState === 'failed' || fromState === 'failed') return 'failed'
  if (toState === 'canceled' || fromState === 'canceled') return 'canceled'
  if (fromState === 'completed' && toState === 'completed') return 'completed'
  if (toState === 'running' || fromState === 'running' || toState === 'queued') return 'running'
  if (fromState === 'completed' && (toState === 'pending' || toState === 'optional')) return 'completed'
  return 'pending'
}

export { APPAM_STAGE_COLORS }
