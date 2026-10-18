<template>
  <div class="system-admin">
    <PageHeader
      title="System"
      description="Runtime, workflow dependencies, and publication readiness"
    >
      <template #meta>
        <span v-if="report">{{ readinessLabel }}</span>
      </template>
      <template #actions>
        <button
          class="icon-button"
          type="button"
          :disabled="loading"
          title="Refresh system status"
          aria-label="Refresh system status"
          @click="refresh"
        >
          <Icon name="rotate-ccw" :size="17" :spin="loading" />
        </button>
      </template>
    </PageHeader>

    <div v-if="error" class="system-message system-message--error" role="alert">
      <Icon name="circle-x" :size="18" />
      <span>{{ error }}</span>
      <button type="button" @click="refresh">Retry</button>
    </div>

    <div v-if="loading && !report" class="system-loading" aria-label="Loading system status">
      <span v-for="index in 4" :key="index"></span>
    </div>

    <template v-else-if="report">
      <section class="status-overview" aria-label="System status summary">
        <article v-for="item in summaryItems" :key="item.label" class="status-overview__item">
          <span class="status-overview__icon" :class="`status-overview__icon--${item.tone}`">
            <Icon :name="item.icon" :size="17" />
          </span>
          <span class="status-overview__copy">
            <small>{{ item.label }}</small>
            <strong :class="`status-text--${item.tone}`">{{ item.value }}</strong>
          </span>
        </article>
      </section>

      <section v-if="priorityChecks.length" class="system-section system-section--priority">
        <header class="section-heading">
          <div>
            <h2>Priority actions</h2>
            <p>Core blockers to resolve first</p>
          </div>
          <span class="section-count">{{ report.summary?.core_blockers || priorityChecks.length }}</span>
        </header>

        <div class="priority-list">
          <article v-for="item in priorityChecks" :key="`${item.group.id}-${item.check.id}`" class="priority-row">
            <span class="priority-row__icon">
              <Icon name="triangle-alert" :size="17" />
            </span>
            <div class="priority-row__copy">
              <span>{{ item.group.label }}</span>
              <strong>{{ item.check.label }}</strong>
              <p>{{ item.check.detail }}</p>
              <div v-if="item.check.action" class="command-row">
                <code>{{ item.check.action }}</code>
                <button
                  type="button"
                  :title="copiedText === item.check.action ? 'Copied' : 'Copy command'"
                  :aria-label="copiedText === item.check.action ? 'Copied' : 'Copy command'"
                  @click="copyText(item.check.action)"
                >
                  <Icon :name="copiedText === item.check.action ? 'check' : 'copy'" :size="15" />
                </button>
              </div>
            </div>
          </article>
        </div>

        <p v-if="remainingPriorityCount" class="priority-more">
          {{ remainingPriorityCount }} more blocker{{ remainingPriorityCount === 1 ? '' : 's' }} listed below.
        </p>
      </section>

      <div v-else class="system-message system-message--success">
        <Icon name="circle-check" :size="18" />
        <span>Core runtime checks are ready.</span>
      </div>

      <section class="system-section">
        <header class="section-heading">
          <div>
            <h2>Environment checks</h2>
            <p>Open a group to inspect paths and setup actions</p>
          </div>
          <span class="section-count">{{ report.groups.length }}</span>
        </header>

        <div class="check-groups">
          <details
            v-for="group in report.groups"
            :key="group.id"
            class="check-group"
            :open="group.id === firstProblemGroupId"
          >
            <summary>
              <span class="check-group__state" :class="`check-group__state--${groupTone(group)}`">
                <Icon :name="groupIcon(group)" :size="17" />
              </span>
              <span class="check-group__title">
                <strong>{{ group.label }}</strong>
                <small>{{ groupReadyCount(group) }}/{{ group.checks.length }} ready</small>
              </span>
              <span v-if="group.optional" class="pill pill--muted">Optional</span>
              <span v-else-if="groupIssueCount(group)" class="pill" :class="`pill--${groupTone(group)}`">
                {{ groupIssueCount(group) }} issue{{ groupIssueCount(group) === 1 ? '' : 's' }}
              </span>
              <span v-else class="pill pill--success">Ready</span>
              <Icon class="check-group__chevron" name="chevron-down" :size="16" />
            </summary>

            <div class="check-list">
              <article v-for="check in group.checks" :key="check.id" class="check-row">
                <span class="check-row__state" :class="`check-row__state--${check.status}`">
                  <Icon :name="statusIcon(check.status)" :size="16" />
                </span>
                <div class="check-row__body">
                  <div class="check-row__heading">
                    <strong>{{ check.label }}</strong>
                    <span :class="`status-text--${statusTone(check.status)}`">{{ statusLabel(check.status) }}</span>
                  </div>
                  <p>{{ check.detail }}</p>
                  <code v-if="check.path" class="check-row__path">{{ check.path }}</code>
                  <div v-if="check.action" class="command-row">
                    <code>{{ check.action }}</code>
                    <button
                      type="button"
                      :title="copiedText === check.action ? 'Copied' : 'Copy command'"
                      :aria-label="copiedText === check.action ? 'Copied' : 'Copy command'"
                      @click="copyText(check.action)"
                    >
                      <Icon :name="copiedText === check.action ? 'check' : 'copy'" :size="15" />
                    </button>
                  </div>
                </div>
              </article>
            </div>
          </details>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import Icon from '../components/ui/Icon.vue'
