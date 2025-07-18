<template>
  <div class="file-picker-container" v-if="isOpen">
    <div class="file-picker-overlay" @click="close"></div>
    <div class="file-picker-modal">
      <header class="picker-header">
        <h3>{{ selectDirectories ? 'Select Directory' : (multiple ? 'Select Files' : 'Select File') }}</h3>
        <button @click="close" class="close-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </header>

      <div class="picker-breadcrumbs">
        <button @click="navigateTo('/')" class="breadcrumb-item">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
          </svg>
          Project Root
        </button>
        <template v-for="(crumb, index) in breadcrumbs" :key="index">
          <span class="separator">/</span>
          <button @click="navigateTo(crumb.path)" class="breadcrumb-item">{{ crumb.name }}</button>
        </template>
        <button 
          v-if="currentPath !== '/'" 
          @click="goUp" 
          class="up-button" 
          title="Go to parent directory"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="17 11 12 6 7 11"></polyline>
            <polyline points="17 18 12 13 7 18"></polyline>
          </svg>
          Parent
        </button>
        <button 
          v-if="selectDirectories" 
          @click="selectCurrentDirectory" 
          class="select-current-dir-button" 
          :class="{ 'is-selected': isCurrentDirectorySelected }"
          :title="isCurrentDirectorySelected ? 'Deselect current directory' : 'Select current directory'"
        >
          <svg v-if="!isCurrentDirectorySelected" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          {{ isCurrentDirectorySelected ? 'Directory Selected' : 'Select This Directory' }}
        </button>
      </div>

      <div class="picker-body">
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
          <span>Loading...</span>
        </div>

        <div v-else-if="filteredFiles.length === 0" class="empty">
          <p v-if="files.length === 0">This directory is empty</p>
          <div v-else>
            <p v-if="selectDirectories">No subdirectories in this directory</p>
            <p v-else>No files matching the criteria in this directory</p>
            <p class="hint" v-if="extensions.length > 0 && !selectDirectories">Supported file types: {{ extensions.join(', ') }}</p>
            <p class="hint">Current directory: {{ currentPath }}</p>
            <div class="interaction-hints">
              <p class="hint">💡 Double-click directories to navigate deeper</p>
              <p class="hint" v-if="selectDirectories">📁 Click directories to select, or use "Select This Directory" button above</p>
              <p class="hint" v-else>📄 Click files to select</p>
            </div>
            <details class="debug-info">
              <summary>Debug Info ({{ files.length }} items)</summary>
              <ul>
                <li v-for="file in files.slice(0, 10)" :key="file.name">
                  {{ file.name }} - {{ file.is_dir ? 'Directory' : 'File' }} {{ file.extension }}
                </li>
                <li v-if="files.length > 10">... {{ files.length - 10 }} more items</li>
              </ul>
            </details>
          </div>
        </div>

        <div v-else class="file-list">
          <div 
            v-for="file in filteredFiles" 
            :key="file.name"
            class="file-item"
            :class="{ 
              'is-directory': file.is_dir,
              'is-selected': isSelected(file),
              'is-selectable': isFileValid(file),
              'is-navigable': file.is_dir
            }"
            @click="handleFileClick(file)"
            @dblclick="handleFileDblClick(file)"
          >
            <div class="file-icon">
              <svg v-if="file.is_dir" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                <polyline points="13 2 13 9 20 9"></polyline>
              </svg>
            </div>
            <div class="file-info">
              <div class="file-name">
                {{ file.name }}
                <span v-if="file.is_dir" class="nav-hint">🔽</span>
                <span v-if="isFileValid(file)" class="select-hint">✓</span>
              </div>
              <div class="file-meta">
                <span v-if="!file.is_dir">{{ formatSize(file.size) }}</span>
                <span>{{ formatDate(file.mtime) }}</span>
                <span v-if="file.is_dir" class="action-hint">Double-click to enter</span>
                <span v-if="isFileValid(file)" class="action-hint">Click to select</span>
              </div>
            </div>
            <input 
              v-if="multiple && isFileValid(file)"
              type="checkbox"
              :checked="isSelected(file)"
              @click.stop="toggleSelection(file)"
              class="file-checkbox"
            />
          </div>
        </div>
      </div>

      <footer class="picker-footer">
        <div class="selected-info">
          <span v-if="selectedFiles.length > 0">
            Selected {{ selectedFiles.length }} files
          </span>
        </div>
        <div class="picker-actions">
          <button @click="close" class="btn-cancel">Cancel</button>
          <button 
            @click="confirm" 
            class="btn-confirm"
            :disabled="selectedFiles.length === 0"
          >
            Confirm
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  projectId: {
    type: String,
    required: true
  },
  extensions: {
    type: Array,
    default: () => []
  },
  multiple: {
    type: Boolean,
    default: false
  },
  selectDirectories: {
    type: Boolean,
    default: false
  },
  modelValue: {
    type: [String, Array],
    default: null
  }
});

