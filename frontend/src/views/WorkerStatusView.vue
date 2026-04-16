<template>
  <div class="worker-status">
    <header class="worker-status__hero">
      <div>
        <div class="worker-status__kicker">Execution Runtime</div>
        <h1>Local Worker Status</h1>
        <p>Monitor the embedded database-backed executor, active jobs, queue depth, and stale-job recovery.</p>
      </div>
      <button class="worker-status__refresh" type="button" @click="refresh" :disabled="loading">
        {{ loading ? 'Refreshing...' : 'Refresh' }}
      </button>
    </header>

    <div v-if="error" class="worker-status__error">{{ error }}</div>

    <section v-if="data" class="worker-status__grid">
      <article class="worker-card worker-card--summary">
        <div class="worker-card__top">
          <h2>Worker</h2>
          <span class="worker-pill" :class="data.embedded_worker_running ? 'ok' : 'idle'">
            {{ data.embedded_worker_running ? 'Running' : 'Stopped' }}
          </span>
        </div>
        <dl class="worker-meta">
          <div><dt>Mode</dt><dd>{{ data.mode }}</dd></div>
          <div><dt>Worker ID</dt><dd class="mono">{{ data.worker.worker_id }}</dd></div>
          <div><dt>Host</dt><dd>{{ data.worker.host }}</dd></div>
          <div><dt>Started</dt><dd>{{ formatDateTime(data.worker.started_at) }}</dd></div>
          <div><dt>Heartbeat</dt><dd>{{ formatDateTime(data.worker.last_heartbeat_at) }}</dd></div>
          <div><dt>Current Job</dt><dd class="mono">{{ data.worker.current_job_id || 'Idle' }}</dd></div>
          <div><dt>Last Claimed</dt><dd>{{ formatDateTime(data.worker.last_claimed_at) }}</dd></div>
          <div><dt>Last Idle</dt><dd>{{ formatDateTime(data.worker.last_idle_at) }}</dd></div>
          <div><dt>Poll Interval</dt><dd>{{ data.poll_interval_seconds }}s</dd></div>
          <div><dt>Stale Timeout</dt><dd>{{ data.stale_timeout_seconds }}s</dd></div>
          <div><dt>Recovered</dt><dd>{{ data.worker.recovered_jobs }}</dd></div>
        </dl>
        <p v-if="data.worker.last_error" class="worker-card__error">
          Last error: {{ data.worker.last_error }}
        </p>
      </article>

      <article class="worker-card">
        <h2>Queue Overview</h2>
        <div class="worker-counts">
          <div class="worker-count">
            <strong>{{ data.counts.queued }}</strong>
            <span>Queued</span>
          </div>
          <div class="worker-count">
            <strong>{{ data.counts.starting }}</strong>
            <span>Starting</span>
          </div>
          <div class="worker-count">
            <strong>{{ data.counts.running }}</strong>
            <span>Running</span>
          </div>
          <div class="worker-count">
            <strong>{{ data.counts.failed }}</strong>
            <span>Failed</span>
          </div>
          <div class="worker-count">
            <strong>{{ data.counts.completed }}</strong>
            <span>Completed</span>
          </div>
          <div class="worker-count">
            <strong>{{ data.counts.canceled }}</strong>
            <span>Canceled</span>
          </div>
        </div>
      </article>

      <article class="worker-card">
        <div class="worker-card__top">
          <h2>Stale Jobs</h2>
          <span class="worker-pill subtle">{{ data.stale_jobs.length }}</span>
        </div>
        <div v-if="data.stale_jobs.length === 0" class="worker-empty">No stale jobs detected.</div>
        <div v-else class="worker-list">
          <div v-for="job in data.stale_jobs" :key="job.id" class="worker-row">
            <div>
              <strong>{{ job.tool_name }}</strong>
              <div class="mono">{{ job.id }}</div>
            </div>
            <div class="worker-row__meta">
              <span class="worker-pill warning">{{ job.status }}</span>
              <span class="mono">pid {{ job.pid || 'n/a' }}</span>
            </div>
          </div>
        </div>
      </article>

      <article class="worker-card worker-card--wide">
        <div class="worker-card__top">
          <h2>Active Jobs</h2>
          <span class="worker-pill subtle">{{ data.active_jobs.length }}</span>
        </div>
        <div v-if="data.active_jobs.length === 0" class="worker-empty">No queued or running jobs.</div>
        <div v-else class="worker-table">
          <div class="worker-table__head">
            <span>Tool</span>
            <span>Status</span>
            <span>Claim</span>
            <span>Heartbeat</span>
          </div>
          <div v-for="job in data.active_jobs" :key="job.id" class="worker-table__row">
            <span>
              <strong>{{ job.tool_name }}</strong>
              <small class="mono">{{ job.id }}</small>
            </span>
            <span class="worker-pill" :class="job.status">{{ humanize(job.status) }}</span>
            <span class="mono">{{ job.claimed_by || 'Unclaimed' }}</span>
            <span>{{ formatDateTime(job.heartbeat_at || job.started_at || job.created_at) }}</span>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'

