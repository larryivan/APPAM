<template>
  <div class="download-manager" :class="{ 'minimized': isMinimized }">
    <!-- 头部控制栏 -->
    <div class="download-header">
      <div class="header-left">
        <Icon class="download-icon" name="download" :size="18" />
        <span class="header-title">Download Manager</span>
        <span class="download-count" v-if="downloadTasks.length">{{ activeDownloads }}/{{ downloadTasks.length }}</span>
      </div>
      <div class="header-controls">
        <button @click="showAddUrlModal = true" class="control-btn add-btn" title="Add Download">
          <Icon name="plus" :size="16" />
        </button>
        <button @click="pauseAll" class="control-btn" title="Pause All" v-if="activeDownloads > 0">
          <Icon name="pause" :size="16" />
        </button>
        <button @click="resumeAll" class="control-btn" title="Resume All" v-if="pausedDownloads > 0">
          <Icon name="play" :size="16" />
        </button>
        <button @click="clearCompleted" class="control-btn" title="Clear Finished" v-if="finishedDownloads > 0">
          <Icon name="trash-2" :size="16" />
        </button>
        <button @click="toggleMinimize" class="control-btn" :title="isMinimized ? 'Expand' : 'Minimize'">
          <Icon :name="isMinimized ? 'chevron-down' : 'chevron-up'" :size="16" />
        </button>
        <button @click="$emit('close')" class="control-btn close-btn" title="Close" aria-label="Close download manager">
          <Icon name="x" :size="16" />
        </button>
      </div>
    </div>

    <!-- 下载列表 -->
    <div class="download-content" v-if="!isMinimized">
      <div v-if="downloadTasks.length === 0" class="empty-downloads">
        <Icon class="empty-icon" name="download" :size="36" :stroke-width="1.5" />
        <div class="empty-text">No download tasks</div>
        <div class="empty-subtext">Click the + button to add URL downloads</div>
      </div>

      <div v-else class="download-list">
        <div 
          v-for="task in downloadTasks" 
          :key="task.id" 
          class="download-item" 
          :class="task.status"
        >
          <!-- 文件信息 -->
          <div class="download-info">
            <div class="file-icon">
              <Icon name="file" :size="21" />
            </div>
            <div class="file-details">
              <div class="file-name" :title="task.filename">{{ task.filename }}</div>
              <div class="file-meta">
                <span class="file-size">{{ formatSize(task.totalSize) }}</span>
                <span class="download-speed" v-if="task.status === 'downloading'">{{ formatSpeed(task.speed) }}</span>
                <span class="time-remaining" v-if="task.status === 'downloading' && task.timeRemaining">{{ formatTime(task.timeRemaining) }}</span>
              </div>
            </div>
          </div>

          <!-- 进度条 -->
          <div class="download-progress">
            <div class="progress-info">
              <span class="progress-text">{{ getProgressText(task) }}</span>
              <span class="progress-percent">{{ Math.round(task.progress) }}%</span>
            </div>
            <div class="progress-bar">
              <div 
                class="progress-fill" 
                :style="{ width: task.progress + '%' }"
                :class="task.status"
              ></div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="download-actions">
            <!-- 下载中 -->
            <button 
              v-if="task.status === 'downloading'" 
              @click="pauseDownload(task.id)"
              class="action-btn pause-btn"
              title="Pause"
            >
              <Icon name="pause" :size="14" />
            </button>

            <!-- 暂停中 -->
            <button 
              v-if="task.status === 'paused'" 
              @click="resumeDownload(task.id)"
              class="action-btn resume-btn"
              title="Resume"
            >
              <Icon name="play" :size="14" />
            </button>

            <!-- 错误状态 -->
            <button 
              v-if="task.status === 'error'" 
              @click="retryDownload(task.id)"
              class="action-btn retry-btn"
              title="Retry"
            >
              <Icon name="rotate-ccw" :size="14" />
            </button>

            <!-- 完成状态 -->
            <button 
              v-if="task.status === 'completed'" 
              @click="openFile(task)"
              class="action-btn open-btn"
              title="Open File"
            >
              <Icon name="external-link" :size="14" />
            </button>

            <!-- 删除按钮 -->
            <button 
              @click="removeDownload(task.id)" 
              class="action-btn remove-btn"
              title="Delete"
            >
              <Icon name="trash-2" :size="14" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加URL模态框 -->
    <div v-if="showAddUrlModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="showAddUrlModal = false">
      <div class="app-modal download-modal" @click.stop ref="addUrlPanel" role="dialog" aria-modal="true" aria-label="Add download URL" tabindex="-1">
        <div class="modal-header app-modal-header">
          <h3>Add download link</h3>
          <button @click="showAddUrlModal = false" class="close-btn app-modal-close" title="Close" aria-label="Close dialog">
            <Icon name="x" :size="18" />
          </button>
        </div>
        <div class="modal-body app-modal-body">
          <div class="input-group">
            <label>Download Link</label>
            <input 
              v-model="newDownloadUrl" 
              placeholder="https://example.org/data.fastq.gz"
              class="url-input"
              @keyup.enter="addDownload"
            />
          </div>
          <div class="input-group">
            <label>Filename (Optional)</label>
            <input 
              v-model="newDownloadFilename" 
              placeholder="Leave blank to auto-extract from URL" 
              class="filename-input"
            />
          </div>
          <div class="download-options">
            <label class="checkbox-label">
              <input type="checkbox" v-model="enableConcurrentDownload" />
              <span class="checkmark"></span>
              Enable multi-threaded download for large files
            </label>
          </div>
        </div>
        <div class="modal-footer app-modal-footer">
          <button @click="addDownload" class="btn-primary" :disabled="!newDownloadUrl.trim()">
            Start Download
          </button>
          <button @click="showAddUrlModal = false" class="btn-cancel">
            Cancel
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useOverlay } from '@/lib/overlay.js'

