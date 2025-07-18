<!-- DragDropUpload.vue - Enhanced drag and drop upload component -->
<template>
  <div 
    class="drag-drop-upload"
    :class="{ 
      'drag-over': isDragOver,
      'uploading': isUploading 
    }"
    @drop="handleDrop"
    @dragover="handleDragOver"
    @dragenter="handleDragEnter"
    @dragleave="handleDragLeave"
  >
    <div v-if="!isUploading" class="upload-content">
      <div class="upload-icon">📁</div>
      <div class="upload-text">
        <p class="primary-text">Drop files here to upload</p>
        <p class="secondary-text">or <button @click="$refs.fileInput.click()" class="browse-btn">browse files</button></p>
      </div>
      <input 
        ref="fileInput" 
        type="file" 
        multiple 
        @change="handleFileSelect"
        style="display: none"
      />
    </div>
    
    <div v-else class="upload-progress">
      <div class="overall-progress">
        <h4>Uploading {{ uploadQueue.length }} file(s)...</h4>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: overallProgress + '%' }"></div>
        </div>
        <span class="progress-text">{{ overallProgress.toFixed(1) }}%</span>
      </div>
      
      <div class="file-list">
        <div 
          v-for="file in uploadQueue" 
          :key="file.id" 
          class="upload-item"
          :class="{ 
            'completed': file.status === 'completed',
            'error': file.status === 'error' 
          }"
        >
          <div class="file-info">
            <span class="file-icon">{{ getFileIcon(file.name) }}</span>
            <span class="file-name">{{ file.name }}</span>
            <span class="file-size">{{ formatSize(file.size) }}</span>
          </div>
          <div class="file-progress">
            <div class="progress-bar small">
              <div class="progress-fill" :style="{ width: file.progress + '%' }"></div>
            </div>
            <span class="status-icon">
              <span v-if="file.status === 'completed'">✅</span>
              <span v-else-if="file.status === 'error'">❌</span>
              <span v-else class="spinner-small"></span>
            </span>
          </div>
        </div>
      </div>
      
      <div class="upload-actions">
        <button @click="cancelUpload" class="cancel-btn">Cancel</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

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

const emit = defineEmits(['upload-complete', 'upload-error'])

const isDragOver = ref(false)
const isUploading = ref(false)
const uploadQueue = ref([])
const dragCounter = ref(0)

const CHUNK_SIZE = 1024 * 1024 * 5 // 5MB chunks

const overallProgress = computed(() => {
  if (uploadQueue.value.length === 0) return 0
  const totalProgress = uploadQueue.value.reduce((sum, file) => sum + file.progress, 0)
  return totalProgress / uploadQueue.value.length
})

const handleDragEnter = (e) => {
  e.preventDefault()
  dragCounter.value++
  isDragOver.value = true
}

const handleDragLeave = (e) => {
  e.preventDefault()
  dragCounter.value--
  if (dragCounter.value === 0) {
    isDragOver.value = false
  }
}

const handleDragOver = (e) => {
  e.preventDefault()
}

const handleDrop = (e) => {
  e.preventDefault()
  isDragOver.value = false
  dragCounter.value = 0
  
  const files = Array.from(e.dataTransfer.files)
  if (files.length > 0) {
    startUpload(files)
  }
}

const handleFileSelect = (e) => {
  const files = Array.from(e.target.files)
  if (files.length > 0) {
    startUpload(files)
  }
}

const startUpload = (files) => {
  isUploading.value = true
  uploadQueue.value = files.map((file, index) => ({
    id: Date.now() + index,
    file,
    name: file.name,
    size: file.size,
    progress: 0,
    status: 'pending'
  }))
  
  uploadFiles()
}

const uploadFiles = async () => {
  for (const fileItem of uploadQueue.value) {
    if (fileItem.status === 'cancelled') break
    
    try {
      fileItem.status = 'uploading'
      await uploadFileInChunks(fileItem)
      fileItem.status = 'completed'
      fileItem.progress = 100
    } catch (error) {
      fileItem.status = 'error'
      console.error(`Failed to upload ${fileItem.name}:`, error)
      emit('upload-error', { file: fileItem, error })
    }
  }
  
  // Cleanup
  setTimeout(() => {
    isUploading.value = false
    uploadQueue.value = []
    emit('upload-complete')
  }, 2000)
}