const data = ref(null)
const error = ref('')
const loading = ref(false)
let pollTimer = null

function formatDateTime(value) {
  if (!value) return 'Unknown'
  const date = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function humanize(status) {
  const map = {
    queued: 'Queued',
    starting: 'Starting',
    running: 'Running',
    failed: 'Failed',
    completed: 'Completed',
    canceled: 'Canceled',
  }
  return map[status] || status
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/system/worker')
    const payload = await response.json()
    if (!response.ok || !payload.success) {
      throw new Error(payload.error || 'Failed to load worker status')
    }
    data.value = payload.data
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  refresh()
  pollTimer = window.setInterval(refresh, 5000)
})

onUnmounted(() => {
  if (pollTimer) window.clearInterval(pollTimer)
})
</script>

<style scoped>
.worker-status {
  max-width: 1180px;
  margin: 0 auto;
  height: calc(100vh - var(--header-height));
  overflow-y: auto;
  overflow-x: hidden;
  padding: 2rem 1.5rem 2rem;
  box-sizing: border-box;
}

.worker-status__hero {
  display: flex;
  justify-content: space-between;
  gap: 1.5rem;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.worker-status__kicker {
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.worker-status__hero h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3rem);
  color: #111827;
}

.worker-status__hero p {
  margin: 0.6rem 0 0;
  max-width: 54rem;
  color: #6b7280;
  line-height: 1.6;
}

.worker-status__refresh {
  border: 1px solid #d7dce7;
  background: #fff;
  border-radius: 999px;
  padding: 0.8rem 1.25rem;
  font-weight: 700;
  color: #1f2937;
}

.worker-status__grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 1rem;
}

.worker-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 24px;
  padding: 1.25rem;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.06);
}

.worker-card--summary,
.worker-card--wide {
  grid-column: span 2;
}

.worker-card__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.worker-card h2 {
  margin: 0;
  font-size: 1.05rem;
  color: #111827;
}

.worker-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.32rem 0.7rem;
  font-size: 0.82rem;
  font-weight: 700;
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
}

.worker-pill.ok,
.worker-pill.running {
  background: rgba(16, 185, 129, 0.12);
  color: #047857;
}

.worker-pill.idle,
.worker-pill.queued,
.worker-pill.starting,
.worker-pill.warning {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

.worker-pill.failed,
.worker-pill.canceled {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.worker-pill.subtle {
  background: rgba(15, 23, 42, 0.06);
  color: #475569;
}

.worker-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem 1rem;
  margin: 0;
}

.worker-meta div {
  display: grid;
  gap: 0.25rem;
}

.worker-meta dt {
  color: #6b7280;
  font-size: 0.82rem;
}

.worker-meta dd {
  margin: 0;
  color: #111827;
  font-weight: 600;
}

.worker-counts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
}

.worker-count {
  border: 1px solid #e5e7eb;
  border-radius: 18px;
  padding: 1rem;
  display: grid;
  gap: 0.25rem;
}

.worker-count strong {
  font-size: 1.6rem;
  color: #111827;
}

.worker-count span {
  color: #6b7280;
}

.worker-list {
  display: grid;
  gap: 0.85rem;
}

.worker-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9rem 0;
  border-top: 1px solid #eef2f7;
}

.worker-row:first-child {
  border-top: 0;
  padding-top: 0;
}

.worker-row__meta {
  display: flex;
  gap: 0.65rem;
  align-items: center;
}

.worker-table {
  display: grid;
}

.worker-table__head,
.worker-table__row {
  display: grid;
  grid-template-columns: 1.5fr 0.9fr 1.2fr 1fr;
  gap: 1rem;
  align-items: center;
}

.worker-table__head {
  color: #6b7280;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e5e7eb;
}

.worker-table__row {
  padding: 0.9rem 0;
  border-bottom: 1px solid #eef2f7;
}

.worker-table__row:last-child {
  border-bottom: 0;
}

.worker-table__row span {
  display: grid;
  gap: 0.2rem;
  color: #111827;
}

.worker-table__row small {
  color: #6b7280;
}

.worker-status__error,
.worker-card__error,
.worker-empty {
  color: #b91c1c;
  background: rgba(254, 242, 242, 0.9);
  border: 1px solid rgba(248, 113, 113, 0.25);
  border-radius: 18px;
  padding: 0.9rem 1rem;
}

.worker-empty {
  color: #6b7280;
  background: rgba(248, 250, 252, 0.92);
  border-color: #e5e7eb;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

@media (max-width: 920px) {
  .worker-status__grid {
    grid-template-columns: 1fr;
  }

  .worker-card--summary,
  .worker-card--wide {
    grid-column: span 1;
  }

  .worker-meta,
  .worker-counts,
  .worker-table__head,
  .worker-table__row {
    grid-template-columns: 1fr;
  }
}
</style>