const props = defineProps({
  projectId: {
    type: String,
    required: true
  },
  currentPath: {
    type: String,
    default: '/'
  }
})

const emit = defineEmits(['close', 'file-downloaded'])

// 状态管理
const downloadTasks = ref([])
const isMinimized = ref(false)
const showAddUrlModal = ref(false)

const addUrlPanel = ref(null)
useOverlay(() => showAddUrlModal.value, { onClose: () => { showAddUrlModal.value = false }, panelRef: addUrlPanel })
const newDownloadUrl = ref('')
const newDownloadFilename = ref('')
const enableConcurrentDownload = ref(true)
const pollTimers = new Map()

// 下载状态统计
const activeDownloads = computed(() => 
  downloadTasks.value.filter(task => ['preparing', 'downloading'].includes(task.status)).length
)
const pausedDownloads = computed(() => 
  downloadTasks.value.filter(task => task.status === 'paused').length
)
const finishedDownloads = computed(() =>
  downloadTasks.value.filter(task => ['completed', 'error', 'cancelled'].includes(task.status)).length
)

const clearPollTimer = (taskId) => {
  const timer = pollTimers.get(taskId)
  if (timer) window.clearTimeout(timer)
  pollTimers.delete(taskId)
}

const schedulePoll = (taskId, delay = 1000) => {
  clearPollTimer(taskId)
  pollTimers.set(taskId, window.setTimeout(() => pollDownloadProgress(taskId), delay))
}

// 方法
const addDownload = async () => {
  if (!newDownloadUrl.value.trim()) return
  
  const url = newDownloadUrl.value.trim()
  const isFtp = url.toLowerCase().startsWith('ftp://')
  const taskId = Date.now().toString()
  
  const task = {
    id: taskId,
    url: url,
    filename: newDownloadFilename.value.trim() || extractFilenameFromUrl(url),
    status: 'preparing',
    progress: 0,
    downloadedSize: 0,
    totalSize: 0,
    speed: 0,
    timeRemaining: null,
    startTime: Date.now(),
    path: props.currentPath,
    concurrent: isFtp ? false : enableConcurrentDownload.value  // Force single-threaded for FTP
  }
  
  downloadTasks.value.unshift(task)
  showAddUrlModal.value = false
  newDownloadUrl.value = ''
  newDownloadFilename.value = ''
  
  await startDownload(taskId)
}

