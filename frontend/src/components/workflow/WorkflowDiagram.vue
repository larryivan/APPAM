<template>
  <div ref="diagramRef" class="workflow-diagram">
    <VueFlow
      :id="flowId"
      :nodes="flowElements.nodes"
      :edges="flowElements.edges"
      :node-types="nodeTypes"
      :edge-types="edgeTypes"
      :nodes-draggable="false"
      :nodes-connectable="false"
      :elements-selectable="false"
      :zoom-on-double-click="false"
      :pan-on-drag="true"
      :fit-view-on-init="true"
      :min-zoom="0.12"
      :max-zoom="1.2"
      class="workflow-flow"
      @node-click="handleNodeClick"
      @pane-ready="handlePaneReady"
    >
      <Background variant="dots" :gap="28" :size="1.2" color="rgba(148, 163, 184, 0.14)" />
      <Controls position="bottom-left" class="workflow-controls" />
    </VueFlow>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useDebounceFn, useResizeObserver } from '@vueuse/core'
import { VueFlow, useNodesInitialized, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import WorkflowStageNode from './WorkflowStageNode.vue'
import WorkflowStatusEdge from './WorkflowStatusEdge.vue'
import { buildWorkflowFlowElements } from '@/lib/workflowDefinitions'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

const props = defineProps({
  workflow: {
    type: Object,
    required: true,
  },
  nodeStates: {
    type: Object,
    default: () => ({}),
  },
  selectedNodeId: {
    type: String,
    default: null,
  },
})

const emit = defineEmits(['select-node'])

const flowId = 'appam-workflow-flow'
const diagramRef = ref(null)

const nodeTypes = {
  'workflow-stage': WorkflowStageNode,
}

const edgeTypes = {
  'workflow-status': WorkflowStatusEdge,
}

const flowElements = computed(() => {
  if (!props.workflow) {
    return { nodes: [], edges: [], bounds: { width: 0, height: 0 } }
  }
  return buildWorkflowFlowElements(props.workflow, props.nodeStates, props.selectedNodeId)
})

const { fitView } = useVueFlow({ id: flowId })
const nodesInitialized = useNodesInitialized()

const fitDiagram = useDebounceFn(async () => {
  await nextTick()
  await fitView({
    padding: 0.3,
    duration: 260,
    includeHiddenNodes: true,
    maxZoom: 0.92,
  })
}, 80)

const handleNodeClick = ({ node }) => {
  emit('select-node', node.id)
}

const handlePaneReady = () => {
  fitDiagram()
}

watch(
  () => props.workflow?.id,
  () => {
    fitDiagram()
  },
  { immediate: true },
)

watch(
  () => nodesInitialized.value,
  (ready) => {
    if (ready) {
      fitDiagram()
    }
  },
  { immediate: true },
)

watch(
  () => flowElements.value.nodes.length,
  () => {
    fitDiagram()
  },
)

useResizeObserver(diagramRef, () => {
  fitDiagram()
})
</script>

<style scoped>
.workflow-diagram {
  height: 680px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--surface-1);
  box-shadow: inset 0 0 0 1px var(--border-color-light);
}

.workflow-flow {
  width: 100%;
  height: 100%;
  background: transparent;
}

:deep(.vue-flow__pane) {
  cursor: grab;
}

:deep(.vue-flow__pane.dragging) {
  cursor: grabbing;
}

:deep(.vue-flow__controls) {
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  overflow: hidden;
}

:deep(.vue-flow__viewport) {
  transition: transform 0.24s ease;
}

:deep(.vue-flow__edge-path) {
  vector-effect: non-scaling-stroke;
}

:deep(.vue-flow__controls-button) {
  width: 32px;
  height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.94);
  color: #475569;
}

:deep(.vue-flow__controls-button:hover) {
  background: #ffffff;
  color: #0f172a;
}

@media (max-width: 900px) {
  .workflow-diagram {
    height: 540px;
    border-radius: 20px;
  }
}
</style>