const emit = defineEmits(['update:modelValue', 'close']);

const isOpen = ref(true);
const loading = ref(false);
const currentPath = ref('/');
const files = ref([]);
const selectedFiles = ref([]);

// Initialize with modelValue
watch(() => props.modelValue, (newVal) => {
  if (newVal === null || newVal === undefined) {
    selectedFiles.value = [];
  } else if (props.multiple && Array.isArray(newVal)) {
    selectedFiles.value = newVal.map(path => ({ path }));
  } else if (!props.multiple && typeof newVal === 'string' && newVal) {
    selectedFiles.value = [{ path: newVal }];
  } else {
    selectedFiles.value = [];
  }
}, { immediate: true });

const breadcrumbs = computed(() => {
  const parts = currentPath.value.split('/').filter(p => p);
  return parts.map((part, index) => ({
    name: part,
    path: '/' + parts.slice(0, index + 1).join('/')
  }));
});

const filteredFiles = computed(() => {
  // If no files loaded, return empty array
  if (!files.value || files.value.length === 0) {
    return [];
  }
  
  return files.value.filter(file => {
    // If in directory selection mode
    if (props.selectDirectories) {
      // Only show directories
      return file.is_dir;
    }
    
    // File selection mode
    // Always show directories (for navigation)
    if (file.is_dir) return true;
    
    // If no extension restrictions, show all files
    if (!props.extensions || props.extensions.length === 0) return true;
    
    // Get file extension (file.extension already includes the dot)
    const fileExt = file.extension || '';
    const fileName = file.name || '';
    
    // Check if file extension matches
    return props.extensions.some(ext => {
      // Handle compound extensions like .fastq.gz
      if (fileName.toLowerCase().endsWith(ext.toLowerCase())) {
        return true;
      }
      // Simple extension match
      return fileExt.toLowerCase() === ext.toLowerCase();
    });
  });
});

const loadFiles = async () => {
  loading.value = true;
  try {
    const response = await fetch(`/api/filemanager/${props.projectId}/list?path=${encodeURIComponent(currentPath.value)}`);
    if (!response.ok) {
      console.error('Failed to load files:', response.statusText);
      files.value = [];
      return;
    }
    const data = await response.json();
    files.value = data.items || [];
    
    // Debug information
    console.log('Loaded files:', files.value.length, 'Current path:', currentPath.value);
    console.log('Extensions filter:', props.extensions);
    console.log('Files:', files.value.map(f => ({ name: f.name, ext: f.extension, is_dir: f.is_dir })));
  } catch (error) {
    console.error('Failed to load files:', error);
    files.value = [];
  } finally {
    loading.value = false;
  }
};

const navigateTo = (path) => {
  // Ensure path format is correct
  if (path === '' || path === '/') {
    currentPath.value = '/';
  } else {
    currentPath.value = path.startsWith('/') ? path : '/' + path;
  }
  loadFiles();
};

