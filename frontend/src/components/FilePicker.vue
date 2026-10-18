<template>
  <Teleport to="body">
    <div v-if="isOpen" class="file-picker-container app-modal-viewport">
      <div class="file-picker-overlay app-modal-backdrop" @click="close"></div>
      <section
        ref="pickerPanel"
        class="file-picker-modal app-modal"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="pickerTitleId"
        tabindex="-1"
      >
        <header class="picker-header app-modal-header">
          <h3 :id="pickerTitleId">{{ selectDirectories ? 'Select directory' : (multiple ? 'Select files' : 'Select file') }}</h3>
          <button
            ref="closeButton"
            type="button"
            class="close-btn app-modal-close"
            title="Close"
            aria-label="Close file picker"
            @click="close"
          >
            <Icon name="x" :size="17" />
          </button>
        </header>

        <div class="picker-breadcrumbs" aria-label="Current folder">
          <div class="breadcrumb-path">
            <button
              type="button"
              class="breadcrumb-item"
              :class="{ active: currentPath === '/' }"
              :aria-current="currentPath === '/' ? 'location' : undefined"
              @click="navigateTo('/')"
            >
              <Icon name="folder" :size="15" />
              <span>Project Root</span>
            </button>
            <template v-for="(crumb, index) in breadcrumbs" :key="crumb.path">
              <Icon name="chevron-right" :size="14" class="separator" />
              <button
                type="button"
                class="breadcrumb-item"
                :class="{ active: index === breadcrumbs.length - 1 }"
                :aria-current="index === breadcrumbs.length - 1 ? 'location' : undefined"
                @click="navigateTo(crumb.path)"
              >
                {{ crumb.name }}
              </button>
            </template>
          </div>
          <div class="breadcrumb-actions">
            <button
              v-if="currentPath !== '/'"
              type="button"
              class="up-button"
              title="Parent folder"
              aria-label="Go to parent folder"
              @click="goUp"
            >
              <Icon name="folder-up" :size="16" />
            </button>
            <button
              v-if="selectDirectories"
              type="button"
              class="select-current-dir-button"
              :class="{ 'is-selected': isCurrentDirectorySelected }"
              :title="isCurrentDirectorySelected ? 'Deselect current folder' : 'Select current folder'"
              @click="selectCurrentDirectory"
            >
              <Icon :name="isCurrentDirectorySelected ? 'check' : 'folder'" :size="15" />
              <span>{{ isCurrentDirectorySelected ? 'Selected' : 'Select folder' }}</span>
            </button>
          </div>
        </div>

        <div class="picker-body" :aria-busy="loading">
          <div v-if="loading" class="loading">
            <Icon name="rotate-ccw" :size="21" spin />
            <span>Loading files</span>
          </div>

          <div v-else-if="loadError" class="picker-state error-state" role="alert">
            <Icon name="triangle-alert" :size="22" />
            <strong>Files could not be loaded</strong>
            <button type="button" @click="loadFiles">Try again</button>
          </div>

          <div v-else-if="filteredFiles.length === 0" class="empty">
            <Icon :name="files.length === 0 ? 'folder-open' : 'search'" :size="23" />
            <strong>{{ emptyStateTitle }}</strong>
            <span v-if="extensions.length > 0 && !selectDirectories" class="hint">
              Accepted: {{ extensions.join(', ') }}
            </span>
          </div>

          <div v-else class="file-list" role="listbox" :aria-multiselectable="multiple">
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
              role="option"
              :aria-selected="isSelected(file)"
              tabindex="0"
              @click="handleFileClick(file)"
              @dblclick="handleFileDblClick(file)"
              @keydown.enter.prevent="handleFileEnter(file)"
            >
              <div class="file-icon">
                <Icon :name="file.is_dir ? 'folder' : 'file'" :size="19" />
              </div>
              <div class="file-info">
                <div class="file-name">
                  <span>{{ file.name }}</span>
                  <Icon v-if="isSelected(file)" name="check" :size="13" class="select-hint" />
                </div>
                <div class="file-meta">
                  <span v-if="!file.is_dir">{{ formatSize(file.size) }}</span>
                  <span>{{ formatDate(file.mtime) }}</span>
                </div>
              </div>
              <button
                v-if="file.is_dir"
                type="button"
                class="open-folder-button"
                :title="`Open ${file.name}`"
                :aria-label="`Open folder ${file.name}`"
                @click.stop="openDirectory(file)"
              >
                <Icon name="chevron-right" :size="16" />
              </button>
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

        <footer class="picker-footer app-modal-footer">
          <div class="selected-info">
            <span v-if="selectedFiles.length > 0">
              {{ selectedFiles.length }} selected
            </span>
          </div>
          <div class="picker-actions">
            <button type="button" class="btn-cancel" @click="close">Cancel</button>
            <button 
              type="button"
              class="btn-confirm"
              :disabled="selectedFiles.length === 0"
              @click="confirmSelection"
            >
              Confirm
            </button>
          </div>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { nextOverlayId, useOverlay } from '@/lib/overlay.js';

