<template>
  <div class="stage-node" :class="nodeClasses" :style="nodeVars">
    <Handle id="target-left" type="target" position="left" class="stage-handle" />
    <Handle id="target-right" type="target" position="right" class="stage-handle" />
    <Handle id="target-top" type="target" position="top" class="stage-handle" />
    <Handle id="target-bottom" type="target" position="bottom" class="stage-handle" />
    <Handle id="source-left" type="source" position="left" class="stage-handle" />
    <Handle id="source-right" type="source" position="right" class="stage-handle" />
    <Handle id="source-top" type="source" position="top" class="stage-handle" />
    <Handle id="source-bottom" type="source" position="bottom" class="stage-handle" />

    <div class="stage-status-dot"></div>

    <div v-if="data.kind === 'input' || data.kind === 'output'" class="stage-file-mark">
      {{ data.kind === 'input' ? 'IN' : 'OUT' }}
    </div>

    <div class="stage-head">
      <h3>{{ data.title }}</h3>
      <p>{{ data.subtitle }}</p>
    </div>

    <div v-if="data.tools?.length" class="stage-chips">
      <span
        v-for="tool in data.tools"
        :key="tool.label"
        class="stage-chip"
        :class="tool.tone || 'soft'"
      >
        {{ tool.label }}
      </span>
    </div>

    <div class="stage-note">
      {{ data.optional ? 'Optional branch' : data.stateLabel }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle } from '@vue-flow/core'

const props = defineProps({
  data: {
    type: Object,
    required: true,
  },
  sourcePosition: {
    type: String,
    default: 'right',
  },
  targetPosition: {
    type: String,
    default: 'left',
  },
})

const nodeClasses = computed(() => [
  `kind-${props.data.kind || 'stage'}`,
  `branch-${props.data.branch || 'neutral'}`,
  `state-${props.data.state || 'pending'}`,
  { selected: props.data.selected, optional: props.data.optional },
])

const nodeVars = computed(() => ({
  '--stage-accent': props.data.colorToken?.accent || '#64748b',
  '--stage-soft': props.data.colorToken?.soft || 'rgba(148, 163, 184, 0.14)',
}))
</script>

<style scoped>
.stage-node {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  height: 100%;
  padding: 14px 14px 12px;
  border-radius: 22px;
  border: 1.5px solid rgba(15, 23, 42, 0.12);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
  color: #0f172a;
  text-align: left;
  transition: box-shadow 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
  box-sizing: border-box;
}

.stage-node.selected {
  border-color: rgba(47, 111, 237, 0.46);
  box-shadow: 0 18px 34px rgba(47, 111, 237, 0.14);
}

.stage-node.optional {
  border-style: dashed;
  background: rgba(255, 255, 255, 0.82);
}

.stage-node.kind-input,
.stage-node.kind-output {
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 24px 12px 12px;
}

.stage-node.branch-orange {
  box-shadow: 0 12px 28px rgba(239, 141, 39, 0.1);
}

.stage-node.branch-green {
  box-shadow: 0 12px 28px rgba(55, 168, 102, 0.1);
}

.stage-node.branch-blue {
  box-shadow: 0 12px 28px rgba(47, 111, 237, 0.1);
}

.stage-status-dot {
  position: absolute;
  top: 14px;
  left: 14px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #cbd5e1;
}

.stage-node.kind-input .stage-status-dot,
.stage-node.kind-output .stage-status-dot {
  top: 16px;
  left: 16px;
}

.stage-node.state-completed .stage-status-dot {
  background: #37a866;
}

.stage-node.state-running .stage-status-dot {
  background: #2f6fed;
  box-shadow: 0 0 0 8px rgba(47, 111, 237, 0.16);
  animation: pulse 1.8s ease-in-out infinite;
}

.stage-node.state-queued .stage-status-dot {
  background: #ef8d27;
}

.stage-node.state-failed .stage-status-dot,
.stage-node.state-canceled .stage-status-dot {
  background: #dc2626;
}

.stage-node.state-optional .stage-status-dot {
  background: #94a3b8;
}

.stage-file-mark {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 38px;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  background: #0f172a;
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.16);
}

.stage-head {
  padding-left: 18px;
}

.stage-node.kind-input .stage-head,
.stage-node.kind-output .stage-head {
  padding-left: 0;
  margin-top: 8px;
  width: 100%;
}

.stage-node.kind-input .stage-head h3,
.stage-node.kind-output .stage-head h3 {
  padding-right: 0;
  font-size: 0.96rem;
}

.stage-node.kind-input .stage-head p,
.stage-node.kind-output .stage-head p {
  max-width: 12ch;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.34;
}

.stage-head h3 {
  margin: 0;
  font-size: 1rem;
  line-height: 1.16;
  padding-right: 8px;
  letter-spacing: -0.02em;
  word-break: break-word;
}

.stage-head p {
  margin: 6px 0 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.4;
}

.stage-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding-left: 18px;
  width: 100%;
}

.stage-node.kind-input .stage-chips,
.stage-node.kind-output .stage-chips {
  padding-left: 0;
  justify-content: center;
}

.stage-chip {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  max-width: 100%;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  background: #fff;
  font-size: 0.76rem;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stage-chip.orange {
  background: rgba(239, 141, 39, 0.12);
  color: #b45309;
}

.stage-chip.green {
  background: rgba(55, 168, 102, 0.14);
  color: #166534;
}

.stage-chip.blue {
  background: rgba(47, 111, 237, 0.12);
  color: #1d4ed8;
}

.stage-chip.soft {
  background: rgba(255, 255, 255, 0.74);
  color: #475569;
}

.stage-note {
  margin-top: auto;
  font-size: 0.75rem;
  font-weight: 700;
  color: #64748b;
  padding-left: 18px;
}

.stage-node.kind-input .stage-note,
.stage-node.kind-output .stage-note {
  padding-left: 0;
  margin-top: 4px;
}

.stage-handle {
  width: 8px;
  height: 8px;
  opacity: 0;
  border: none;
  pointer-events: none;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.08);
    opacity: 0.72;
  }
}
</style>