import PageHeader from '../components/ui/PageHeader.vue'

const report = ref(null)
const loading = ref(false)
const error = ref('')
const copiedText = ref('')
let copiedTimer = null

const readinessLabel = computed(() => {
  if (!report.value) return ''
  const blockers = report.value.summary?.core_blockers || 0
  return blockers ? `${blockers} core blocker${blockers === 1 ? '' : 's'}` : 'Core runtime ready'
})

const summaryItems = computed(() => {
  if (!report.value) return []
  const coreBlockers = report.value.summary?.core_blockers || 0
  return [
    {
      label: 'Core runtime',
      value: report.value.ready ? 'Ready' : `${coreBlockers} blocked`,
      tone: report.value.ready ? 'success' : 'danger',
      icon: report.value.ready ? 'circle-check' : 'circle-x',
    },
    {
      label: 'Publication record',
      value: report.value.publication_ready ? 'Ready' : 'Incomplete',
      tone: report.value.publication_ready ? 'success' : 'warning',
      icon: report.value.publication_ready ? 'circle-check' : 'triangle-alert',
    },
    {
      label: 'Metagenomics',
      value: capabilityReady('metagenomics') ? 'Available' : 'Unavailable',
      tone: capabilityReady('metagenomics') ? 'success' : 'danger',
      icon: capabilityReady('metagenomics') ? 'circle-check' : 'circle-x',
    },
    {
      label: 'Paleoproteomics',
      value: capabilityReady('paleoproteomics') ? 'Available' : 'Not ready',
      tone: capabilityReady('paleoproteomics') ? 'success' : 'muted',
      icon: capabilityReady('paleoproteomics') ? 'circle-check' : 'circle',
    },
  ]
})

const allPriorityChecks = computed(() => (report.value?.groups || [])
  .filter((group) => !group.optional && group.id !== 'publication')
  .flatMap((group) => (group.checks || [])
    .filter((check) => check.status === 'error')
    .map((check) => ({ group, check }))))

const priorityChecks = computed(() => allPriorityChecks.value.slice(0, 4))
const remainingPriorityCount = computed(() => Math.max(0, allPriorityChecks.value.length - priorityChecks.value.length))
const firstProblemGroupId = computed(() => (
  report.value?.groups?.find((group) => !group.optional && groupIssueCount(group))?.id || ''
))

function capabilityReady(name) {
  return Boolean(report.value?.capabilities?.[name]?.ready)
}

function groupReadyCount(group) {
  return (group.checks || []).filter((check) => check.status === 'ok').length
}

function groupIssueCount(group) {
  return (group.checks || []).filter((check) => check.status !== 'ok').length
}

function groupTone(group) {
  if ((group.checks || []).some((check) => check.status === 'error')) return group.optional ? 'warning' : 'danger'
  if ((group.checks || []).some((check) => check.status === 'warn')) return 'warning'
  return 'success'
}