const goUp = () => {
  const currentParts = currentPath.value.split('/').filter(p => p);
  if (currentParts.length > 0) {
    if (currentParts.length === 1) {
      // If currently in first-level subdirectory, return to root
      navigateTo('/');
    } else {
      // Otherwise return to parent directory
      const parentPath = '/' + currentParts.slice(0, -1).join('/');
      navigateTo(parentPath);
    }
  }
};

const isFileValid = (file) => {
  if (props.selectDirectories) {
    // Directory selection mode: only directories are valid
    return file.is_dir;
  } else {
    // File selection mode: only files are valid, directories are for navigation
    if (file.is_dir) return false;
    if (props.extensions.length === 0) return true;
    
    const fileExt = file.extension || '';
    return props.extensions.some(ext => 
      fileExt.toLowerCase() === ext.toLowerCase() ||
      file.name.toLowerCase().endsWith(ext.toLowerCase())
    );
  }
};

const isSelected = (file) => {
  const filePath = buildFilePath(file.name);
  return selectedFiles.value.some(f => f.path === filePath);
};

const toggleSelection = (file) => {
  const filePath = buildFilePath(file.name);
  const index = selectedFiles.value.findIndex(f => f.path === filePath);
  
  if (index >= 0) {
    selectedFiles.value.splice(index, 1);
  } else {
    if (props.multiple) {
      selectedFiles.value.push({ path: filePath, name: file.name });
    } else {
      selectedFiles.value = [{ path: filePath, name: file.name }];
    }
  }
};

const buildFilePath = (fileName) => {
  if (currentPath.value === '/') {
    return '/' + fileName;
  } else {
    return currentPath.value + '/' + fileName;
  }
};

const handleFileClick = (file) => {
  if (!isFileValid(file)) return;
  
  // Directory selection mode or file selection mode, both can be selected with click
  if (props.multiple) {
    toggleSelection(file);
  } else {
    // Single selection mode, click to select
    toggleSelection(file);
  }
};

const handleFileDblClick = (file) => {
  if (file.is_dir) {
    // In any mode, double-click directories to navigate
    const newPath = buildFilePath(file.name);
    navigateTo(newPath);
  } else if (!props.selectDirectories && isFileValid(file)) {
    // File selection mode: double-click file to select and confirm
    toggleSelection(file);
    if (!props.multiple) {
      confirm();
    }
  }
};

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (timestamp) => {
  return new Date(timestamp * 1000).toLocaleDateString('en-US');
};

const close = () => {
  isOpen.value = false;
  emit('close');
};

const confirm = () => {
  const paths = selectedFiles.value.map(f => f.path);
  emit('update:modelValue', props.multiple ? paths : paths[0] || '');
  close();
};

const selectCurrentDirectory = () => {
  const currentDirPath = currentPath.value; // Current directory path
  const currentDirName = currentPath.value === '/' ? 'Project Root' : currentPath.value.split('/').pop();
  
  if (props.multiple) {
    const existingIndex = selectedFiles.value.findIndex(f => f.path === currentDirPath);
    if (existingIndex >= 0) {
      selectedFiles.value.splice(existingIndex, 1);
    } else {
      selectedFiles.value.push({ path: currentDirPath, name: currentDirName });
    }
  } else {
    selectedFiles.value = [{ path: currentDirPath, name: currentDirName }];
    confirm(); // Confirm directly in single-select mode
  }
};

const isCurrentDirectorySelected = computed(() => {
  const currentDirPath = currentPath.value;
  return selectedFiles.value.some(f => f.path === currentDirPath);
});

// Load initial files
loadFiles();
</script>

<style scoped>
.file-picker-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.file-picker-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
}

