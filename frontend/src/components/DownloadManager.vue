<template>
  <div class="download-manager" :class="{ 'minimized': isMinimized }">
    <!-- 头部控制栏 -->
    <div class="download-header">
      <div class="header-left">
        <svg class="download-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        <span class="header-title">Download Manager</span>
        <span class="download-count" v-if="downloadTasks.length">{{ activeDownloads }}/{{ downloadTasks.length }}</span>
      </div>
      <div class="header-controls">
        <button @click="showAddUrlModal = true" class="control-btn add-btn" title="Add Download">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
        <button @click="pauseAll" class="control-btn" title="Pause All" v-if="activeDownloads > 0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="4" width="4" height="16"></rect>
            <rect x="14" y="4" width="4" height="16"></rect>
          </svg>
        </button>
        <button @click="resumeAll" class="control-btn" title="Resume All" v-if="pausedDownloads > 0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
        </button>
        <button @click="clearCompleted" class="control-btn" title="Clear Completed" v-if="completedDownloads > 0">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
        <button @click="toggleMinimize" class="control-btn" :title="isMinimized ? 'Expand' : 'Minimize'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline v-if="isMinimized" points="18 15 12 9 6 15"></polyline>
            <polyline v-else points="6 9 12 15 18 9"></polyline>
          </svg>
        </button>
        <button @click="$emit('close')" class="control-btn close-btn" title="Close">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>

    <!-- 下载列表 -->
    <div class="download-content" v-if="!isMinimized">
      <div v-if="downloadTasks.length === 0" class="empty-downloads">
        <svg class="empty-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
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
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                <polyline points="13 2 13 9 20 9"></polyline>
              </svg>
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
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="6" y="4" width="4" height="16"></rect>
                <rect x="14" y="4" width="4" height="16"></rect>
              </svg>
            </button>

            <!-- 暂停中 -->
            <button 
              v-if="task.status === 'paused'" 
              @click="resumeDownload(task.id)"
              class="action-btn resume-btn"
              title="Resume"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
            </button>

            <!-- 错误状态 -->
            <button 
              v-if="task.status === 'error'" 
              @click="retryDownload(task.id)"
              class="action-btn retry-btn"
              title="Retry"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="23 4 23 10 17 10"></polyline>
                <polyline points="1 20 1 14 7 14"></polyline>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
            </button>

            <!-- 完成状态 -->
            <button 
              v-if="task.status === 'completed'" 
              @click="openFile(task)"
              class="action-btn open-btn"
              title="Open File"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                <polyline points="15 3 21 3 21 9"></polyline>
                <line x1="10" y1="14" x2="21" y2="3"></line>
              </svg>
            </button>

            <!-- 删除按钮 -->
            <button 
              @click="removeDownload(task.id)" 
              class="action-btn remove-btn"
              title="Delete"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加URL模态框 -->
    <div v-if="showAddUrlModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="showAddUrlModal = false">
      <div class="app-modal download-modal" @click.stop>
        <div class="modal-header app-modal-header">
          <h3>Add Download Link</h3>
          <button @click="showAddUrlModal = false" class="close-btn app-modal-close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body app-modal-body">
          <div class="input-group">
            <label>Download Link</label>
            <input 
              v-model="newDownloadUrl" 
              placeholder="Enter download link (HTTP/HTTPS/FTP supported)" 
              class="url-input"
              @keyup.enter="addDownload"
            />
            <div class="url-help">
              <small>
                Supported protocols: HTTP, HTTPS, FTP<br/>
                Examples: https://example.com/file.zip or ftp://ftp.example.com/path/file.gz
              </small>
            </div>
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
              Enable multi-threaded download (for HTTP/HTTPS large files)
            </label>
            <div class="options-help">
              <small>Note: FTP protocol currently only supports single-threaded downloads, but supports resume functionality</small>
            </div>
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
const newDownloadUrl = ref('')
const newDownloadFilename = ref('')
const enableConcurrentDownload = ref(true)

// 下载状态统计
const activeDownloads = computed(() => 
  downloadTasks.value.filter(task => task.status === 'downloading').length
)
const pausedDownloads = computed(() => 
  downloadTasks.value.filter(task => task.status === 'paused').length
)
const completedDownloads = computed(() => 
  downloadTasks.value.filter(task => task.status === 'completed').length
)

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
        path: props.currentPath,
        concurrent: task.concurrent,
        task_id: taskId
      })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    // 开始轮询下载进度
    pollDownloadProgress(taskId)
    
  } catch (error) {
    console.error('Download error:', error)
    task.status = 'error'
    task.error = error.message
  }
}

const pollDownloadProgress = async (taskId) => {
  const task = downloadTasks.value.find(t => t.id === taskId)
  if (!task || task.status === 'completed' || task.status === 'error') return
  
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
    } else if (task.status === 'downloading' || task.status === 'paused' || task.status === 'preparing') {
      setTimeout(() => pollDownloadProgress(taskId), 1000)
    }
    
  } catch (error) {
    console.error('Progress polling error:', error)
    setTimeout(() => pollDownloadProgress(taskId), 2000)
  }
}

const pauseDownload = async (taskId) => {
  try {
    await fetch(`/api/filemanager/${props.projectId}/download-pause/${taskId}`, {
      method: 'POST'
    })
    const task = downloadTasks.value.find(t => t.id === taskId)
    if (task) task.status = 'paused'
  } catch (error) {
    console.error('Pause error:', error)
  }
}

const resumeDownload = async (taskId) => {
  try {
    await fetch(`/api/filemanager/${props.projectId}/download-resume/${taskId}`, {
      method: 'POST'
    })
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

const clearCompleted = () => {
  downloadTasks.value = downloadTasks.value.filter(task => task.status !== 'completed')
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
        error: task.error || null
      }))
      .filter(task => task.id)

    downloadTasks.value = tasks

    tasks.forEach(task => {
      if (task.status !== 'completed' && task.status !== 'error') {
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
  // Clean up timers
})
</script>

<style scoped>
.download-manager {
  position: fixed;
  bottom: 100px;
  right: 24px;
  width: 480px;
  max-height: 600px;
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  z-index: 1000;
  transition: all 0.3s ease;
}

.download-manager.minimized {
  max-height: 60px;
}

/* 头部 */
.download-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--surface-2);
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
  background: var(--gradient-primary);
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
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
  padding: 6px;
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
  background: var(--gradient-primary);
  color: white;
}

.add-btn:hover {
  background: linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%);
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
  padding: 40px 20px;
  gap: 12px;
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
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 8px;
  transition: all 0.2s;
  box-shadow: var(--shadow-xs);
}

.download-item:hover {
  border-color: var(--border-color-dark);
  box-shadow: var(--shadow-sm);
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
  padding: 6px;
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
  margin-bottom: 20px;
}

.input-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: var(--gray-700);
}

.url-input, .filename-input {
  width: 100%;
  padding: 12px 16px;
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
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
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
  background: var(--gradient-primary);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  background: var(--surface-1);
  color: var(--gray-700);
  border: 1px solid var(--border-color);
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: var(--surface-2);
}

/* 自定义滚动条 */
.download-content::-webkit-scrollbar {
  width: 6px;
}

.download-content::-webkit-scrollbar-track {
  background: var(--surface-2);
}

.download-content::-webkit-scrollbar-thumb {
  background: var(--gray-300);
  border-radius: 3px;
}

.download-content::-webkit-scrollbar-thumb:hover {
  background: var(--gray-400);
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
