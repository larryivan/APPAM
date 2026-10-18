<template>
  <Teleport to="body">
    <div class="toast-region" role="region" aria-label="Notifications">
      <TransitionGroup name="toast">
        <article
          v-for="toast in toastList"
          :key="toast.id"
          class="toast"
          :class="`toast--${toast.tone}`"
          :role="toast.tone === 'error' ? 'alert' : 'status'"
          :aria-live="toast.tone === 'error' ? 'assertive' : 'polite'"
        >
          <Icon class="toast-icon" :name="iconFor(toast.tone)" :size="17" />
          <div class="toast-copy">
            <p v-if="toast.title" class="toast-title">{{ toast.title }}</p>
            <p class="toast-message">{{ toast.message }}</p>
            <details v-if="toast.detail" class="toast-detail">
              <summary>Technical details</summary>
              <pre>{{ toast.detail }}</pre>
            </details>
          </div>
          <button
            type="button"
            class="toast-dismiss"
            aria-label="Dismiss notification"
            @click="dismissToast(toast.id)"
          >
            <Icon name="x" :size="15" />
          </button>
        </article>
      </TransitionGroup>
    </div>
  </Teleport>

  <Modal
    :open="confirmDialogState.open"
    :title="confirmDialogState.title"
    size="sm"
    @close="settleConfirm(false)"
  >
    <p v-if="confirmDialogState.message" class="confirm-message">
      {{ confirmDialogState.message }}
    </p>
    <p v-if="confirmDialogState.detail" class="confirm-detail">
      {{ confirmDialogState.detail }}
    </p>

    <template #footer>
      <button type="button" class="confirm-btn" @click="settleConfirm(false)">
        {{ confirmDialogState.cancelLabel }}
      </button>
      <button
        type="button"
        class="confirm-btn confirm-btn--primary"
        :class="{ 'confirm-btn--danger': confirmDialogState.tone === 'danger' }"
        @click="settleConfirm(true)"
      >
        {{ confirmDialogState.confirmLabel }}
      </button>
    </template>
  </Modal>
</template>

<script setup>
import Icon from './Icon.vue'
import Modal from './Modal.vue'
import { confirmDialogState, dismissToast, settleConfirm, toastList } from '@/lib/notify.js'

const ICONS = { success: 'check', error: 'triangle-alert', info: 'info' }
const iconFor = (tone) => ICONS[tone] || ICONS.info
</script>

<style scoped>
.toast-region {
  position: fixed;
  right: var(--spacing-4);
  bottom: var(--spacing-4);
  z-index: var(--z-toast);
  display: grid;
  gap: var(--spacing-2);
  width: min(380px, calc(100vw - var(--spacing-8)));
  pointer-events: none;
}

.toast {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  box-shadow: var(--shadow-md);
  pointer-events: auto;
}

.toast-icon { margin-top: 1px; color: var(--gray-500); }
.toast--success .toast-icon { color: var(--success-500); }
.toast--error .toast-icon { color: var(--error-500); }

.toast-copy { min-width: 0; }

.toast-title {
  margin: 0 0 2px;
  color: var(--gray-900);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.toast-message {
  margin: 0;
  color: var(--gray-700);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  overflow-wrap: anywhere;
}

.toast-detail { margin-top: var(--spacing-2); }

.toast-detail summary {
  color: var(--gray-500);
  font-size: var(--text-xs);
  cursor: pointer;
}

.toast-detail pre {
  margin: var(--spacing-2) 0 0;
  max-height: 160px;
  padding: var(--spacing-2);
  overflow: auto;
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  color: var(--gray-600);
  font-family: var(--font-family-mono);
  font-size: var(--text-xs);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.toast-dismiss {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--gray-400);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.toast-dismiss:hover { background: var(--surface-2); color: var(--gray-700); }

.toast-enter-active,
.toast-leave-active { transition: opacity var(--transition-base), transform var(--transition-base); }
.toast-enter-from { opacity: 0; transform: translateY(8px); }
.toast-leave-to { opacity: 0; transform: translateY(4px); }
.toast-move { transition: transform var(--transition-base); }

.confirm-message {
  margin: 0;
  color: var(--gray-700);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.confirm-detail {
  margin: var(--spacing-3) 0 0;
  color: var(--gray-500);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.confirm-btn {
  min-height: var(--control-height);
  padding: 0 var(--spacing-4);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--gray-700);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.confirm-btn:hover { background: var(--surface-2); }

.confirm-btn--primary {
  border-color: var(--primary-600);
  background: var(--primary-600);
  color: #fff;
}

.confirm-btn--primary:hover { background: var(--primary-700); border-color: var(--primary-700); }

.confirm-btn--danger {
  border-color: var(--error-600);
  background: var(--error-600);
}

.confirm-btn--danger:hover { background: var(--error-500); border-color: var(--error-500); }
</style>
