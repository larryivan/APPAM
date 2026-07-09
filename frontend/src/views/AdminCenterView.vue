<template>
  <div class="admin-center">
    <AdminNav active="setup" />

    <PageHeader eyebrow="Administration" title="Lab Setup">
      <template #meta>
        <span>{{ readinessLabel }}</span>
      </template>
      <template #actions>
        <button class="refresh-button" type="button" :disabled="loading" title="Refresh readiness" @click="refresh">
          <Icon name="rotate-ccw" :size="16" :spin="loading" />
          {{ loading ? 'Checking' : 'Refresh' }}
        </button>
      </template>
    </PageHeader>

    <p v-if="error" class="setup-message error">{{ error }}</p>

    <template v-if="report">
      <section class="readiness-strip" aria-label="Readiness summary">
        <div>
          <span>Core runtime</span>
          <strong :class="report.ready ? 'ok' : 'error'">{{ report.ready ? 'Ready' : 'Blocked' }}</strong>
        </div>
        <div>
          <span>Publication record</span>
          <strong :class="report.publication_ready ? 'ok' : 'warning'">
            {{ report.publication_ready ? 'Ready' : 'Incomplete' }}
          </strong>
        </div>
        <div>
          <span>Metagenomics</span>
          <strong :class="capabilityReady('metagenomics') ? 'ok' : 'error'">
            {{ capabilityReady('metagenomics') ? 'Available' : 'Unavailable' }}
          </strong>
        </div>
        <div>
          <span>Paleoproteomics</span>
          <strong :class="capabilityReady('paleoproteomics') ? 'ok' : 'muted'">
            {{ capabilityReady('paleoproteomics') ? 'Available' : 'Optional' }}
          </strong>
        </div>
      </section>

      <section v-for="group in report.groups" :key="group.id" class="setup-group">
        <header>
          <div>
            <h2>{{ group.label }}</h2>
            <span v-if="group.optional" class="optional-label">Optional workflow</span>
          </div>
          <span class="group-count">{{ groupReadyCount(group) }}/{{ group.checks.length }}</span>
        </header>

        <div class="check-list">
          <article v-for="check in group.checks" :key="check.id" class="check-row">
            <span class="check-icon" :class="check.status">
              <Icon :name="statusIcon(check.status)" :size="18" />
            </span>
            <div class="check-main">
              <div class="check-heading">
                <strong>{{ check.label }}</strong>
                <span class="status-label" :class="check.status">{{ statusLabel(check.status) }}</span>
              </div>
              <p>{{ check.detail }}</p>
              <code v-if="check.path">{{ check.path }}</code>
              <div v-if="check.action" class="check-action">
                <span>Next</span>
                <code>{{ check.action }}</code>
              </div>
            </div>
          </article>
        </div>
      </section>
    </template>

    <div v-else-if="loading" class="setup-loading">Checking server resources...</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AdminNav from '../components/AdminNav.vue'
import Icon from '../components/ui/Icon.vue'
import PageHeader from '../components/ui/PageHeader.vue'

const report = ref(null)
const loading = ref(false)
const error = ref('')

const readinessLabel = computed(() => {
  if (!report.value) return 'Checking server resources'
  const blockers = report.value.summary?.core_blockers || 0
  return blockers ? `${blockers} core blocker${blockers === 1 ? '' : 's'}` : 'Core runtime ready'
})

function capabilityReady(name) {
  return Boolean(report.value?.capabilities?.[name]?.ready)
}

function groupReadyCount(group) {
  return (group.checks || []).filter((check) => check.status === 'ok').length
}

function statusIcon(status) {
  if (status === 'ok') return 'circle-check'
  if (status === 'error') return 'circle-x'
  return 'triangle-alert'
}

function statusLabel(status) {
  if (status === 'ok') return 'Ready'
  if (status === 'error') return 'Action needed'
  return 'Optional'
}

async function refresh() {
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
</script>

<style scoped>
.admin-center {
  width: min(1120px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0 48px;
}

.refresh-button {
  min-height: 36px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 13px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--surface-1);
  color: var(--gray-700);
  font-weight: var(--font-medium);
  cursor: pointer;
}

.refresh-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.setup-message,
.setup-loading {
  margin: 24px 0;
  padding: 14px 16px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--gray-600);
  background: var(--surface-1);
}

.setup-message.error {
  color: #b42318;
  border-color: #f5c2bd;
  background: #fff7f6;
}

.readiness-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: 22px 0 32px;
  border-block: 1px solid var(--border-color);
}

.readiness-strip > div {
  min-width: 0;
  padding: 17px 18px;
  border-right: 1px solid var(--border-color);
}

.readiness-strip > div:last-child {
  border-right: 0;
}

.readiness-strip span,
.readiness-strip strong {
  display: block;
}

.readiness-strip span {
  margin-bottom: 5px;
  color: var(--gray-500);
  font-size: var(--text-xs);
  text-transform: uppercase;
}

.readiness-strip strong {
  overflow-wrap: anywhere;
  color: var(--gray-900);
  font-size: var(--text-lg);
}

.readiness-strip strong.ok { color: #087443; }
.readiness-strip strong.error { color: #b42318; }
.readiness-strip strong.warning { color: #9a6700; }
.readiness-strip strong.muted { color: var(--gray-500); }

.setup-group {
  margin-top: 28px;
}

.setup-group > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
}

.setup-group h2 {
  display: inline;
  margin: 0;
  color: var(--gray-900);
  font-size: var(--text-lg);
}

.optional-label,
.group-count {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.optional-label {
  margin-left: 9px;
}

.group-count {
  font-variant-numeric: tabular-nums;
}

.check-list {
  border-top: 1px solid var(--border-color);
}

.check-row {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 12px;
  padding: 15px 4px;
  border-bottom: 1px solid var(--border-color-light);
}

.check-icon {
  padding-top: 1px;
  color: var(--gray-400);
}

.check-icon.ok { color: #087443; }
.check-icon.error { color: #b42318; }
.check-icon.warn { color: #9a6700; }

.check-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
}

.check-heading strong {
  color: var(--gray-900);
  font-size: var(--text-sm);
}

.status-label {
  flex: 0 0 auto;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.status-label.ok { color: #087443; }
.status-label.error { color: #b42318; }
.status-label.warn { color: #9a6700; }

.check-main p {
  margin: 4px 0 0;
  color: var(--gray-600);
  font-size: var(--text-sm);
  line-height: 1.5;
}

.check-main > code,
.check-action code {
  display: block;
  margin-top: 7px;
  overflow-wrap: anywhere;
  color: var(--gray-600);
  font-size: var(--text-xs);
}

.check-action {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: baseline;
  gap: 9px;
  margin-top: 8px;
}

.check-action span {
  color: var(--primary-700);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
}

.check-action code {
  margin: 0;
  color: var(--gray-800);
}

@media (max-width: 760px) {
  .readiness-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .readiness-strip > div:nth-child(2) {
    border-right: 0;
  }

  .readiness-strip > div:nth-child(-n + 2) {
    border-bottom: 1px solid var(--border-color);
  }
}

@media (max-width: 480px) {
  .admin-center {
    width: min(100% - 22px, 1120px);
    padding-top: 16px;
  }

  .readiness-strip {
    grid-template-columns: 1fr;
  }

  .readiness-strip > div {
    border-right: 0;
    border-bottom: 1px solid var(--border-color);
  }

  .readiness-strip > div:last-child {
    border-bottom: 0;
  }

  .check-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 3px;
  }
}
</style>