.file-picker-modal {
  position: relative;
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.picker-header {
  padding: 16px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.picker-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  padding: 8px;
  cursor: pointer;
  color: #64748b;
  transition: color 0.15s ease;
}

.close-btn:hover {
  color: #1e293b;
}

.picker-breadcrumbs {
  padding: 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  min-height: 60px;
}

.breadcrumb-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: white;
  border: 1px solid #e2e8f0;
  padding: 8px 12px;
  cursor: pointer;
  color: #475569;
  font-size: 14px;
  white-space: nowrap;
  transition: all 0.2s ease;
  border-radius: 8px;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.breadcrumb-item:hover {
  background: #f8fafc;
  border-color: #3b82f6;
  color: #3b82f6;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.breadcrumb-item:first-child {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  border-color: #3b82f6;
}

.breadcrumb-item:first-child:hover {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: white;
  border-color: #2563eb;
}

.separator {
  color: #cbd5e1;
  font-weight: 600;
  font-size: 16px;
  margin: 0 4px;
}

.up-button {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  border: 1px solid #f59e0b;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
  border-radius: 8px;
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.up-button:hover {
  background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
  border-color: #d97706;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.up-button svg {
  width: 16px;
  height: 16px;
}

.select-current-dir-button {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: 1px solid #10b981;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s ease;
  border-radius: 8px;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-left: auto;
}

.select-current-dir-button:hover {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  border-color: #059669;
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.select-current-dir-button.is-selected {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  border-color: #8b5cf6;
  color: white;
}

.select-current-dir-button.is-selected:hover {
  background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%);
  border-color: #7c3aed;
}

.select-current-dir-button svg {
  width: 16px;
  height: 16px;
}

.picker-body {
  flex: 1;
  overflow-y: auto;
  min-height: 300px;
}

.loading, .empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #64748b;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.hint {
  font-size: 14px;
  color: #94a3b8;
  margin-top: 8px;
}

.interaction-hints {
  margin-top: 8px;
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
}

.debug-info {
  margin-top: 16px;
  padding: 12px;
  background: #f1f5f9;
  border-radius: 6px;
  font-size: 12px;
  color: #475569;
}

.debug-info summary {
  cursor: pointer;
  font-weight: 500;
}

.debug-info ul {
  margin: 8px 0 0 0;
  padding-left: 16px;
}

.file-list {
  padding: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  gap: 12px;
}

.file-item:hover {
  background: #f8fafc;
}

.file-item.is-selected {
  background: #dbeafe;
  border: 1px solid #93c5fd;
}

.file-item.is-directory {
  color: #475569;
}

.file-item.is-selectable {
  cursor: pointer;
}

.file-item.is-selectable:hover {
  background: #f1f5f9;
}

.file-item.is-directory.is-selectable .file-icon svg {
  stroke: #3b82f6;
  fill: #dbeafe;
}

.file-item:not(.is-selectable) {
  opacity: 0.7;
  cursor: default;
}

.file-item.is-navigable {
  cursor: pointer;
}

.file-item.is-navigable:hover {
  background: #dbeafe;
  border-left: 3px solid #3b82f6;
}

.file-item.is-navigable .file-icon svg {
  stroke: #3b82f6;
  fill: #dbeafe;
}

.file-icon svg {
  width: 24px;
  height: 24px;
  stroke: #64748b;
}

.file-item.is-directory .file-icon svg {
  stroke: #3b82f6;
  fill: #dbeafe;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-hint {
  margin-left: 4px;
  font-size: 12px;
  color: #94a3b8;
}

.select-hint {
  margin-left: 4px;
  font-size: 12px;
  color: #3b82f6;
}

.action-hint {
  margin-left: 4px;
  font-size: 12px;
  color: #94a3b8;
}

.file-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.file-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.picker-footer {
  padding: 16px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.selected-info {
  font-size: 14px;
  color: #64748b;
}

.picker-actions {
  display: flex;
  gap: 12px;
}

.btn-cancel {
  background: #f8fafc;
  color: #475569;
  border: 1px solid #e2e8f0;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s ease;
}

.btn-cancel:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.btn-confirm {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s ease;
}

.btn-confirm:hover:not(:disabled) {
  background: #2563eb;
}

.btn-confirm:disabled {
  background: #cbd5e1;
  color: #94a3b8;
  cursor: not-allowed;
}
</style> 