const uploadFileInChunks = async (fileItem) => {
  const file = fileItem.file
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
  
  for (let chunkNumber = 0; chunkNumber < totalChunks; chunkNumber++) {
    if (fileItem.status === 'cancelled') return
    
    const start = chunkNumber * CHUNK_SIZE
    const end = Math.min(start + CHUNK_SIZE, file.size)
    const chunk = file.slice(start, end)

    const formData = new FormData()
    formData.append('file', chunk)
    formData.append('chunkNumber', chunkNumber + 1)
    formData.append('totalChunks', totalChunks)
    formData.append('filename', file.name)
    formData.append('path', props.currentPath === '/' ? '' : props.currentPath)

    const response = await fetch(`/api/filemanager/${props.projectId}/upload-chunk`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Upload failed')
    }

    fileItem.progress = ((chunkNumber + 1) / totalChunks) * 100
  }
}

const cancelUpload = () => {
  uploadQueue.value.forEach(file => {
    if (file.status === 'uploading' || file.status === 'pending') {
      file.status = 'cancelled'
    }
  })
  
  setTimeout(() => {
    isUploading.value = false
    uploadQueue.value = []
  }, 1000)
}

const getFileIcon = (fileName) => {
  const ext = fileName.split('.').pop()?.toLowerCase() || ''
  const iconMap = {
    // Images
    png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🖼️', svg: '🖼️', webp: '🖼️',
    // Documents
    pdf: '📄', doc: '📄', docx: '📄', txt: '📄', md: '📄',
    // Spreadsheets
    xls: '📊', xlsx: '📊', csv: '📊',
    // Archives
    zip: '📦', tar: '📦', gz: '📦', rar: '📦', 
    // Code
    js: '📜', ts: '📜', py: '🐍', java: '☕', html: '🌐', css: '🎨',
    // Media
    mp4: '🎥', avi: '🎥', mov: '🎥', mp3: '🎵', wav: '🎵',
    // Bioinformatics
    fasta: '🧬', fastq: '🧬', vcf: '🧬', gff: '🧬', bed: '🧬'
  }
  return iconMap[ext] || '📄'
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
</script>

<style scoped>
.drag-drop-upload {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 40px 20px;
  text-align: center;
  background: #f9fafb;
  transition: all 0.3s ease;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drag-drop-upload.drag-over {
  border-color: #3b82f6;
  background: #eff6ff;
  transform: scale(1.02);
}

.drag-drop-upload.uploading {
  background: white;
  border-color: #10b981;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.upload-icon {
  font-size: 48px;
  opacity: 0.7;
}

.upload-text {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.primary-text {
  font-size: 18px;
  font-weight: 600;
  color: #374151;
  margin: 0;
}

.secondary-text {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}

.browse-btn {
  background: none;
  border: none;
  color: #3b82f6;
  cursor: pointer;
  text-decoration: underline;
  font-size: 14px;
  padding: 0;
}

.browse-btn:hover {
  color: #2563eb;
}

.upload-progress {
  width: 100%;
  max-width: 600px;
}

.overall-progress {
  margin-bottom: 24px;
}

.overall-progress h4 {
  margin: 0 0 12px 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.progress-bar {
  width: 100%;
  height: 12px;
  background: #f3f4f6;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar.small {
  height: 6px;
  border-radius: 3px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  transition: width 0.3s ease;
  border-radius: inherit;
}

.progress-text {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.file-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 20px;
}

.upload-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}

.upload-item.completed {
  border-color: #10b981;
  background: #f0fdf4;
}

.upload-item.error {
  border-color: #ef4444;
  background: #fef2f2;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.file-icon {
  font-size: 20px;
}

.file-name {
  font-weight: 500;
  color: #111827;
  flex: 1;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: 12px;
  color: #6b7280;
  min-width: 60px;
}

.file-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 120px;
}

.file-progress .progress-bar {
  width: 80px;
  margin: 0;
}

.status-icon {
  min-width: 20px;
  text-align: center;
}

.spinner-small {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid #f3f4f6;
  border-top: 2px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.upload-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.cancel-btn {
  padding: 8px 20px;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.cancel-btn:hover {
  background: #e5e7eb;
  border-color: #9ca3af;
}

/* Responsive design */
@media (max-width: 768px) {
  .drag-drop-upload {
    padding: 20px 16px;
    min-height: 150px;
  }
  
  .upload-icon {
    font-size: 36px;
  }
  
  .primary-text {
    font-size: 16px;
  }
  
  .file-info {
    gap: 8px;
  }
  
  .file-progress {
    min-width: 100px;
  }
  
  .file-progress .progress-bar {
    width: 60px;
  }
}
</style>