import Icon from './ui/Icon.vue';

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
const loadError = ref('');
const currentPath = ref('/');
const files = ref([]);
const selectedFiles = ref([]);
const closeButton = ref(null);
let loadController = null;

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

const emptyStateTitle = computed(() => {
  if (files.value.length === 0) return 'This folder is empty';
  return props.selectDirectories ? 'No folders here' : 'No matching files';
});

const loadFiles = async () => {
  loadController?.abort();
  const controller = new AbortController();
  loadController = controller;
  loading.value = true;
  loadError.value = '';
  try {
    const response = await fetch(
      `/api/filemanager/${props.projectId}/list?path=${encodeURIComponent(currentPath.value)}`,
      { signal: controller.signal },
    );
    if (!response.ok) {
      throw new Error('Files could not be loaded');
    }
    const data = await response.json();
    if (!controller.signal.aborted) files.value = data.items || [];
  } catch (error) {
    if (error?.name === 'AbortError') return;
    console.error('Failed to load files:', error);
    files.value = [];
    loadError.value = 'Files could not be loaded';
  } finally {
    if (loadController === controller) {
      loadController = null;
      loading.value = false;
    }
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

const openDirectory = (file) => {
  if (!file?.is_dir) return;
  navigateTo(buildFilePath(file.name));
};

const handleFileDblClick = (file) => {
  if (file.is_dir) {
    openDirectory(file);
  } else if (!props.selectDirectories && isFileValid(file)) {
    // File selection mode: double-click file to select and confirm
    toggleSelection(file);
    if (!props.multiple) {
      confirmSelection();
    }
  }
};

const handleFileEnter = (file) => {
  if (file.is_dir) {
    openDirectory(file);
    return;
  }
  handleFileClick(file);
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
  if (!isOpen.value) return;
  loadController?.abort();
  isOpen.value = false;
  emit('close');
};

const pickerPanel = ref(null);
const pickerTitleId = nextOverlayId('file-picker-title');
useOverlay(() => isOpen.value, { onClose: close, panelRef: pickerPanel });

const confirmSelection = () => {
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
    confirmSelection(); // Confirm directly in single-select mode
  }
};

const isCurrentDirectorySelected = computed(() => {
  const currentDirPath = currentPath.value;
  return selectedFiles.value.some(f => f.path === currentDirPath);
});

onMounted(async () => {
  loadFiles();
});

onBeforeUnmount(() => {
  loadController?.abort();
});
</script>

<style scoped>
.file-picker-container {
  z-index: 1300;
  padding: 20px;
}

.file-picker-overlay {
  position: absolute;
  inset: 0;
}

.file-picker-modal {
  position: relative;
  z-index: 1;
  width: min(600px, 100%);
  max-height: calc(100vh - 40px);
  max-height: calc(100dvh - 40px);
  overflow: hidden;
}

.picker-header {
  flex: 0 0 auto;
  padding: 14px 18px;
  background: var(--surface-1);
}

.picker-breadcrumbs {
  display: flex;
  min-width: 0;
  min-height: 50px;
  flex: 0 0 auto;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color-light);
  background: var(--surface-2);
}

.breadcrumb-path {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
  scrollbar-width: thin;
}

.breadcrumb-item {
  display: inline-flex;
  min-height: 32px;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
  padding: 0 8px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-500);
  font: inherit;
  font-size: var(--text-xs);
  white-space: nowrap;
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.breadcrumb-item:hover {
  background: var(--surface-3);
  color: var(--gray-800);
}

.breadcrumb-item.active {
  color: var(--gray-900);
  font-weight: var(--font-semibold);
}

.separator {
  flex: 0 0 auto;
  color: var(--gray-300);
}

.breadcrumb-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 6px;
}

.up-button,
.open-folder-button {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.up-button:hover,
.open-folder-button:hover {
  background: var(--surface-3);
  color: var(--gray-800);
}

.select-current-dir-button {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--surface-1);
  color: var(--gray-700);
  font: inherit;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
}

.select-current-dir-button:hover {
  border-color: rgba(var(--accent-rgb), 0.35);
  color: var(--primary-700);
}

