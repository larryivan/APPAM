<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="modal-layer"
        @mousedown.self="closeOnBackdrop && $emit('close')"
      >
        <div
          ref="panel"
          class="modal-panel"
          :class="`modal-panel--${size}`"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          :aria-describedby="subtitle ? descriptionId : undefined"
          tabindex="-1"
        >
          <header class="modal-header">
            <div class="modal-heading">
              <p v-if="eyebrow" class="modal-eyebrow">{{ eyebrow }}</p>
              <h2 :id="titleId">{{ title }}</h2>
              <p v-if="subtitle" :id="descriptionId" class="modal-subtitle">{{ subtitle }}</p>
            </div>
            <button
              type="button"
              class="modal-close"
              title="Close"
              aria-label="Close"
              @click="$emit('close')"
            >
              <Icon name="x" :size="17" />
            </button>
          </header>

          <div class="modal-body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </footer>
        </div>
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
  subtitle: { type: String, default: '' },
  size: { type: String, default: 'md' }, // sm | md | lg
  closeOnBackdrop: { type: Boolean, default: true },
})

const emit = defineEmits(['close'])

const panel = ref(null)
const titleId = nextOverlayId('modal-title')
const descriptionId = nextOverlayId('modal-description')

useOverlay(() => props.open, { onClose: () => emit('close'), panelRef: panel })
</script>

<style scoped>
.modal-layer {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-6);
  background: rgb(18 22 26 / 0.28);
}

.modal-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  width: min(560px, 100%);
  max-height: min(720px, calc(100vh - var(--spacing-12)));
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-xl);
  background: var(--surface-1);
  box-shadow: var(--shadow-lg);
  outline: none;
}

.modal-panel--sm { width: min(420px, 100%); }
.modal-panel--lg { width: min(760px, 100%); }

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-4);
  padding: var(--spacing-5) var(--spacing-6) var(--spacing-4);
  border-bottom: 1px solid var(--border-color-light);
}

.modal-heading {
  min-width: 0;
}

.modal-eyebrow {
  margin: 0 0 var(--spacing-1);
  color: var(--gray-500);
  font-size: 11px;
  font-weight: var(--font-medium);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.modal-heading h2 {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.modal-subtitle {
  margin: var(--spacing-1) 0 0;
  color: var(--gray-500);
  font-size: var(--text-sm);
}

.modal-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.modal-close:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.modal-body {
  min-height: 0;
  padding: var(--spacing-5) var(--spacing-6);
  overflow-y: auto;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--spacing-2);
  padding: var(--spacing-4) var(--spacing-6);
  border-top: 1px solid var(--border-color-light);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--transition-fast);
}

.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition: transform var(--transition-base), opacity var(--transition-base);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  opacity: 0;
  transform: translateY(6px) scale(0.99);
}

@media (max-width: 640px) {
  .modal-layer {
    padding: var(--spacing-3);
    align-items: flex-end;
  }

  .modal-panel,
  .modal-panel--sm,
  .modal-panel--lg {
    width: 100%;
    max-height: calc(100vh - var(--spacing-8));
  }
}
</style>
