<template>
  <Teleport to="body">
    <Transition name="side-panel">
      <div v-if="open" class="side-panel-layer" @mousedown.self="$emit('close')">
        <aside
          ref="panel"
          class="side-panel"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="resolvedTitleId"
          tabindex="-1"
        >
          <header class="side-panel__header">
            <div>
              <p v-if="eyebrow">{{ eyebrow }}</p>
              <h2 :id="resolvedTitleId">{{ title }}</h2>
              <slot name="subtitle" />
            </div>
            <button type="button" title="Close" aria-label="Close" @click="$emit('close')">
              <Icon name="x" :size="17" />
            </button>
          </header>

          <div class="side-panel__body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="side-panel__footer">
            <slot name="footer" />
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

import Icon from './Icon.vue'
import { nextOverlayId, useOverlay } from '@/lib/overlay.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  eyebrow: { type: String, default: '' },
  // Defaults to a unique id: a fixed one collides when two panels are mounted.
  titleId: { type: String, default: '' },
})

const emit = defineEmits(['close'])

const panel = ref(null)
const generatedTitleId = nextOverlayId('side-panel-title')
const resolvedTitleId = props.titleId || generatedTitleId

useOverlay(() => props.open, { onClose: () => emit('close'), panelRef: panel })
</script>

<style scoped>
.side-panel-layer {
  position: fixed;
  z-index: var(--z-modal);
  inset: var(--header-height) 0 0;
  display: flex;
  justify-content: flex-end;
  background: rgb(21 29 41 / 0.32);
}

.side-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  width: min(500px, 100%);
  min-width: 0;
  height: 100%;
  border-left: 1px solid var(--border-color);
  background: var(--surface-1);
  box-shadow: -12px 0 36px rgb(21 29 41 / 0.12);
}

.side-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  min-height: 76px;
  padding: 17px 20px;
  border-bottom: 1px solid var(--border-color-light);
}

.side-panel__header > div {
  min-width: 0;
}

.side-panel__header p {
  margin: 0 0 2px;
  color: var(--primary-700);
  font-size: 11px;
  font-weight: var(--font-semibold);
  text-transform: uppercase;
}

.side-panel__header h2 {
  margin: 0;
  overflow-wrap: anywhere;
  color: var(--gray-900);
  font-size: 18px;
  font-weight: var(--font-semibold);
}

.side-panel__header :deep(.side-panel-subtitle) {
  display: block;
  margin-top: 3px;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.side-panel__header > button {
  display: grid;
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--gray-600);
  cursor: pointer;
}

.side-panel__header > button:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.side-panel__body {
  min-height: 0;
  overflow-y: auto;
  padding: 20px;
}

.side-panel__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-height: 58px;
  padding: 10px 20px;
  border-top: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.side-panel-enter-active,
.side-panel-leave-active {
  transition: background-color var(--transition-base);
}

.side-panel-enter-active .side-panel,
.side-panel-leave-active .side-panel {
  transition: transform var(--transition-base);
}

.side-panel-enter-from,
.side-panel-leave-to {
  background: transparent;
}

.side-panel-enter-from .side-panel,
.side-panel-leave-to .side-panel {
  transform: translateX(100%);
}

@media (max-width: 620px) {
  .side-panel {
    width: 100%;
    border-left: 0;
    box-shadow: none;
  }

  .side-panel__body,
  .side-panel__header,
  .side-panel__footer {
    padding-inline: 16px;
  }
}
</style>
