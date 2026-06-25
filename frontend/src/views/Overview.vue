<template>
  <div class="overview-container">
    <div v-if="notifications.length" class="overview-toasts">
      <div v-for="notice in notifications" :key="notice.id" class="overview-toast" :class="notice.kind">
        <strong>{{ notice.title }}</strong>
        <span>{{ notice.message }}</span>
      </div>
    </div>
    <div class="overview-content">
      <!-- 项目基本信息卡片 -->
      <div class="overview-card">
        <div class="card-header">
          <div class="header-left">
            <h2>{{ project?.name || 'Loading...' }}</h2>
            <span class="project-id">ID: {{ $route.params.id }}</span>
          </div>
          <div class="header-actions">
            <router-link :to="`/workspace/${$route.params.id}/filemanager`" class="action-btn primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              Enter Workspace
            </router-link>
            <router-link :to="`/workspace/${$route.params.id}`" class="action-btn secondary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              Tool Library
            </router-link>
          </div>
        </div>
        
        <div class="project-details">
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">Creator</span>
              <span class="value">{{ project?.creator || 'Unknown' }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Created</span>
              <span class="value">{{ formatDate(project?.created_at) }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Last Accessed</span>
              <span class="value">{{ formatDate(project?.last_accessed) }}</span>
            </div>
            <div class="detail-item" v-if="project?.description">
              <span class="label">Description</span>
              <span class="value description">{{ project.description }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="overview-card dashboard-card">
        <div class="card-header">
          <h3>Workflow Readiness</h3>
          <button @click="fetchDashboard" class="refresh-btn" :class="{ loading: dashboardLoading }">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="m3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
          </button>
        </div>
        <div class="dashboard-grid">
          <div class="readiness-tile" :class="{ ok: dashboard?.readiness?.has_passed_preflight }">
            <span class="tile-label">Latest Preflight</span>
            <strong>{{ dashboard?.latest_preflight ? (dashboard.latest_preflight.ok ? 'Passed' : 'Failed') : 'Missing' }}</strong>
            <small>{{ formatDateTime(dashboard?.latest_preflight?.created_at) }}</small>
          </div>
          <div class="readiness-tile" :class="{ ok: dashboard?.readiness?.has_completed_run }">
            <span class="tile-label">Workflow Runs</span>
            <strong>{{ dashboard?.latest_run?.status ? getStatusText(dashboard.latest_run.status) : 'No Run' }}</strong>
            <small>{{ dashboard?.latest_run?.workflow_id || 'No workflow history' }}</small>
          </div>
          <div class="readiness-tile" :class="{ ok: dashboard?.readiness?.database_manifest_found }">
            <span class="tile-label">Database Manifest</span>
            <strong>{{ dashboard?.database_manifest?.found ? 'Recorded' : 'Inferred' }}</strong>
            <small>{{ dashboard?.readiness?.database_resources_present || 0 }}/{{ dashboard?.readiness?.database_resources_total || 0 }} resources</small>
          </div>
        </div>

        <div v-if="dashboardMetrics.length" class="metric-strip">
          <div v-for="metric in dashboardMetrics" :key="`${metric.group}-${metric.name}-${metric.sample_id}`" class="metric-chip">
            <span>{{ metric.group }} · {{ metric.name }}</span>
            <strong>{{ formatMetric(metric) }}</strong>
          </div>
        </div>

        <div v-if="dashboard?.recommendations?.length" class="dashboard-notes">
          <div v-for="note in dashboard.recommendations" :key="note" class="dashboard-note">{{ note }}</div>
        </div>
      </div>

      <!-- 系统性能监控 -->
      <SystemPerformance />

      <!-- 当前进程状态卡片 -->
      <div class="overview-card">
        <div class="card-header">
          <h3>Current Process Status</h3>
          <button @click="refreshStatus" class="refresh-btn" :class="{ loading: statusLoading }">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="m3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
          </button>
        </div>
        
        <div class="process-status">
          <div v-if="currentTask.status === 'not_found'" class="status-empty">
            <div class="empty-icon">⚡</div>
            <p>No running processes</p>
            <p class="sub-text">All tasks completed or not started yet</p>
          </div>
          
          <div v-else class="status-active">
            <div class="status-header">
              <div class="status-info">
                <div class="tool-name">{{ currentTask.tool }}</div>
                <div class="status-badge" :class="currentTask.status">
                  <span class="status-dot"></span>
                  {{ getStatusText(currentTask.status) }}
                </div>
              </div>
              <button
                v-if="['starting', 'running', 'queued'].includes(currentTask.status)"
                @click="viewLogs"
                class="logs-btn"
              >
                View Logs
              </button>
              <button
                v-if="currentTask.job_id && ['starting', 'running', 'queued'].includes(currentTask.status)"
                @click="cancelJob(currentTask.job_id)"
                class="logs-btn danger"
              >
                {{ currentTask.status === 'queued' ? 'Cancel' : 'Interrupt' }}
              </button>
            </div>

            <div v-if="currentTask.queue_position" class="queue-info">
              Queue position: {{ currentTask.queue_position }}
            </div>

            <div v-if="currentTask.status === 'starting' || currentTask.status === 'running'" class="queue-info">
              Worker: {{ currentTask.claimed_by || 'Awaiting claim' }}
              <span v-if="currentTask.pid" class="queue-info__mono">pid {{ currentTask.pid }}</span>
              <span v-if="currentTask.heartbeat_at" class="queue-info__mono">heartbeat {{ formatDateTime(currentTask.heartbeat_at) }}</span>
            </div>
            
            <div v-if="(currentTask.status === 'failed' || currentTask.status === 'canceled') && currentTask.error" class="error-info">
              <strong>Error:</strong>{{ currentTask.error }}
            </div>
            
            <div v-if="currentTask.status === 'failed' && currentTask.code" class="error-info">
              <strong>Exit Code:</strong>{{ currentTask.code }}
            </div>

            <div v-if="currentTask.failure_label" class="error-info soft">
              <strong>Failure Class:</strong>{{ currentTask.failure_label }}
            </div>

            <div v-if="currentTask.failure_suggestion" class="error-info soft">
              <strong>Suggested Fix:</strong>{{ currentTask.failure_suggestion }}
            </div>
          </div>
        </div>
      </div>

      <!-- 进程历史记录卡片 -->
      <div class="overview-card">
        <div class="card-header">
          <h3>Process History</h3>
          <div class="header-controls">
            <select v-model="historyFilter" class="filter-select">
              <option value="all">All Status</option>
              <option value="queued">Queued</option>
              <option value="starting">Starting</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="running">Running</option>
              <option value="canceled">Canceled</option>
            </select>
          </div>
        </div>
        
        <div class="history-list">
          <div v-if="historyLoading" class="history-loading">
            <div class="loading-spinner"></div>
            <p>Loading history...</p>
          </div>
          
          <div v-else-if="filteredHistory.length === 0" class="history-empty">
            <div class="empty-icon">📋</div>
            <p>No history records</p>
            <p class="sub-text">Process history will appear here after execution</p>
          </div>
          
          <div v-else>
            <div 
              v-for="item in filteredHistory" 
              :key="item.id" 
              class="history-item"
              @click="viewHistoryLogs(item)"
            >
              <div class="history-info">
                <div class="history-tool">{{ item.tool }}</div>
                <div class="history-time">{{ formatDateTime(item.timestamp) }}</div>
              </div>
              <div class="history-status">
                <div class="status-badge" :class="item.status">
                  <span class="status-dot"></span>
                  {{ getStatusText(item.status) }}
                </div>
                <div class="history-duration" v-if="item.duration">
                  {{ formatDuration(item.duration) }}
                </div>
                <button
                  v-if="['queued', 'starting', 'running'].includes(item.status)"
                  class="mini-action danger"
                  @click.stop="cancelJob(item.jobId)"
                >
                  {{ item.status === 'queued' ? 'Cancel' : 'Interrupt' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 日志查看模态框 -->
    <teleport to="body">
      <div v-if="showLogsModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="closeLogsModal">
        <div class="modal-content logs-modal app-modal" @click.stop>
          <div class="modal-header app-modal-header">
            <h3>{{ logsTitle }}</h3>
            <button @click="closeLogsModal" class="close-btn app-modal-close">×</button>
          </div>
          <div class="logs-content">

          
          <!-- 日志工具栏 -->
          <div v-if="logs.length > 0" class="logs-toolbar">
            <div class="toolbar-left">
              <span class="logs-count">{{ logs.length }} log lines</span>
              <button @click="clearLogs" class="clear-btn" title="Clear logs">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14z"></path>
                </svg>
              </button>
              <button @click="copyAllLogs" class="copy-btn" title="Copy all logs">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </div>
            <div class="toolbar-right">
              <label class="auto-scroll-toggle">
                <input type="checkbox" v-model="autoScroll" />
                <span>Auto Scroll</span>
              </label>
              <button @click="scrollToBottom" class="scroll-btn" title="Scroll to bottom">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M7 13l3 3 3-3m-3-9v12"></path>
                </svg>
              </button>
            </div>
          </div>
          
          <!-- 日志容器 -->
          <div v-if="logs.length === 0 && !logsLoading" class="logs-empty">
            <div class="empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
                <polyline points="10 9 9 9 8 9"></polyline>
              </svg>
              <p>No logs available</p>
              <span class="sub-text">Logs will appear when tools start executing</span>
            </div>
          </div>
          <div v-else class="logs-container" ref="logsContainer">
            <div 
              v-for="(log, index) in logs" 
              :key="index" 
              class="log-line"
              :class="getLogLineClass(log)"
              @click="selectLogLine(index)"
              :data-line-number="index + 1"
            >
              <span class="line-number">{{ (index + 1).toString().padStart(3, '0') }}</span>
              <span class="line-content">{{ formatLogContent(log) }}</span>
              <button class="copy-line-btn" @click.stop="copyLogLine(log)" title="Copy this line">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
              </button>
            </div>
            <!-- 新日志指示器 -->
            <div v-if="hasNewLogs && !autoScroll" class="new-logs-indicator" @click="scrollToBottom">
              <span>{{ newLogsCount }} new logs</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M7 13l3 3 3-3"></path>
              </svg>
            </div>
          </div>
        </div>
          <div class="modal-footer app-modal-footer">
            <button @click="exportLogs" class="export-btn">Export Logs</button>
            <button @click="closeLogsModal" class="close-modal-btn">Close</button>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import SystemPerformance from '@/components/SystemPerformance.vue'

const route = useRoute()
const projectId = computed(() => route.params.id)

// 项目信息
const project = ref(null)
const projectLoading = ref(true)
const dashboard = ref(null)
const dashboardLoading = ref(false)

// 当前进程状态
const currentTask = ref({ status: 'not_found', tool: null })
const statusLoading = ref(false)
const notifications = ref([])
const lastTaskFingerprint = ref('')

// 进程历史
const processHistory = ref([])
const historyFilter = ref('all')
const historyLoading = ref(false)

// 日志查看
const showLogsModal = ref(false)
const logs = ref([])
const logsTitle = ref('')
const logsLoading = ref(false)
let logPollTimer = null
const logOffset = ref(0)
const currentLogJobId = ref(null)
const logsContainer = ref(null)

// 日志交互
const autoScroll = ref(true)
const hasNewLogs = ref(false)
const newLogsCount = ref(0)
const lastScrollTop = ref(0)
const selectedLogLine = ref(-1)

const syncModalLock = (isOpen) => {
  document.body.classList.toggle('modal-open', isOpen)
}

// 计算属性
const filteredHistory = computed(() => {
  if (historyFilter.value === 'all') {
    return processHistory.value
  }
  return processHistory.value.filter(item => item.status === historyFilter.value)
})
const dashboardMetrics = computed(() => (dashboard.value?.metrics || []).slice(0, 8))

// 方法
const fetchProjectInfo = async () => {
  try {
    projectLoading.value = true
    const response = await fetch(`/api/projects/${projectId.value}`)
    if (response.ok) {
      project.value = await response.json()
    } else {
      console.error('Failed to fetch project info')
    }
  } catch (error) {
    console.error('Error fetching project info:', error)
  } finally {
    projectLoading.value = false
  }
}

const fetchCurrentStatus = async () => {
  try {
    const response = await fetch(`/api/pipeline/${projectId.value}/task-status`)
    if (response.ok) {
      const status = await response.json()
      currentTask.value = status
    }
  } catch (error) {
    console.error('Error fetching task status:', error)
  }
}

const fetchDashboard = async () => {
  try {
    dashboardLoading.value = true
    const response = await fetch(`/api/projects/${projectId.value}/dashboard`)
    if (response.ok) {
      dashboard.value = await response.json()
    }
  } catch (error) {
    console.error('Error fetching project dashboard:', error)
  } finally {
    dashboardLoading.value = false
  }
}

const fetchProcessHistory = async () => {
  try {
    historyLoading.value = true
    const response = await fetch(`/api/jobs?project_id=${projectId.value}&limit=20`)
    if (response.ok) {
      const payload = await response.json()
      const history = payload.jobs || []
      processHistory.value = history.map(item => ({
        id: item.id,
        jobId: item.id,
        tool: item.tool_name,
        status: item.status,
        timestamp: item.started_at || item.created_at,
        duration: item.duration,
        command: item.command,
        exitCode: item.exit_code,
        errorMessage: item.error_message,
        queuePosition: item.queue_position,
        failureLabel: item.failure_label,
        failureSuggestion: item.failure_suggestion,
      }))
    }
  } catch (error) {
    console.error('Error fetching process history:', error)
  } finally {
    historyLoading.value = false
  }
}

const refreshStatus = async () => {
  statusLoading.value = true
  await fetchCurrentStatus()
  setTimeout(() => {
    statusLoading.value = false
  }, 500)
}

const pushNotification = (title, message, kind = 'info') => {
  const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
  notifications.value.push({ id, title, message, kind })
  window.setTimeout(() => {
    notifications.value = notifications.value.filter(item => item.id !== id)
  }, 4200)
}

const cancelJob = async (jobId) => {
  try {
    const response = await fetch(`/api/jobs/${jobId}/interrupt`, { method: 'POST' })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(payload.error || 'Failed to cancel job')
    }
    pushNotification('Task Update', payload.message || 'Task interrupt requested', 'warning')
    await fetchCurrentStatus()
    await fetchProcessHistory()
  } catch (error) {
    pushNotification('Task Update', error.message || 'Failed to cancel job', 'error')
  }
}

const stopLogPolling = () => {
  if (logPollTimer) {
    clearInterval(logPollTimer)
    logPollTimer = null
  }
}

const pollLogs = async () => {
  if (!currentLogJobId.value) return
  try {
    const response = await fetch(`/api/jobs/${currentLogJobId.value}/logs?offset=${logOffset.value}`)
    if (!response.ok) return
    const data = await response.json()
    if (typeof data.offset === 'number') {
      logOffset.value = data.offset
    }
    if (data.content) {
      const lines = data.content.split('\n').filter(line => line !== '')
      if (lines.length > 0) {
        const wasAtBottom = isScrolledToBottom()
        let addedCount = 0
        lines.forEach(line => {
          if (!shouldFilterLog(line)) {
            logs.value.push(line)
            addedCount += 1
          }
        })
        if (addedCount > 0) {
          if (!autoScroll.value && !wasAtBottom) {
            hasNewLogs.value = true
            newLogsCount.value += addedCount
          }
          if (autoScroll.value || wasAtBottom) {
            setTimeout(scrollToBottom, 50)
          }
        }
      }
    }
    if (data.status && !['starting', 'running', 'queued'].includes(data.status)) {
      stopLogPolling()
      logsLoading.value = false
    }
  } catch (error) {
    console.error('Log polling failed:', error)
  }
}

const startLogPolling = () => {
  stopLogPolling()
  pollLogs()
  logPollTimer = setInterval(pollLogs, 2000)
}

const openLogsForJob = (jobId, title, shouldPoll) => {
  currentLogJobId.value = jobId
  logOffset.value = 0
  logsTitle.value = title
  logs.value = []
  showLogsModal.value = true
  logsLoading.value = true
  hasNewLogs.value = false
  newLogsCount.value = 0

  if (shouldPoll) {
    startLogPolling()
  } else {
    stopLogPolling()
    pollLogs().finally(() => {
      logsLoading.value = false
    })
  }
}

const viewLogs = () => {
  if (!currentTask.value.job_id) return
  const shouldPoll = ['starting', 'running', 'queued'].includes(currentTask.value.status)
  openLogsForJob(
    currentTask.value.job_id,
    `${currentTask.value.tool} - Live Logs`,
    shouldPoll
  )
}

watch(showLogsModal, (isOpen) => {
  syncModalLock(isOpen)
})

const isScrolledToBottom = () => {
  if (!logsContainer.value) return true
  const { scrollTop, scrollHeight, clientHeight } = logsContainer.value
  return Math.abs(scrollHeight - clientHeight - scrollTop) < 10
}

const scrollToBottom = () => {
  if (logsContainer.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
    hasNewLogs.value = false
    newLogsCount.value = 0
  }
}

const clearLogs = () => {
  if (confirm('Are you sure you want to clear all logs? This action cannot be undone.')) {
    logs.value = []
    hasNewLogs.value = false
    newLogsCount.value = 0
  }
}

const copyAllLogs = async () => {
  try {
    const logContent = logs.value.join('\n')
    await navigator.clipboard.writeText(logContent)
    // 可以添加一个临时提示
  } catch (error) {
    console.error('Copy failed:', error)
  }
}

const copyLogLine = async (log) => {
  try {
    await navigator.clipboard.writeText(log)
  } catch (error) {
    console.error('Copy failed:', error)
  }
}

const selectLogLine = (index) => {
  selectedLogLine.value = selectedLogLine.value === index ? -1 : index
}

const getLogLineClass = (log) => {
  const classes = []
  
  if (log.startsWith('[SYSTEM]')) {
    classes.push('system')
  } else if (log.startsWith('[ERROR]') || log.includes('error') || log.includes('Error')) {
    classes.push('error')
  } else if (log.startsWith('[WARN]') || log.includes('warning') || log.includes('Warning')) {
    classes.push('warning')
  } else if (log.startsWith('[INFO]') || log.includes('info')) {
    classes.push('info')
  } else if (log.startsWith('[DEBUG]') || log.includes('debug')) {
    classes.push('debug')
  }
  
  return classes
}

const formatLogContent = (log) => {
  // 移除时间戳和清理格式
  return log.replace(/^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]/, '').trim()
}



const viewHistoryLogs = (historyItem) => {
  if (!historyItem.jobId) return
  const shouldPoll = ['starting', 'running', 'queued'].includes(historyItem.status)
  openLogsForJob(
    historyItem.jobId,
    `${historyItem.tool} - History Logs`,
    shouldPoll
  )
}

const closeLogsModal = () => {
  showLogsModal.value = false
  
  stopLogPolling()
  currentLogJobId.value = null
  logOffset.value = 0
  
  // 重置状态
  logs.value = []
  logsLoading.value = false
  hasNewLogs.value = false
  newLogsCount.value = 0
  selectedLogLine.value = -1
  autoScroll.value = true
}

const exportLogs = () => {
  const logContent = logs.value.join('\n')
  const blob = new Blob([logContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${project.value?.name || 'project'}_logs_${new Date().toISOString().slice(0, 10)}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

const getStatusText = (status) => {
  const statusMap = {
    queued: 'Queued',
    starting: 'Starting',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    canceled: 'Canceled',
    not_found: 'No Task'
  }
  return statusMap[status] || status
}

const shouldFilterLog = (logData) => {
  if (!logData || typeof logData !== 'string') return false;
  
  // 过滤掉静默心跳
  if (logData.includes('[HEARTBEAT_SILENT]')) {
    return true;
  }
  
  // 过滤掉重复的系统状态消息
  if (logData.includes('[SYSTEM]')) {
    // 检查是否是重复的连接关闭消息
    if (logData.includes('Connection closed - no active tasks')) {
      const lastSystemMessage = logs.value
        .slice(-5) // 检查最近5条消息
        .reverse()
        .find(log => log && log.includes('[SYSTEM]'));
      
      if (lastSystemMessage && lastSystemMessage.includes('Connection closed')) {
        return true; // 过滤重复的连接关闭消息
      }
    }
    
    // 过滤掉过于频繁的 "Ready to receive" 消息
    if (logData.includes('Ready to receive new tasks')) {
      const recentReadyMessages = logs.value
        .slice(-3)
        .filter(log => log && log.includes('Ready to receive new tasks'));
      
      if (recentReadyMessages.length > 0) {
        return true; // 过滤重复的就绪消息
      }
    }
  }
  
  return false;
}

const formatDate = (dateString) => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const formatDateTime = (dateString) => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatDuration = (seconds) => {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${Math.round(seconds / 3600)}h`
}

const formatMetric = (metric) => {
  const value = metric.value
  const text = metric.text
  const unit = metric.unit || ''
  if (value !== null && value !== undefined && value !== '') {
    const numeric = Number(value)
    const formatted = Number.isFinite(numeric) ? (Math.abs(numeric) >= 10 ? numeric.toFixed(0) : numeric.toFixed(2)) : value
    return `${formatted}${unit}`
  }
  return text || 'Recorded'
}

// 定时刷新当前状态
let statusInterval = null

onMounted(() => {
  fetchProjectInfo()
  fetchDashboard()
  fetchCurrentStatus()
  fetchProcessHistory()
  
  // 每5秒刷新一次状态与历史
  statusInterval = setInterval(() => {
    fetchCurrentStatus()
    fetchDashboard()
    fetchProcessHistory()
  }, 5000)
})

onUnmounted(() => {
  if (statusInterval) {
    clearInterval(statusInterval)
  }
  stopLogPolling()
  syncModalLock(false)
})

watch(
  () => currentTask.value,
  (task) => {
    const fingerprint = [task?.job_id, task?.status, task?.tool].join(':')
    if (!task?.job_id || !task?.status || fingerprint === lastTaskFingerprint.value) {
      return
    }
    if (['completed', 'failed', 'canceled'].includes(task.status)) {
      const title = task.status === 'completed' ? 'Task Completed' : task.status === 'failed' ? 'Task Failed' : 'Task Canceled'
      const message = task.tool
        ? `${task.tool}${task.failure_label ? ` · ${task.failure_label}` : ''}`
        : 'Task updated'
      pushNotification(title, message, task.status === 'completed' ? 'success' : task.status === 'failed' ? 'error' : 'warning')
    }
    lastTaskFingerprint.value = fingerprint
  },
  { deep: true },
)
</script>

<style scoped>
.overview-container {
  min-height: 100%;
  background: var(--gray-50);
}

.overview-toasts {
  position: fixed;
  top: 86px;
  right: 24px;
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.overview-toast {
  min-width: 280px;
  max-width: 360px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.92);
  color: white;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.18);
}

.overview-toast.success { background: rgba(22, 101, 52, 0.94); }
.overview-toast.warning { background: rgba(146, 64, 14, 0.94); }
.overview-toast.error { background: rgba(153, 27, 27, 0.94); }

.overview-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-6);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

/* 卡片样式 */
.overview-card {
  background: white;
  border-radius: var(--radius-lg);
  padding: var(--spacing-6);
  box-shadow: var(--shadow-sm);
  border: var(--border-width) solid var(--border-color);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
  padding-bottom: var(--spacing-4);
  border-bottom: var(--border-width) solid var(--gray-200);
}

.header-left h2 {
  margin: 0;
  color: var(--gray-800);
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
}

.project-id {
  font-family: var(--font-family-mono);
  color: var(--gray-500);
  font-size: var(--text-sm);
  background: var(--gray-100);
  padding: var(--spacing-1) var(--spacing-2);
  border-radius: var(--radius-md);
  margin-left: var(--spacing-3);
}

.header-actions {
  display: flex;
  gap: var(--spacing-3);
}

.action-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-base);
}

.action-btn.primary {
  background: var(--primary-600);
  color: white;
}

.action-btn.primary:hover {
  background: var(--primary-700);
}

.action-btn.secondary {
  background: var(--gray-100);
  color: var(--gray-700);
}

.action-btn.secondary:hover {
  background: var(--gray-200);
}

/* 项目详情 */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-4);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.detail-item .label {
  font-size: var(--text-sm);
  color: var(--gray-600);
  font-weight: var(--font-medium);
}

.detail-item .value {
  color: var(--gray-800);
  font-size: var(--text-base);
}

.detail-item .value.description {
  grid-column: 1 / -1;
  margin-top: var(--spacing-2);
  padding: var(--spacing-3);
  background: var(--gray-50);
  border-radius: var(--radius-md);
  border-left: 4px solid var(--primary-500);
}

.dashboard-card {
  display: grid;
  gap: var(--spacing-4);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--spacing-3);
}

.readiness-tile {
  display: grid;
  gap: var(--spacing-1);
  padding: var(--spacing-4);
  border-radius: var(--radius-md);
  background: var(--gray-50);
  border: var(--border-width) solid var(--gray-200);
}

.readiness-tile.ok {
  background: var(--success-50);
  border-color: rgba(34, 197, 94, 0.18);
}

.tile-label {
  color: var(--gray-500);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
}

.readiness-tile strong {
  color: var(--gray-800);
  font-size: var(--text-xl);
}

.readiness-tile small {
  color: var(--gray-500);
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--spacing-2);
}

.metric-chip {
  display: grid;
  gap: 2px;
  padding: var(--spacing-3);
  border-radius: var(--radius-md);
  background: rgba(37, 99, 235, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.12);
}

.metric-chip span {
  color: var(--gray-600);
  font-size: var(--text-xs);
}

.metric-chip strong {
  color: var(--primary-700);
}

.dashboard-notes {
  display: grid;
  gap: var(--spacing-2);
}

.dashboard-note {
  padding: var(--spacing-3);
  border-radius: var(--radius-md);
  background: var(--warning-50);
  color: var(--warning-700);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

/* 进程状态 */
.card-header h3 {
  margin: 0;
  color: var(--gray-700);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: var(--gray-100);
  color: var(--gray-600);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
}

.refresh-btn:hover {
  background: var(--gray-200);
}

.refresh-btn.loading svg {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.status-empty {
  text-align: center;
  padding: var(--spacing-8) var(--spacing-4);
  color: var(--gray-500);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-3);
}

.sub-text {
  font-size: var(--text-sm);
  color: var(--gray-400);
  margin-top: var(--spacing-1);
}

.status-active {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.queue-info {
  color: var(--gray-600);
  font-size: var(--text-sm);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-3);
}

.queue-info__mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.tool-name {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--gray-800);
}

.status-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-xl);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.status-badge.running {
  background: var(--primary-100);
  color: var(--primary-700);
}

.status-badge.starting {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.status-badge.completed {
  background: var(--success-50);
  color: var(--success-600);
}

.status-badge.failed {
  background: var(--error-50);
  color: var(--error-600);
}

.status-badge.queued {
  background: var(--warning-50);
  color: var(--warning-600);
}

.status-badge.canceled {
  background: var(--gray-100);
  color: var(--gray-600);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-badge.running .status-dot {
  background: var(--primary-500);
  animation: pulse 2s infinite;
}

.status-badge.starting .status-dot {
  background: #1d4ed8;
  animation: pulse 1.4s infinite;
}

.status-badge.completed .status-dot {
  background: var(--success-500);
}

.status-badge.failed .status-dot {
  background: var(--error-500);
}

.status-badge.queued .status-dot {
  background: var(--warning-500);
}

.status-badge.canceled .status-dot {
  background: var(--gray-500);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.logs-btn {
  background: var(--primary-600);
  color: white;
  border: none;
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--transition-base);
}

.logs-btn:hover {
  background: var(--primary-700);
}

.logs-btn.danger {
  background: var(--error-50);
  color: var(--error-700);
}

.logs-btn.danger:hover {
  background: var(--error-100);
}

.error-info {
  padding: var(--spacing-3);
  background: var(--error-50);
  border: var(--border-width) solid var(--error-200);
  border-radius: var(--radius-md);
  color: var(--error-700);
  font-size: var(--text-sm);
}

.error-info.soft {
  background: var(--gray-100);
  border-color: var(--gray-200);
  color: var(--gray-700);
}

/* 历史记录 */
.header-controls {
  display: flex;
  gap: var(--spacing-3);
}

.filter-select {
  padding: var(--spacing-1) var(--spacing-3);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-md);
  background: white;
  font-size: var(--text-sm);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.history-loading {
  text-align: center;
  padding: var(--spacing-8) var(--spacing-4);
  color: var(--gray-500);
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--gray-200);
  border-top: 2px solid var(--primary-500);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto var(--spacing-3);
}

.history-empty {
  text-align: center;
  padding: var(--spacing-8) var(--spacing-4);
  color: var(--gray-500);
}

.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3);
  border: var(--border-width) solid var(--gray-200);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-base);
}

.history-item:hover {
  background: var(--gray-50);
  border-color: var(--gray-300);
}

.history-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.history-tool {
  font-weight: var(--font-medium);
  color: var(--gray-800);
}

.history-time {
  font-size: var(--text-sm);
  color: var(--gray-500);
}

.history-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--spacing-1);
}

.mini-action {
  border: none;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.mini-action.danger {
  background: var(--error-50);
  color: var(--error-700);
}

.history-duration {
  font-size: var(--text-xs);
  color: var(--gray-400);
}

/* 日志模态框 */
.logs-modal {
  width: 95vw;
  max-width: 1000px;
  max-height: 85vh;
  height: 75vh;
  overflow: hidden;
}

.logs-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.logs-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--gray-500);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-8);
}

.empty-state svg {
  color: var(--gray-300);
  margin-bottom: var(--spacing-4);
}

.empty-state p {
  margin: 0 0 var(--spacing-2) 0;
  font-size: var(--text-lg);
  font-weight: var(--font-medium);
  color: var(--gray-600);
}

.empty-state .sub-text {
  font-size: var(--text-sm);
  color: var(--gray-400);
}

.logs-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-4);
  font-family: var(--font-family-mono);
  font-size: var(--text-sm);
  line-height: 1.5;
  /* 优化滚动性能 */
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  transform: translateZ(0);
  /* 自定义滚动条样式 */
  scrollbar-width: thin;
  scrollbar-color: var(--gray-400) var(--surface-2);
}

.logs-container::-webkit-scrollbar {
  width: 6px;
}

.logs-container::-webkit-scrollbar-track {
  background: var(--surface-2);
  border-radius: var(--radius-sm);
}

.logs-container::-webkit-scrollbar-thumb {
  background: var(--gray-400);
  border-radius: var(--radius-sm);
  transition: background var(--transition-base);
}

.logs-container::-webkit-scrollbar-thumb:hover {
  background: var(--gray-500);
}



/* 日志工具栏 */
.logs-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: var(--border-width) solid var(--border-color);
  background: var(--gray-50);
  font-size: var(--text-sm);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.logs-count {
  color: var(--gray-600);
  font-weight: var(--font-medium);
}

.clear-btn, .copy-btn, .scroll-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: white;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--gray-600);
  cursor: pointer;
  transition: all var(--transition-base);
}

.clear-btn:hover, .copy-btn:hover, .scroll-btn:hover {
  background: var(--gray-100);
  border-color: var(--gray-300);
  color: var(--gray-700);
}

.auto-scroll-toggle {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--gray-600);
}

.auto-scroll-toggle input[type="checkbox"] {
  width: 14px;
  height: 14px;
}

/* 改进的日志行样式 */
.log-line {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-2);
  padding: var(--spacing-1) var(--spacing-2);
  margin-bottom: 1px;
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
  font-size: var(--text-sm);
  line-height: 1.4;
  word-wrap: break-word;
  transition: all var(--transition-base);
  cursor: pointer;
}

.log-line:hover {
  background: var(--gray-50);
}

.log-line:hover .copy-line-btn {
  opacity: 1;
}

.line-number {
  color: var(--gray-400);
  font-size: var(--text-xs);
  min-width: 32px;
  text-align: right;
  user-select: none;
  flex-shrink: 0;
}

.line-content {
  flex: 1;
  color: var(--gray-700);
}

.copy-line-btn {
  opacity: 0;
  width: 20px;
  height: 20px;
  border: none;
  background: var(--gray-200);
  border-radius: var(--radius-sm);
  color: var(--gray-600);
  cursor: pointer;
  transition: all var(--transition-base);
  flex-shrink: 0;
  margin-left: auto;
}

.copy-line-btn:hover {
  background: var(--gray-300);
  color: var(--gray-700);
}

/* 日志行类型样式 */
.log-line.system .line-content {
  color: var(--primary-600);
  font-weight: var(--font-medium);
}

.log-line.error {
  background: var(--error-50);
  border-left: 3px solid var(--error-500);
}

.log-line.error .line-content {
  color: var(--error-700);
}

.log-line.warning {
  background: var(--warning-50);
  border-left: 3px solid var(--warning-500);
}

.log-line.warning .line-content {
  color: var(--warning-700);
}

.log-line.info .line-content {
  color: var(--primary-700);
}

.log-line.debug .line-content {
  color: var(--gray-500);
  font-style: italic;
}

/* 新日志指示器 */
.new-logs-indicator {
  position: sticky;
  bottom: var(--spacing-4);
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  background: var(--primary-600);
  color: white;
  border-radius: var(--radius-xl);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  margin: var(--spacing-4) auto 0;
  width: fit-content;
  box-shadow: var(--shadow-lg);
  animation: bounceIn 0.3s ease-out;
}

.new-logs-indicator:hover {
  background: var(--primary-700);
  transform: translateY(-2px);
  box-shadow: var(--shadow-xl);
}

@keyframes bounceIn {
  from {
    transform: translateY(10px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.export-btn {
  background: var(--surface-1);
  color: var(--gray-700);
  border: var(--border-width) solid var(--border-color);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  cursor: pointer;
}

.export-btn:hover {
  background: var(--surface-3);
}

.close-modal-btn {
  background: var(--gradient-primary);
  color: white;
  border: none;
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  cursor: pointer;
}

.close-modal-btn:hover {
  background: linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .overview-content {
    padding: var(--spacing-4);
    gap: var(--spacing-4);
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-3);
  }
  
  .header-actions {
    width: 100%;
    justify-content: stretch;
  }
  
  .action-btn {
    flex: 1;
    justify-content: center;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .status-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-3);
  }
  
  .history-item {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-2);
  }
  
  .history-status {
    align-items: flex-start;
  }
  
  .logs-modal {
    width: 95vw;
    height: 90vh;
    margin: var(--spacing-4);
  }
}
</style> 