const startDownload = async (taskId) => {
  const task = downloadTasks.value.find(t => t.id === taskId)
  if (!task) return
  
  try {
    task.status = 'downloading'
    
    const response = await fetch(`/api/filemanager/${props.projectId}/download-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: task.url,
        filename: task.filename,
        path: task.path || props.currentPath,
        concurrent: task.concurrent
      })
    })

    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.error || `HTTP error! status: ${response.status}`)
    }

    task.id = payload.task_id
    // 开始轮询下载进度
    pollDownloadProgress(payload.task_id)
    
  } catch (error) {
    console.error('Download error:', error)
    task.status = 'error'
    task.error = error.message
  }
}

const pollDownloadProgress = async (taskId) => {
  const task = downloadTasks.value.find(t => t.id === taskId)
  if (!task || ['completed', 'error', 'cancelled', 'paused'].includes(task.status)) {
    clearPollTimer(taskId)
    return
  }
  
  try {
    const response = await fetch(`/api/filemanager/${props.projectId}/download-progress/${taskId}`)
    if (!response.ok) return
    
    const progress = await response.json()
    
    // 更新任务状态
    Object.assign(task, {
      progress: progress.progress || 0,
      downloadedSize: progress.downloaded_size || 0,
      totalSize: progress.total_size || 0,
      speed: progress.speed || 0,
      timeRemaining: progress.time_remaining,
      status: progress.status || task.status
    })
    
    if (task.status === 'completed') {
      emit('file-downloaded', task.filename)
    } else if (task.status === 'downloading' || task.status === 'preparing') {
      schedulePoll(taskId)
    }
    
  } catch (error) {
    console.error('Progress polling error:', error)
    schedulePoll(taskId, 2000)
  }
}

const pauseDownload = async (taskId) => {
  try {
    const response = await fetch(`/api/filemanager/${props.projectId}/download-pause/${taskId}`, {
      method: 'POST'
    })
    if (!response.ok) throw new Error('Failed to pause download')
    const task = downloadTasks.value.find(t => t.id === taskId)
    if (task) task.status = 'paused'
    clearPollTimer(taskId)
  } catch (error) {
    console.error('Pause error:', error)
  }
}

const resumeDownload = async (taskId) => {
  try {
    const response = await fetch(`/api/filemanager/${props.projectId}/download-resume/${taskId}`, {
      method: 'POST'
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'Failed to resume download')
    const task = downloadTasks.value.find(t => t.id === taskId)
    if (task) {
      task.status = 'downloading'
      pollDownloadProgress(taskId)
    }
  } catch (error) {
    console.error('Resume error:', error)
  }
}

const retryDownload = async (taskId) => {
  const task = downloadTasks.value.find(t => t.id === taskId)
  if (task) {
    await fetch(`/api/filemanager/${props.projectId}/download-cancel/${taskId}`, { method: 'POST' })
    clearPollTimer(taskId)
    task.status = 'preparing'
    task.progress = 0
    task.downloadedSize = 0
    task.error = null
    await startDownload(taskId)
  }
}

const removeDownload = async (taskId) => {
  try {
    await fetch(`/api/filemanager/${props.projectId}/download-cancel/${taskId}`, {
      method: 'POST'
    })
  } catch (error) {
    console.error('Cancel error:', error)
  } finally {
    clearPollTimer(taskId)
    const index = downloadTasks.value.findIndex(t => t.id === taskId)
    if (index > -1) downloadTasks.value.splice(index, 1)
  }
}

const pauseAll = () => {
  downloadTasks.value
    .filter(task => task.status === 'downloading')
    .forEach(task => pauseDownload(task.id))
}

const resumeAll = () => {
  downloadTasks.value
    .filter(task => task.status === 'paused')
    .forEach(task => resumeDownload(task.id))
}

const clearCompleted = async () => {
  try {
    const response = await fetch(`/api/filemanager/${props.projectId}/download-cleanup`, { method: 'POST' })
    if (!response.ok) throw new Error('Failed to clear download history')
    downloadTasks.value
      .filter(task => ['completed', 'error', 'cancelled'].includes(task.status))
      .forEach(task => clearPollTimer(task.id))
    downloadTasks.value = downloadTasks.value.filter(
      task => !['completed', 'error', 'cancelled'].includes(task.status)
    )
  } catch (error) {
    console.error('Download cleanup error:', error)
  }
}

const openFile = (task) => {
  emit('file-downloaded', task.filename)
}

const toggleMinimize = () => {
  isMinimized.value = !isMinimized.value
}

// 工具函数
const extractFilenameFromUrl = (url) => {
  try {
    const urlObj = new URL(url)
    const pathname = urlObj.pathname
    const filename = pathname.split('/').pop()
    return filename || 'download'
  } catch {
    return 'download'
  }
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatSpeed = (bytesPerSecond) => {
  if (!bytesPerSecond) return '0 B/s'
  return formatSize(bytesPerSecond) + '/s'
}

const formatTime = (seconds) => {
  if (!seconds || seconds === Infinity) return ''
  
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  
  if (hours > 0) {
    return `${hours}h ${minutes}m`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

const getProgressText = (task) => {
  const isFtp = task.url && task.url.toLowerCase().startsWith('ftp://')
  
  switch (task.status) {
    case 'preparing': return 'Preparing...'
    case 'downloading': 
      if (isFtp) {
        return 'Downloading (FTP)'
      }
      return 'Downloading'
    case 'paused': return 'Paused'
    case 'completed': return 'Completed'
    case 'cancelled': return 'Cancelled'
    case 'error': return task.error || 'Download failed'
    default: return 'Unknown status'
  }
}

const loadExistingDownloads = async () => {
  try {
    const response = await fetch(`/api/filemanager/${props.projectId}/downloads`)
    if (!response.ok) return

    const data = await response.json()
    const tasks = (data.downloads || [])
      .map(task => ({
        id: task.task_id || task.id,
        url: task.url,
        filename: task.filename,
        status: task.status || 'preparing',
        progress: task.progress || 0,
        downloadedSize: task.downloaded_size || 0,
        totalSize: task.total_size || 0,
        speed: task.speed || 0,
        timeRemaining: task.time_remaining ?? null,
        error: task.error || null,
        path: task.path || props.currentPath,
        concurrent: task.concurrent !== false
      }))
      .filter(task => task.id)

    downloadTasks.value = tasks

    tasks.forEach(task => {
      if (task.status === 'downloading' || task.status === 'preparing') {
        pollDownloadProgress(task.id)
      }
    })
  } catch (error) {
    console.error('Failed to load downloads:', error)
  }
}

// Lifecycle
onMounted(() => {
  loadExistingDownloads()
})

onUnmounted(() => {
  pollTimers.forEach(timer => window.clearTimeout(timer))
  pollTimers.clear()
})
</script>

<style scoped>
.download-manager {
  position: fixed;
  bottom: 100px;
  right: 24px;
  width: 440px;
  max-height: min(600px, calc(100vh - 140px));
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  z-index: 1000;
  transition: max-height var(--transition-base);
}

.download-manager.minimized {
  max-height: 48px;
}

/* 头部 */
.download-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 46px;
  padding: 7px 10px 7px 12px;
  background: var(--surface-1);
  border-bottom: 1px solid var(--border-color-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.download-icon {
  color: var(--primary-600);
}

.header-title {
  font-weight: 600;
  color: var(--gray-900);
}

.download-count {
  background: var(--surface-2);
  color: var(--gray-600);
  padding: 2px 6px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 500;
}

.header-controls {
  display: flex;
  gap: 4px;
}

.control-btn {
  background: none;
  border: none;
  width: 30px;
  height: 30px;
  padding: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--gray-600);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.control-btn:hover {
  background: var(--surface-3);
  color: var(--gray-900);
}

.add-btn {
  background: var(--primary-600);
  color: white;
}

.add-btn:hover {
  background: var(--primary-700);
}

.download-header .close-btn:hover {
  background: var(--error-50);
  color: var(--error-600);
}

/* 内容区域 */
.download-content {
  max-height: 480px;
  overflow-y: auto;
}

.empty-downloads {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 36px 20px;
  gap: 8px;
}

.empty-icon {
  color: var(--gray-300);
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--gray-600);
}

.empty-subtext {
  font-size: 14px;
  color: var(--gray-500);
}

/* 下载列表 */
.download-list {
  padding: 8px;
}

.download-item {
  background: var(--surface-1);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-base);
  padding: 12px;
  margin-bottom: 8px;
  transition: border-color var(--transition-fast), background var(--transition-fast);
}

.download-item:hover {
  border-color: var(--border-color-dark);
}

.download-item.error {
  border-color: rgba(239, 68, 68, 0.35);
  background: var(--error-50);
}

.download-item.completed {
  border-color: rgba(34, 197, 94, 0.35);
  background: var(--success-50);
}

/* 文件信息 */
.download-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.file-icon {
  color: var(--gray-600);
  flex-shrink: 0;
}

.file-details {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 500;
  color: var(--gray-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 2px;
}

.file-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--gray-600);
}

/* 进度条 */
.download-progress {
  margin-bottom: 8px;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
  font-size: 12px;
}

.progress-text {
  color: var(--gray-600);
}

.progress-percent {
  color: var(--gray-900);
  font-weight: 500;
}

.progress-bar {
  height: 6px;
  background: var(--surface-3);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-fill.downloading {
  background: var(--primary-500);
}

.progress-fill.paused {
  background: var(--warning-500);
}

.progress-fill.completed {
  background: var(--success-500);
}

.progress-fill.error {
  background: var(--error-500);
}

/* 操作按钮 */
.download-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}

.action-btn {
  background: none;
  border: 1px solid var(--border-color);
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--gray-600);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background: var(--surface-2);
  border-color: var(--border-color-dark);
}

.pause-btn:hover, .resume-btn:hover {
  border-color: var(--primary-500);
  color: var(--primary-600);
}

.retry-btn:hover {
  border-color: var(--warning-500);
  color: var(--warning-600);
}

.open-btn:hover {
  border-color: var(--success-500);
  color: var(--success-600);
}

.remove-btn:hover {
  border-color: var(--error-500);
  color: var(--error-600);
}

/* 模态框 */
.download-modal {
  width: 90%;
  max-width: 480px;
  overflow: hidden;
}

.input-group {
  margin-bottom: 16px;
}

.input-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: var(--gray-700);
}

.url-input, .filename-input {
  width: 100%;
  height: var(--control-height);
  padding: 0 11px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 14px;
  transition: all 0.2s;
  box-sizing: border-box;
  background: var(--surface-1);
}

.url-input:focus, .filename-input:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.14);
}

.download-options {
  margin-top: 16px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--gray-700);
}

.checkbox-label input[type="checkbox"] {
  margin: 0;
}

.url-help, .options-help {
  margin-top: 6px;
}

.url-help small, .options-help small {
  color: var(--gray-600);
  font-size: 12px;
  line-height: 1.4;
}

.btn-primary {
  min-height: 36px;
  background: var(--primary-600);
  color: white;
  border: none;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-700);
}

.btn-primary:disabled {
  background: var(--gray-300);
  color: var(--gray-500);
  cursor: not-allowed;
}

.btn-cancel {
  background: var(--surface-1);
  color: var(--gray-700);
  border: 1px solid var(--border-color);
  min-height: 36px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: var(--surface-2);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .download-manager {
    bottom: 80px;
    right: 16px;
    width: calc(100vw - 32px);
    max-width: 400px;
  }
}

@media (max-width: 640px) {
  .download-manager {
    bottom: 76px;
    width: calc(100vw - 32px);
    right: 16px;
    left: 16px;
  }
}
</style> 
