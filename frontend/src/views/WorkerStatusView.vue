<template>
  <div class="queue-admin">
    <PageHeader title="Queue" description="Worker health and analysis activity">
      <template #meta>
        <span v-if="data">Updates every 5 seconds · {{ formatRelative(updatedAt) }}</span>
      </template>
      <template #actions>
        <button
          class="icon-button"
          type="button"
          :disabled="loading"
          title="Refresh queue status"
          aria-label="Refresh queue status"
          @click="refresh"
        >
          <Icon name="rotate-ccw" :size="17" :spin="loading" />
        </button>
      </template>
    </PageHeader>

    <div v-if="error" class="queue-message queue-message--error" role="alert">
      <Icon name="circle-x" :size="18" />
      <span>{{ error }}</span>
      <button type="button" @click="refresh">Retry</button>
    </div>

    <div v-if="loading && !data" class="queue-loading" aria-label="Loading queue status">
      <span></span><span></span><span></span>
    </div>

    <template v-else-if="data">
      <section class="worker-banner" :class="{ 'worker-banner--offline': !workerHealthy }">
        <span class="worker-banner__icon">
          <Icon :name="workerHealthy ? 'activity' : 'triangle-alert'" :size="19" />
        </span>
        <div class="worker-banner__copy">
          <strong>{{ workerHealthy ? 'Worker online' : 'Worker unavailable' }}</strong>
          <span>{{ workerHeadline }}</span>
        </div>
        <span class="worker-banner__heartbeat">{{ heartbeatLabel }}</span>
      </section>

      <section class="queue-summary" aria-label="Queue summary">
        <article v-for="item in queueSummary" :key="item.label" :class="{ 'has-alert': item.alert }">
          <small>{{ item.label }}</small>
          <strong>{{ item.value }}</strong>
        </article>
      </section>

      <section class="queue-section">
        <header class="section-heading">
          <div>
            <h2>Active jobs</h2>
            <p>Queued, starting, and running analyses</p>
          </div>
          <span>{{ data.active_jobs.length }}</span>
        </header>

        <div v-if="data.active_jobs.length" class="job-table-wrap">
          <table class="job-table">
            <thead>
              <tr>
                <th>Analysis</th>
                <th>Status</th>
                <th>Worker</th>
                <th>Last activity</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="job in data.active_jobs" :key="job.id">
                <td>
                  <span class="job-name">
                    <strong>{{ job.tool_name }}</strong>
                    <code>{{ compactId(job.id) }}</code>
                  </span>
                </td>
                <td><span class="pill" :class="jobTone(job.status)">{{ humanize(job.status) }}</span></td>
                <td><code class="job-worker">{{ job.claimed_by || 'Unclaimed' }}</code></td>
                <td class="job-time">{{ formatDateTime(job.heartbeat_at || job.started_at || job.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-else class="queue-empty">
          <span><Icon name="circle-check" :size="18" /></span>
          <div>
            <strong>Queue is clear</strong>
            <p>No analyses are waiting or running.</p>
          </div>
        </div>
      </section>

      <section v-if="data.stale_jobs.length || data.worker.last_error" class="queue-section queue-section--attention">
        <header class="section-heading">
          <div>
            <h2>Needs attention</h2>
            <p>Stale jobs and the latest worker error</p>
          </div>
          <span>{{ data.stale_jobs.length + (data.worker.last_error ? 1 : 0) }}</span>
        </header>

        <article v-if="data.worker.last_error" class="attention-row">
          <Icon name="circle-x" :size="17" />
          <div><strong>Worker error</strong><p>{{ data.worker.last_error }}</p></div>
        </article>
        <article v-for="job in data.stale_jobs" :key="job.id" class="attention-row">
          <Icon name="triangle-alert" :size="17" />
          <div>
            <strong>{{ job.tool_name }}</strong>
            <p>{{ humanize(job.status) }} · {{ compactId(job.id) }} · pid {{ job.pid || 'n/a' }}</p>
          </div>
        </article>
      </section>

      <details class="worker-details">
        <summary>
          <span>
            <Icon name="cpu" :size="17" />
            Worker details
          </span>
          <Icon name="chevron-down" :size="16" />
        </summary>
        <dl>
          <div><dt>Mode</dt><dd>{{ data.mode }}</dd></div>
          <div><dt>Host</dt><dd>{{ data.worker.host }}</dd></div>
          <div><dt>Worker ID</dt><dd><code>{{ data.worker.worker_id }}</code></dd></div>
          <div><dt>Started</dt><dd>{{ formatDateTime(data.worker.started_at) }}</dd></div>
          <div><dt>Last heartbeat</dt><dd>{{ formatDateTime(data.worker.last_heartbeat_at) }}</dd></div>
          <div><dt>Current job</dt><dd><code>{{ data.worker.current_job_id || 'Idle' }}</code></dd></div>
          <div><dt>Last claimed</dt><dd>{{ formatDateTime(data.worker.last_claimed_at) }}</dd></div>
          <div><dt>Last idle</dt><dd>{{ formatDateTime(data.worker.last_idle_at) }}</dd></div>
          <div><dt>Poll interval</dt><dd>{{ data.poll_interval_seconds }}s</dd></div>
          <div><dt>Stale timeout</dt><dd>{{ data.stale_timeout_seconds }}s</dd></div>
          <div><dt>Recovered jobs</dt><dd>{{ data.worker.recovered_jobs }}</dd></div>
        </dl>
      </details>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

import Icon from '../components/ui/Icon.vue'
import PageHeader from '../components/ui/PageHeader.vue'

const data = ref(null)
const error = ref('')
const loading = ref(false)
const updatedAt = ref(null)
const now = ref(Date.now())
let pollTimer = null
let clockTimer = null

const workerHealthy = computed(() => Boolean(data.value?.embedded_worker_running && !data.value?.worker?.last_error))

const activeCount = computed(() => (
  (data.value?.counts?.queued || 0)
  + (data.value?.counts?.starting || 0)
  + (data.value?.counts?.running || 0)
))

const workerHeadline = computed(() => {
  if (!data.value) return ''
  if (!data.value.embedded_worker_running) return 'The execution worker is not responding.'
  if (data.value.worker.last_error) return 'Online with a reported error.'
  if (data.value.worker.current_job_id) return `Running job ${compactId(data.value.worker.current_job_id)} on ${data.value.worker.host}.`
  return `Idle on ${data.value.worker.host}. Ready to claim analyses.`
})

const heartbeatLabel = computed(() => {
  const value = data.value?.worker?.last_heartbeat_at
  return value ? `Heartbeat ${formatRelative(value)}` : 'No heartbeat'
})

const queueSummary = computed(() => {
  const counts = data.value?.counts || {}
  return [
    { label: 'Active', value: activeCount.value },
    { label: 'Queued', value: counts.queued || 0 },
    { label: 'Completed', value: counts.completed || 0 },
    { label: 'Failed', value: counts.failed || 0, alert: Boolean(counts.failed) },
    { label: 'Canceled', value: counts.canceled || 0 },
  ]
})

function parseDate(value) {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(String(value).replace(' ', 'T'))
  return Number.isNaN(date.getTime()) ? null : date
}

function formatDateTime(value) {
  const date = parseDate(value)
  if (!date) return value || 'Never'
  return new Intl.DateTimeFormat('en', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  }).format(date)
}

function formatRelative(value) {
  const date = parseDate(value)
  if (!date) return 'just now'
  const delta = Math.max(0, Math.floor((now.value - date.getTime()) / 1000))
  if (delta < 5) return 'just now'
  if (delta < 60) return `${delta}s ago`
  const minutes = Math.floor(delta / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ago`
}

function compactId(value) {
  const text = String(value || '')
  return text.length > 14 ? `${text.slice(0, 8)}…${text.slice(-4)}` : text || 'Unknown'
}

function humanize(status) {
  const labels = {
    queued: 'Queued', starting: 'Starting', running: 'Running', failed: 'Failed', completed: 'Completed', canceled: 'Canceled',
  }
  return labels[status] || status
}

function jobTone(status) {
  if (status === 'running') return 'pill--running'
  if (status === 'failed' || status === 'canceled') return 'pill--danger'
  if (status === 'queued' || status === 'starting') return 'pill--warning'
  return 'pill--muted'
}

async function refresh() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/system/worker')
    const payload = await response.json().catch(() => ({}))
    if (!response.ok || !payload.success) throw new Error(payload.error || 'Failed to load queue status.')
    data.value = payload.data
    updatedAt.value = new Date()
    now.value = Date.now()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
  pollTimer = window.setInterval(refresh, 5000)
  clockTimer = window.setInterval(() => { now.value = Date.now() }, 1000)
})

onUnmounted(() => {
  window.clearInterval(pollTimer)
  window.clearInterval(clockTimer)
})
</script>

<style scoped>
.queue-admin {
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

.icon-button:hover:not(:disabled) { border-color: var(--border-color-dark); color: var(--gray-900); }
.icon-button:disabled { cursor: wait; color: var(--gray-400); }

.queue-message {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 42px;
  padding: 8px 10px;
  margin-bottom: 16px;
  border: 1px solid #f0c7c3;
  border-radius: var(--radius-base);
  background: var(--error-50);
  color: var(--error-600);
  font-size: var(--text-xs);
}

.queue-message span { flex: 1; }
.queue-message button { border: 0; background: transparent; color: inherit; font-weight: var(--font-semibold); cursor: pointer; }

.queue-loading {
  display: grid;
  gap: 12px;
}

.queue-loading span {
  height: 70px;
  border-radius: var(--radius-base);
  background: var(--surface-2);
  animation: queue-pulse 1.2s ease-in-out infinite alternate;
}

.worker-banner {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  min-height: 66px;
  padding: 12px 14px;
  margin: 20px 0 18px;
  border: 1px solid #c9e7d8;
  border-radius: var(--radius-md);
  background: var(--success-50);
}

.worker-banner--offline {
  border-color: #f0c7c3;
  background: var(--error-50);
}

.worker-banner__icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: var(--radius-full);
  background: var(--surface-1);
  color: var(--success-600);
}

.worker-banner--offline .worker-banner__icon { color: var(--error-600); }

.worker-banner__copy {
  display: grid;
  min-width: 0;
}

.worker-banner__copy strong {
  color: var(--gray-900);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.worker-banner__copy span,
.worker-banner__heartbeat {
  margin-top: 2px;
  color: var(--gray-600);
  font-size: var(--text-xs);
}

.worker-banner__heartbeat {
  margin: 0;
  white-space: nowrap;
}

.queue-summary {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  margin-bottom: 30px;
  border-block: 1px solid var(--border-color);
}

.queue-summary article {
  min-width: 0;
  padding: 14px 16px;
  border-right: 1px solid var(--border-color-light);
}

.queue-summary article:last-child { border-right: 0; }
.queue-summary small,
.queue-summary strong { display: block; }
.queue-summary small { color: var(--gray-500); font-size: 11px; }
.queue-summary strong { margin-top: 3px; color: var(--gray-900); font-size: 18px; font-weight: var(--font-semibold); font-variant-numeric: tabular-nums; }
.queue-summary article.has-alert strong { color: var(--error-600); }

.queue-section {
  margin-top: 28px;
}

.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
}

.section-heading h2 { margin: 0; color: var(--gray-900); font-size: 16px; font-weight: var(--font-semibold); }
.section-heading p { margin: 3px 0 0; color: var(--gray-500); font-size: var(--text-xs); }
.section-heading > span { color: var(--gray-500); font-size: var(--text-xs); font-variant-numeric: tabular-nums; }

.job-table-wrap {
  overflow-x: auto;
}

.job-table {
  width: 100%;
  min-width: 660px;
  border-collapse: collapse;
}

.job-table th,
.job-table td {
  padding: 11px 8px;
  border-bottom: 1px solid var(--border-color-light);
  text-align: left;
  vertical-align: middle;
}

.job-table th { color: var(--gray-500); font-size: 11px; font-weight: var(--font-medium); }

.job-name { display: grid; }
.job-name strong { color: var(--gray-800); font-size: var(--text-xs); font-weight: var(--font-medium); }
.job-name code { margin-top: 2px; color: var(--gray-500); font-size: 11px; }
.job-worker { color: var(--gray-600); font-size: 11px; overflow-wrap: anywhere; }
.job-time { color: var(--gray-500); font-size: var(--text-xs); }

.queue-empty {
  display: flex;
  align-items: center;
  gap: 11px;
  min-height: 80px;
  padding: 14px 4px;
  border-bottom: 1px solid var(--border-color-light);
}

.queue-empty > span {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: var(--radius-full);
  background: var(--success-50);
  color: var(--success-600);
}

.queue-empty strong { display: block; color: var(--gray-800); font-size: var(--text-sm); font-weight: var(--font-medium); }
.queue-empty p { margin: 2px 0 0; color: var(--gray-500); font-size: var(--text-xs); }

.queue-section--attention .section-heading h2 { color: var(--error-600); }

.attention-row {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 9px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--border-color-light);
  color: var(--error-600);
}

.attention-row strong { color: var(--gray-800); font-size: var(--text-xs); font-weight: var(--font-medium); }
.attention-row p { margin: 2px 0 0; color: var(--gray-600); font-size: 11px; }

.worker-details {
  margin-top: 30px;
  border-block: 1px solid var(--border-color);
}

.worker-details summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 48px;
  color: var(--gray-700);
  cursor: pointer;
  list-style: none;
}

.worker-details summary::-webkit-details-marker { display: none; }
.worker-details summary > span { display: flex; align-items: center; gap: 8px; font-size: var(--text-xs); font-weight: var(--font-medium); }
.worker-details summary > :deep(svg) { color: var(--gray-400); transition: transform var(--transition-fast); }
.worker-details[open] summary > :deep(svg) { transform: rotate(180deg); }

.worker-details dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 28px;
  margin: 0;
  padding-bottom: 12px;
}

.worker-details dl div {
  display: flex;
  min-width: 0;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 0;
  border-top: 1px solid var(--border-color-light);
  font-size: var(--text-xs);
}

.worker-details dt { color: var(--gray-500); }
.worker-details dd { min-width: 0; margin: 0; overflow-wrap: anywhere; color: var(--gray-800); font-weight: var(--font-medium); text-align: right; }
.worker-details code { font-size: 11px; }

@keyframes queue-pulse { to { opacity: 0.45; } }

@media (max-width: 760px) {
  .queue-summary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .queue-summary article:nth-child(3) { border-right: 0; }
  .queue-summary article:nth-child(-n + 3) { border-bottom: 1px solid var(--border-color-light); }
  .worker-details dl { grid-template-columns: minmax(0, 1fr); }
}

@media (max-width: 520px) {
  .worker-banner {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .worker-banner__heartbeat {
    grid-column: 2;
  }

  .queue-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .queue-summary article,
  .queue-summary article:nth-child(3) {
    border-right: 1px solid var(--border-color-light);
    border-bottom: 1px solid var(--border-color-light);
  }

  .queue-summary article:nth-child(even) { border-right: 0; }
  .queue-summary article:last-child { border-bottom: 0; }
}
</style>