function groupIcon(group) {
  const tone = groupTone(group)
  if (tone === 'success') return 'circle-check'
  if (tone === 'danger') return 'circle-x'
  return 'triangle-alert'
}

function statusIcon(status) {
  if (status === 'ok') return 'circle-check'
  if (status === 'error') return 'circle-x'
  return 'triangle-alert'
}

function statusTone(status) {
  if (status === 'ok') return 'success'
  if (status === 'error') return 'danger'
  return 'warning'
}

function statusLabel(status) {
  if (status === 'ok') return 'Ready'
  if (status === 'error') return 'Action needed'
  return 'Review'
}

async function copyText(value) {
  try {
    await navigator.clipboard.writeText(value)
    copiedText.value = value
    window.clearTimeout(copiedTimer)
    copiedTimer = window.setTimeout(() => { copiedText.value = '' }, 1800)
  } catch {
    copiedText.value = ''
  }
}

async function refresh() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/system/readiness')
    const payload = await response.json().catch(() => ({}))
    if (!response.ok || !payload.success) {
      throw new Error(payload.error || 'Failed to check server readiness.')
    }
    report.value = payload.data
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

onMounted(refresh)
onBeforeUnmount(() => window.clearTimeout(copiedTimer))
</script>

<style scoped>
.system-admin {
  min-width: 0;
}

.icon-button {
  display: grid;
  width: var(--control-height);
  height: var(--control-height);
  place-items: center;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--gray-600);
  cursor: pointer;
}

.icon-button:hover:not(:disabled) {
  border-color: var(--border-color-dark);
  color: var(--gray-900);
}

.icon-button:disabled {
  cursor: wait;
  color: var(--gray-400);
}

.system-message {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 10px 12px;
  margin-bottom: 18px;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-base);
  font-size: var(--text-sm);
}

.system-message span {
  flex: 1;
}

.system-message button {
  border: 0;
  background: transparent;
  color: inherit;
  font-weight: var(--font-semibold);
  cursor: pointer;
}

.system-message--error {
  border-color: #f0c7c3;
  background: var(--error-50);
  color: var(--error-600);
}

.system-message--success {
  border-color: #c9e7d8;
  background: var(--success-50);
  color: var(--success-600);
}

.system-loading,
.status-overview {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-block: 1px solid var(--border-color);
}

.system-loading span {
  height: 70px;
  margin: 16px;
  border-radius: var(--radius-base);
  background: var(--surface-2);
  animation: system-pulse 1.2s ease-in-out infinite alternate;
}

.status-overview {
  margin: 20px 0 30px;
}

.status-overview__item {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 11px;
  padding: 15px 16px;
  border-right: 1px solid var(--border-color-light);
}

.status-overview__item:last-child {
  border-right: 0;
}

.status-overview__icon {
  display: grid;
  width: 30px;
  height: 30px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: var(--radius-full);
  background: var(--surface-2);
  color: var(--gray-500);
}

.status-overview__icon--success { background: var(--success-50); color: var(--success-600); }
.status-overview__icon--warning { background: var(--warning-50); color: var(--warning-600); }
.status-overview__icon--danger { background: var(--error-50); color: var(--error-600); }

.status-overview__copy {
  display: grid;
  min-width: 0;
}

