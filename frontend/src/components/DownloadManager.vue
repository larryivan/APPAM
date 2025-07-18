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
    <div v-if="showAddUrlModal" class="modal-overlay" @click="showAddUrlModal = false">
      <div class="modal" @click.stop>
        <div class="modal-header">
          <h3>Add Download Link</h3>
          <button @click="showAddUrlModal = false" class="close-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
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
        <div class="modal-footer">
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
    } else if (task.status === 'downloading' || task.status === 'paused') {
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

// Lifecycle
onMounted(() => {
  // Can restore download tasks from local storage
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
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
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
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.download-icon {
  color: #3b82f6;
}

.header-title {
  font-weight: 600;
  color: #1e293b;
}

.download-count {
  background: #3b82f6;
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
  border-radius: 6px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.control-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.add-btn {
  background: #3b82f6;
  color: white;
}

.add-btn:hover {
  background: #2563eb;
}

.close-btn:hover {
  background: #fef2f2;
  color: #dc2626;
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
  color: #e2e8f0;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  color: #64748b;
}

.empty-subtext {
  font-size: 14px;
  color: #94a3b8;
}

/* 下载列表 */
.download-list {
  padding: 8px;
}

.download-item {
  background: #fefefe;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  transition: all 0.2s;
}

.download-item:hover {
  border-color: #cbd5e1;
  box-shadow: 0 2px 4px rgb(0 0 0 / 0.05);
}

.download-item.error {
  border-color: #fca5a5;
  background: #fef2f2;
}

.download-item.completed {
  border-color: #86efac;
  background: #f0fdf4;
}

/* 文件信息 */
.download-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.file-icon {
  color: #64748b;
  flex-shrink: 0;
}

.file-details {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 500;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 2px;
}

.file-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #64748b;
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
  color: #64748b;
}

.progress-percent {
  color: #1e293b;
  font-weight: 500;
}

.progress-bar {
  height: 6px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.progress-fill.downloading {
  background: #3b82f6;
}

.progress-fill.paused {
  background: #f59e0b;
}

.progress-fill.completed {
  background: #10b981;
}

.progress-fill.error {
  background: #ef4444;
}

/* 操作按钮 */
.download-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}

.action-btn {
  background: none;
  border: 1px solid #e2e8f0;
  padding: 6px;
  border-radius: 6px;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}

.pause-btn:hover, .resume-btn:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}

.retry-btn:hover {
  border-color: #f59e0b;
  color: #f59e0b;
}

.open-btn:hover {
  border-color: #10b981;
  color: #10b981;
}

.remove-btn:hover {
  border-color: #ef4444;
  color: #ef4444;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1);
  width: 90%;
  max-width: 480px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}

.close-btn {
  background: none;
  border: none;
  padding: 6px;
  cursor: pointer;
  color: #64748b;
  border-radius: 6px;
  transition: all 0.2s;
}

.modal-body {
  padding: 24px;
}

.input-group {
  margin-bottom: 20px;
}

.input-group label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  color: #374151;
}

.url-input, .filename-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
  box-sizing: border-box;
}

.url-input:focus, .filename-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
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
  color: #374151;
}

.checkbox-label input[type="checkbox"] {
  margin: 0;
}

.url-help, .options-help {
  margin-top: 6px;
}

.url-help small, .options-help small {
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-cancel {
  background: white;
  color: #475569;
  border: 1px solid #e2e8f0;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: #f8fafc;
}

/* 自定义滚动条 */
.download-content::-webkit-scrollbar {
  width: 6px;
}

.download-content::-webkit-scrollbar-track {
  background: #f8fafc;
}

.download-content::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.download-content::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
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