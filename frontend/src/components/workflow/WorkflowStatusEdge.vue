<template>
  <g class="workflow-edge-layer">
    <path :d="edgePath" class="edge-main" :class="edgeClasses" :style="edgeVars" />
    <path :d="edgePath" class="edge-flow" :class="edgeClasses" :style="edgeVars" />

    <circle
      v-for="packet in packets"
      :key="packet.key"
      class="flow-packet"
      :class="edgeClasses"
      :style="edgeVars"
      :r="packet.radius"
    >
      <animateMotion
        :dur="packet.duration"
        :begin="packet.begin"
        repeatCount="indefinite"
        rotate="auto"
        :path="edgePath"
      />
    </circle>
  </g>
</template>

<script setup>
import { computed } from 'vue'
import { getSmoothStepPath } from '@vue-flow/core'

const props = defineProps({
  sourceX: {
    type: Number,
    required: true,
  },
  sourceY: {
    type: Number,
    required: true,
  },
  targetX: {
    type: Number,
    required: true,
  },
  targetY: {
    type: Number,
    required: true,
  },
  sourcePosition: {
    type: String,
    required: true,
  },
  targetPosition: {
    type: String,
    required: true,
  },
  data: {
    type: Object,
    default: () => ({}),
  },
})

function buildRoundedPath(points, radius = 18) {
  if (!points.length) return ''
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`

  let d = `M ${points[0].x} ${points[0].y}`

  for (let i = 1; i < points.length; i += 1) {
    const prev = points[i - 1]
    const curr = points[i]
    const next = points[i + 1]

    if (!next) {
      d += ` L ${curr.x} ${curr.y}`
      continue
    }

    const inDx = curr.x - prev.x
    const inDy = curr.y - prev.y
    const outDx = next.x - curr.x
    const outDy = next.y - curr.y
    const inLen = Math.hypot(inDx, inDy)
    const outLen = Math.hypot(outDx, outDy)

    if (!inLen || !outLen) {
      d += ` L ${curr.x} ${curr.y}`
      continue
    }

    const corner = Math.min(radius, inLen / 2, outLen / 2)
    const cornerStart = {
      x: curr.x - (inDx / inLen) * corner,
      y: curr.y - (inDy / inLen) * corner,
    }
    const cornerEnd = {
      x: curr.x + (outDx / outLen) * corner,
      y: curr.y + (outDy / outLen) * corner,
    }

    d += ` L ${cornerStart.x} ${cornerStart.y}`
    d += ` Q ${curr.x} ${curr.y} ${cornerEnd.x} ${cornerEnd.y}`
  }

  return d
}

const edgePath = computed(() => {
  const routePoints = Array.isArray(props.data?.routePoints) ? props.data.routePoints : []
  if (routePoints.length) {
    return buildRoundedPath(
      [
        { x: props.sourceX, y: props.sourceY },
        ...routePoints,
        { x: props.targetX, y: props.targetY },
      ],
      18,
    )
  }

  return getSmoothStepPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    targetX: props.targetX,
    targetY: props.targetY,
    sourcePosition: props.sourcePosition,
    targetPosition: props.targetPosition,
    borderRadius: 20,
  })[0]
})

const edgeClasses = computed(() => [
  'workflow-status-edge',
  `state-${props.data?.state || 'pending'}`,
])

const edgeVars = computed(() => ({
  '--edge-color': props.data?.colorToken?.accent || '#94a3b8',
}))

const packets = computed(() => {
  const state = props.data?.state || 'pending'
  if (state === 'optional' || state === 'failed' || state === 'canceled' || state === 'pending' || state === 'idle') {
    return []
  }

  if (state === 'running') {
    return [
      { key: 'a', begin: '0s', duration: '1.45s', radius: 4.2 },
      { key: 'b', begin: '0.48s', duration: '1.9s', radius: 3.5 },
      { key: 'c', begin: '0.96s', duration: '2.35s', radius: 3.0 },
    ]
  }

  if (state === 'queued') {
    return [
      { key: 'a', begin: '0s', duration: '2.4s', radius: 3.0 },
      { key: 'b', begin: '1.1s', duration: '2.8s', radius: 2.6 },
    ]
  }

  return [
    { key: 'a', begin: '0s', duration: '3.8s', radius: 2.6 },
  ]
})
</script>

<style scoped>
.edge-main {
  stroke: var(--edge-color);
  stroke-width: 3.6px;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
  opacity: 0.22;
}

.edge-main.state-completed {
  opacity: 0.72;
}

.edge-main.state-running {
  opacity: 0.58;
}

.edge-main.state-queued {
  opacity: 0.56;
}

.edge-main.state-pending,
.edge-main.state-idle,
.edge-main.state-optional {
  stroke: rgba(148, 163, 184, 0.74);
  opacity: 0.4;
}

.edge-main.state-failed,
.edge-main.state-canceled {
  stroke: #dc2626;
  opacity: 0.92;
}

.edge-flow {
  stroke: var(--edge-color);
  stroke-width: 2.4px;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
  stroke-dasharray: 18 16;
  opacity: 0;
  animation: none;
}

.edge-flow.state-running {
  opacity: 0.94;
  stroke-width: 3px;
  stroke-dasharray: 22 12;
  animation: flow 1.25s linear infinite;
  filter: drop-shadow(0 0 10px color-mix(in srgb, var(--edge-color) 34%, transparent));
}

.edge-flow.state-completed {
  opacity: 0.34;
  animation: flow 3.2s linear infinite;
}

.edge-flow.state-queued {
  opacity: 0.64;
  stroke-dasharray: 16 14;
  animation: flow 2.15s linear infinite;
}

.edge-flow.state-pending,
.edge-flow.state-idle,
.edge-flow.state-optional {
  opacity: 0;
}

.edge-flow.state-failed,
.edge-flow.state-canceled {
  stroke: #dc2626;
  opacity: 0.18;
}

.flow-packet {
  fill: var(--edge-color);
  opacity: 0.24;
  pointer-events: none;
}

.flow-packet.state-running {
  opacity: 0.96;
  filter: drop-shadow(0 0 8px color-mix(in srgb, var(--edge-color) 42%, transparent));
}

.flow-packet.state-completed {
  opacity: 0.42;
}

.flow-packet.state-queued {
  opacity: 0.72;
}

.flow-packet.state-pending,
.flow-packet.state-idle,
.flow-packet.state-optional {
  opacity: 0;
  fill: rgba(148, 163, 184, 0.88);
}

.flow-packet.state-failed,
.flow-packet.state-canceled {
  stroke: #dc2626;
  fill: #dc2626;
  opacity: 0.24;
}

@keyframes flow {
  to {
    stroke-dashoffset: -52;
  }
}

@media (prefers-reduced-motion: reduce) {
  .edge-flow,
  .flow-packet {
    animation: none !important;
  }
}
</style>