.status-overview__copy small {
  overflow: hidden;
  color: var(--gray-500);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-overview__copy strong {
  margin-top: 3px;
  overflow-wrap: anywhere;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.status-text--success { color: var(--success-600); }
.status-text--warning { color: var(--warning-600); }
.status-text--danger { color: var(--error-600); }
.status-text--muted { color: var(--gray-500); }

.system-section {
  margin-top: 30px;
}

.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 11px;
  border-bottom: 1px solid var(--border-color);
}

.section-heading h2 {
  margin: 0;
  color: var(--gray-900);
  font-size: 16px;
  font-weight: var(--font-semibold);
}

.section-heading p {
  margin: 3px 0 0;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.section-count {
  min-width: 24px;
  color: var(--gray-500);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.priority-list {
  border-bottom: 1px solid var(--border-color-light);
}

.priority-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  gap: 10px;
  padding: 14px 4px;
  border-bottom: 1px solid var(--border-color-light);
}

.priority-row:last-child {
  border-bottom: 0;
}

.priority-row__icon {
  padding-top: 2px;
  color: var(--error-500);
}

.priority-row__copy > span {
  display: block;
  margin-bottom: 2px;
  color: var(--gray-500);
  font-size: 11px;
}

.priority-row__copy > strong {
  color: var(--gray-900);
  font-size: var(--text-sm);
}

.priority-row__copy > p,
.check-row__body > p {
  margin: 3px 0 0;
  color: var(--gray-600);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.priority-more {
  margin: 10px 0 0;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.check-groups {
  border-bottom: 1px solid var(--border-color);
}

.check-group {
  border-bottom: 1px solid var(--border-color-light);
}

.check-group:last-child {
  border-bottom: 0;
}

.check-group > summary {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto 18px;
  align-items: center;
  gap: 10px;
  min-height: 58px;
  padding: 8px 4px;
  color: var(--gray-700);
  cursor: pointer;
  list-style: none;
}

.check-group > summary::-webkit-details-marker {
  display: none;
}

.check-group > summary:hover {
  color: var(--gray-900);
}

.check-group__state {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: var(--radius-full);
  background: var(--surface-2);
  color: var(--gray-500);
}

.check-group__state--success { background: var(--success-50); color: var(--success-600); }
.check-group__state--warning { background: var(--warning-50); color: var(--warning-600); }
.check-group__state--danger { background: var(--error-50); color: var(--error-600); }

.check-group__title {
  display: grid;
}

.check-group__title strong {
  color: var(--gray-900);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.check-group__title small {
  margin-top: 2px;
  color: var(--gray-500);
  font-size: 11px;
}

.check-group__chevron {
  color: var(--gray-400);
  transition: transform var(--transition-fast);
}

.check-group[open] .check-group__chevron {
  transform: rotate(180deg);
}

.check-list {
  padding-left: 38px;
  border-top: 1px solid var(--border-color-light);
}

.check-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 9px;
  padding: 13px 4px;
  border-bottom: 1px solid var(--border-color-light);
}

.check-row:last-child {
  border-bottom: 0;
}

.check-row__state {
  padding-top: 1px;
  color: var(--gray-400);
}

.check-row__state--ok { color: var(--success-600); }
.check-row__state--warn { color: var(--warning-600); }
.check-row__state--error { color: var(--error-600); }

.check-row__heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.check-row__heading strong {
  color: var(--gray-800);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.check-row__heading span {
  flex: 0 0 auto;
  font-size: 11px;
}

.check-row__path {
  display: block;
  margin-top: 6px;
  overflow-wrap: anywhere;
  color: var(--gray-500);
  font-size: 11px;
}

.command-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 30px;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 5px 5px 5px 9px;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-base);
  background: var(--surface-2);
}

.command-row code {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--gray-700);
  font-size: 11px;
}

.command-row button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
}

.command-row button:hover {
  background: var(--surface-3);
  color: var(--gray-800);
}

@keyframes system-pulse {
  to { opacity: 0.45; }
}

@media (max-width: 860px) {
  .status-overview,
  .system-loading {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .status-overview__item:nth-child(2),
  .system-loading span:nth-child(2) {
    border-right: 0;
  }

  .status-overview__item:nth-child(-n + 2) {
    border-bottom: 1px solid var(--border-color-light);
  }
}

@media (max-width: 520px) {
  .status-overview {
    grid-template-columns: minmax(0, 1fr);
  }

  .status-overview__item {
    border-right: 0;
    border-bottom: 1px solid var(--border-color-light);
  }

  .status-overview__item:last-child {
    border-bottom: 0;
  }

  .check-group > summary {
    grid-template-columns: 28px minmax(0, 1fr) 18px;
  }

  .check-group > summary .pill {
    display: none;
  }

  .check-list {
    padding-left: 4px;
  }

  .check-row__heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 2px;
  }
}
</style>