.select-current-dir-button.is-selected {
  border-color: rgba(var(--accent-rgb), 0.3);
  background: var(--primary-50);
  color: var(--primary-700);
}

.picker-body {
  min-height: 176px;
  max-height: min(430px, calc(100vh - 210px));
  max-height: min(430px, calc(100dvh - 210px));
  flex: 0 1 auto;
  overflow-y: auto;
  background: var(--surface-1);
}

.loading,
.empty,
.picker-state {
  display: flex;
  min-height: 176px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
  color: var(--gray-500);
  font-size: var(--text-sm);
  text-align: center;
}

.loading :deep(.app-icon) {
  color: var(--primary-600);
}

.empty > strong,
.picker-state > strong {
  color: var(--gray-700);
  font-size: var(--text-sm);
}

.hint {
  max-width: 420px;
  color: var(--gray-400);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.error-state {
  color: var(--error-600);
}

.error-state button {
  min-height: 32px;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--surface-1);
  color: var(--gray-700);
  font: inherit;
  font-size: var(--text-xs);
  cursor: pointer;
}

.file-list {
  display: grid;
  gap: 2px;
  padding: 8px 10px;
}

.file-item {
  display: flex;
  min-width: 0;
  min-height: 56px;
  align-items: center;
  gap: 10px;
  padding: 7px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  outline: none;
  color: var(--gray-700);
  cursor: default;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.file-item:hover,
.file-item:focus-visible {
  background: var(--surface-2);
}

.file-item:focus-visible {
  border-color: rgba(var(--accent-rgb), 0.35);
}

.file-item.is-selectable,
.file-item.is-navigable {
  cursor: pointer;
}

.file-item.is-selected {
  border-color: rgba(var(--accent-rgb), 0.25);
  background: var(--primary-50);
}

.file-icon {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: 0 0 32px;
  border-radius: 6px;
  background: var(--surface-2);
  color: var(--gray-500);
}

.file-item.is-directory .file-icon {
  background: var(--primary-50);
  color: var(--primary-600);
}

.file-info {
  min-width: 0;
  flex: 1;
}

.file-name {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 5px;
  color: var(--gray-800);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.file-name > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.select-hint {
  flex: 0 0 auto;
  color: var(--primary-600);
}

.file-meta {
  display: flex;
  gap: 10px;
  margin-top: 2px;
  color: var(--gray-400);
  font-size: var(--text-xs);
}

.open-folder-button {
  flex: 0 0 32px;
}

.file-checkbox {
  width: 17px;
  height: 17px;
  flex: 0 0 17px;
  accent-color: var(--primary-600);
  cursor: pointer;
}

.picker-footer {
  min-height: 58px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: var(--surface-1);
}

.selected-info {
  min-width: 0;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.picker-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.btn-cancel,
.btn-confirm {
  min-width: 78px;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 6px;
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
}

.btn-cancel {
  border: 1px solid var(--border-color);
  background: var(--surface-1);
  color: var(--gray-700);
}

.btn-cancel:hover {
  border-color: var(--border-color-dark);
  background: var(--surface-2);
}

.btn-confirm {
  border: 1px solid var(--primary-600);
  background: var(--primary-600);
  color: white;
}

.btn-confirm:hover:not(:disabled) {
  border-color: var(--primary-700);
  background: var(--primary-700);
}

.btn-confirm:disabled {
  border-color: var(--gray-200);
  background: var(--gray-200);
  color: var(--gray-400);
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .file-picker-container {
    padding: 8px;
  }

  .file-picker-modal {
    width: 100%;
    max-height: calc(100vh - 16px);
    max-height: calc(100dvh - 16px);
  }

  .picker-header {
    padding: 12px 14px;
  }

  .picker-breadcrumbs {
    align-items: stretch;
    flex-wrap: wrap;
    padding: 7px 10px;
  }

  .breadcrumb-path {
    flex-basis: calc(100% - 40px);
  }

  .breadcrumb-actions {
    margin-left: auto;
  }

  .select-current-dir-button span {
    display: none;
  }

  .select-current-dir-button {
    width: 34px;
    justify-content: center;
    padding: 0;
  }

  .picker-body {
    min-height: 150px;
    max-height: calc(100vh - 190px);
    max-height: calc(100dvh - 190px);
  }

  .loading,
  .empty,
  .picker-state {
    min-height: 150px;
  }

  .picker-footer {
    padding: 9px 12px;
  }

  .btn-cancel,
  .btn-confirm {
    min-width: 72px;
  }
}

@media (max-height: 620px) {
  .picker-body,
  .loading,
  .empty,
  .picker-state {
    min-height: 140px;
  }
}
</style>
