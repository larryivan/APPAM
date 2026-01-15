<template>
  <div class="tool-interface-container" v-if="tool">
    <header class="tool-header">
      <div class="tool-header-content">
        <div class="tool-info">
          <div class="tool-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 19l7-7 3 3-7 7-3-3z"></path>
              <path d="m18 13-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"></path>
              <path d="m2 2 7.586 7.586"></path>
              <circle cx="11" cy="11" r="2"></circle>
            </svg>
          </div>
          <div class="tool-title">
            <h2>{{ tool.tool_name }}</h2>
            <p :title="tool.description">{{ tool.description }}</p>
          </div>
        </div>
        <div class="tool-status">
          <div class="status-indicator" :class="taskStatus">
            <span class="status-dot"></span>
            <span class="status-text">{{ getStatusText() }}</span>
          </div>
          <button @click="refreshStatus" class="refresh-status-btn" :class="{ refreshing: isRefreshingStatus }" title="refresh status" :disabled="isRefreshingStatus">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
          </button>
        </div>
      </div>
    </header>

    <div class="tool-body">
      <!-- 参数配置区域 -->
      <div class="form-section">
        <div class="form-card">
          <div class="form-header">
            <h4>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z"></path>
                <path d="M12 8v4"></path>
                <path d="M12 16h.01"></path>
              </svg>
              Parameters
            </h4>
            <div class="form-header-actions">
              <div class="param-count">{{ tool.parameters.length }}</div>
              <button 
                @click="openParameterSuggestions"
                class="smart-fill-btn"
                :class="{ loading: isParameterFilling }"
                :disabled="isParameterFilling"
                title="Generate AI parameter suggestions"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  <path d="M12 7v6"></path>
                  <path d="M9 10l3-3 3 3"></path>
                </svg>
                {{ isParameterFilling ? 'Thinking...' : 'Config by AI' }}
              </button>

            </div>
          </div>

          
          <div v-if="tool.parameters.length > 0" class="param-list">
            <div v-for="param in tool.parameters" :key="param.name" class="param-row">
              <div class="param-header">
                <label :for="param.name" class="param-label">
                  {{ param.name }}
                  <span v-if="param.required" class="required-indicator">*</span>
                </label>
                <span class="param-type">{{ getParamTypeDisplay(param) }}</span>
              </div>
              <p class="param-description">{{ param.description }}</p>
              
              <!-- File input type -->
              <div v-if="param.type === 'file'" class="file-input-container">
                <div v-if="param.multiple && Array.isArray(formValues[param.name])" class="file-list">
                  <div v-for="(file, index) in formValues[param.name]" :key="index" class="selected-file">
                    <div class="file-info">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                        <polyline points="13 2 13 9 20 9"></polyline>
                      </svg>
                      <span class="file-path">{{ file }}</span>
                    </div>
                    <button @click="removeFile(param.name, index)" class="remove-file">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  </div>
                </div>
                <div v-else-if="!param.multiple && formValues[param.name]" class="selected-file">
                  <div class="file-info">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                      <polyline points="13 2 13 9 20 9"></polyline>
                    </svg>
                    <span class="file-path">{{ formValues[param.name] }}</span>
                  </div>
                  <button @click="formValues[param.name] = ''" class="remove-file">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </div>
                <button @click="openFilePicker(param)" class="file-select-btn">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                    <polyline points="13 2 13 9 20 9"></polyline>
                  </svg>
                  {{ param.multiple ? 'Choose Files' : 'Choose File' }}
                </button>
              </div>
              
              <!-- Directory input type -->
              <div v-else-if="param.type === 'directory'" class="file-input-container">
                <div v-if="param.multiple && Array.isArray(formValues[param.name])" class="file-list">
                  <div v-for="(dir, index) in formValues[param.name]" :key="index" class="selected-file">
                    <div class="file-info">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                      </svg>
                      <span class="file-path">{{ dir }}</span>
                    </div>
                    <button @click="removeFile(param.name, index)" class="remove-file">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  </div>
                </div>
                <div v-else-if="!param.multiple && formValues[param.name]" class="selected-file">
                  <div class="file-info">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <span class="file-path">{{ formValues[param.name] }}</span>
                  </div>
                  <button @click="formValues[param.name] = ''" class="remove-file">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                  </button>
                </div>
                <button @click="openFilePicker(param)" class="file-select-btn">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                  </svg>
                  {{ param.multiple ? 'Choose Directories' : 'Choose Directory' }}
                </button>
              </div>
              
              <!-- Flag input type -->
              <div v-else-if="param.type === 'flag'" class="flag-input-container">
                <label class="flag-switch">
                  <input 
                    type="checkbox"
                    :id="param.name"
                    v-model="formValues[param.name]"
                    class="flag-checkbox"
                  />
                  <span class="flag-slider">
                    <span class="flag-slider-inner"></span>
                  </span>
                  <span class="flag-label">{{ formValues[param.name] ? 'Enable' : 'Disable' }}</span>
                </label>
              </div>
              
              <!-- Select input type for parameters with options -->
              <div v-else-if="param.options && param.options.length > 0" class="select-input-container">
                <div class="select-wrapper">
                  <select 
                    :id="param.name"
                    v-model="formValues[param.name]"
                    class="param-select"
                  >
                    <option value="" disabled>Choose{{ param.name }}</option>
                    <option 
                      v-for="option in param.options" 
                      :key="option" 
                      :value="option"
                    >
                      {{ option }}
                    </option>
                  </select>
                  <div class="select-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </div>
                </div>
              </div>
              
              <!-- Other input types -->
              <div v-else class="input-group">
                <input 
                  :type="param.type === 'integer' ? 'number' : param.type === 'float' ? 'number' : 'text'"
                  :step="param.type === 'float' ? '0.01' : param.type === 'integer' ? '1' : undefined"
                  :id="param.name"
                  v-model="formValues[param.name]"
                  class="param-input"
                  :placeholder="param.default || 'Input' + param.name"
                />
                <div class="input-icon">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 6v6l4 2"></path>
                    <circle cx="12" cy="12" r="10"></circle>
                  </svg>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="no-params">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M12 16v-4"></path>
              <path d="M12 8h.01"></path>
            </svg>
            <p>This tool does not require parameter configuration</p>
          </div>
        </div>
        
        <!-- 运行按钮 -->
        <button @click="runTool" class="run-button" :disabled="taskStatus === 'running'">
          <div class="button-content">
            <svg v-if="taskStatus === 'running'" class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 1 1-9-9c4.97 0 9 4.03 9 9z"></path>
            </svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
            <span>{{ taskStatus === 'running' ? 'Running...' : 'Running ' + tool.tool_name }}</span>
          </div>
        </button>
      </div>

      <!-- 实时日志区域 -->
      <div class="logs-section">
        <div class="logs-header">
          <div class="logs-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            <h4>Real-time Logs</h4>
          </div>
          <div class="logs-actions">
            <button @click="clearLogs" class="clear-logs-btn" title="Clear Logs">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 6h18l-2 13H5L3 6z"></path>
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
                  <button @click="showVerboseLogs = !showVerboseLogs" 
                          class="toggle-verbose-btn" 
                          :class="{ active: showVerboseLogs }"
                          :title="showVerboseLogs ? 'Hide system messages' : 'Show system messages'">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 12l2 2 4-4"></path>
                <path d="M21 12c-1 0-3-1-3-3s2-3 3-3 3 1 3 3-2 3-3 3"></path>
                <path d="M3 12c1 0 3-1 3-3s-2-3-3-3-3 1-3 3 2 3 3 3"></path>
              </svg>
            </button>
            <span class="log-count">{{ filteredLogs.length }} / {{ allLogs.length }} logs</span>
          </div>
        </div>
        <div class="logs-container" ref="logsContainer" :class="{ empty: filteredLogs.length === 0 }">
          <div v-if="filteredLogs.length === 0" class="empty-logs">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <circle cx="9" cy="9" r="2"></circle>
              <path d="M21 15l-3.086-3.086a2 2 0 0 0-2.828 0L6 21"></path>
            </svg>
              <p>Run the tool to view real-time output</p>
              <span>Logs will be displayed here in real-time</span>
          </div>
          <div v-for="(log, index) in filteredLogs" 
               :key="index" 
               class="log-line"
               :class="getLogLineClass(log)"
          >
            <span class="log-prefix">{{ getLogPrefix(log) }}</span>
            <span class="log-content">{{ log.data }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- 空状态 -->
  <div v-else class="loading-pane">
    <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 19l7-7 3 3-7 7-3-3z"></path>
      <path d="m18 13-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"></path>
      <path d="m2 2 7.586 7.586"></path>
      <circle cx="11" cy="11" r="2"></circle>
    </svg>
    <p>Select a tool from the sidebar to start using</p>
  </div>
  
  <!-- File Picker Component -->
  <FilePicker
    v-if="showFilePicker"
    :project-id="route.params.id"
    :extensions="currentPickerParam?.extensions || []"
    :multiple="currentPickerParam?.multiple || false"
    :select-directories="currentPickerParam?.type === 'directory'"
    v-model="tempFileSelection"
    @close="closeFilePicker"
  />

  <div v-if="showSuggestionModal" class="parameter-suggestion-overlay" @click="closeSuggestionModal">
    <div class="parameter-suggestion-card" @click.stop>
      <header class="suggestion-header">
        <div>
          <h4>AI Parameter Suggestions</h4>
          <p v-if="suggestionPayload?.summary">{{ suggestionPayload.summary }}</p>
        </div>
        <button class="suggestion-close" @click="closeSuggestionModal" title="Close">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </header>

      <div v-if="suggestionPayload?.warnings?.length" class="suggestion-section warnings">
        <strong>Notes</strong>
        <ul>
          <li v-for="warning in suggestionPayload.warnings" :key="warning">{{ warning }}</li>
        </ul>
      </div>

      <div v-if="suggestionPayload?.missing_info?.length" class="suggestion-section missing-info">
        <strong>Missing Info</strong>
        <ul>
          <li v-for="missing in suggestionPayload.missing_info" :key="missing">{{ missing }}</li>
        </ul>
      </div>

      <div class="suggestion-list">
        <div v-if="suggestionEntries.length === 0" class="suggestion-empty">
          No suggestions were returned for this tool.
        </div>

        <label v-for="entry in suggestionEntries" :key="entry.name" class="suggestion-item">
          <input
            type="checkbox"
            v-model="suggestionSelections[entry.name]"
          />
          <div class="suggestion-details">
            <div class="suggestion-title">
              <span class="param-name">{{ entry.name }}</span>
              <span class="param-type">{{ entry.type }}</span>
            </div>
            <div class="suggestion-values">
              <span>Current: <em>{{ entry.current }}</em></span>
              <span>Suggested: <em>{{ entry.suggested }}</em></span>
            </div>
            <p v-if="entry.reasoning" class="suggestion-reasoning">{{ entry.reasoning }}</p>
          </div>
        </label>
      </div>

      <footer class="suggestion-actions">
        <button class="secondary-btn" @click="closeSuggestionModal">Cancel</button>
        <button class="primary-btn" @click="applyParameterSuggestions" :disabled="suggestionEntries.length === 0">
          Apply Selected
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import FilePicker from './FilePicker.vue';

const route = useRoute();
const tool = ref(null);
const formValues = ref({});
const allLogs = ref([]); // 存储所有日志
const taskStatus = ref('not_found');
const logsContainer = ref(null);
const showVerboseLogs = ref(false); // 控制是否显示详细日志
const toolLibrary = ref({});

// 参数填充相关状态
const isParameterFilling = ref(false);

const showSuggestionModal = ref(false);
const suggestionPayload = ref(null);
const suggestionSelections = ref({});

// 计算属性 - 过滤后的日志
const filteredLogs = computed(() => {
  if (showVerboseLogs.value) {
    return allLogs.value; // 显示所有日志
  }
  
  // 过滤掉系统消息和调试信息
  return allLogs.value.filter(log => {
    if (!log.data) return true;
    
    // 保留错误和警告
    if (log.data.includes('[ERROR]') || log.data.includes('[WARN]') || 
        log.data.includes('error') || log.data.includes('Error') ||
        log.data.includes('warning') || log.data.includes('Warning')) {
      return true;
    }
    
    // 过滤系统消息（除了开始执行的消息）
    if (log.data.includes('[SYSTEM]')) {
      return log.data.includes('Starting command:') || 
             log.data.includes('Command completed') ||
             log.data.includes('Command failed');
    }
    
    return true; // 保留其他日志
  });
});

// File picker state
const showFilePicker = ref(false);
const currentPickerParam = ref(null);
const tempFileSelection = ref(null);

// 状态管理
const isRefreshingStatus = ref(false);

// 连接管理
let eventSource = null;

const scrollToBottom = () => {
  nextTick(() => {
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight;
    }
  });
};

const fetchToolLibrary = async () => {
  try {
    const response = await fetch('/api/tools');
    toolLibrary.value = await response.json();
  } catch (error) {
    console.error('Failed to load tool library:', error);
  }
};

const resetSuggestionState = () => {
  showSuggestionModal.value = false;
  suggestionPayload.value = null;
  suggestionSelections.value = {};
};

const updateTool = () => {
  const toolName = route.params.tool;
  if (!toolName) {
    tool.value = null;
    resetSuggestionState();
    return;
  }
  const foundTool = toolLibrary.value[toolName.toLowerCase()];
  if (foundTool) {
    tool.value = foundTool;
    formValues.value = {};
    tool.value.parameters.forEach(p => {
      if (p.type === 'file' || p.type === 'directory') {
        formValues.value[p.name] = p.multiple ? [] : '';
      } else if (p.type === 'flag') {
        formValues.value[p.name] = p.default || false;
      } else if (p.options && p.options.length > 0) {
        // For parameters with options, use default if specified and valid, otherwise use first option
        if (p.default && p.options.includes(p.default)) {
          formValues.value[p.name] = p.default;
        } else {
          formValues.value[p.name] = p.options[0];
        }
      } else {
        formValues.value[p.name] = p.default || '';
      }
    });
    
    // 重置工具状态和日志
    taskStatus.value = 'not_found';
    
    // 重新检查状态
    checkTaskStatus();
    resetSuggestionState();
  } else {
    tool.value = null;
    resetSuggestionState();
  }
};

const openFilePicker = (param) => {
  currentPickerParam.value = param;
  tempFileSelection.value = formValues.value[param.name];
  showFilePicker.value = true;
};

const closeFilePicker = () => {
  if (currentPickerParam.value && tempFileSelection.value !== null) {
    formValues.value[currentPickerParam.value.name] = tempFileSelection.value;
  }
  showFilePicker.value = false;
  currentPickerParam.value = null;
  tempFileSelection.value = null;
};

const removeFile = (paramName, index) => {
  if (Array.isArray(formValues.value[paramName])) {
    formValues.value[paramName].splice(index, 1);
  }
};

const runTool = async () => {
  if (!tool.value) return;
  allLogs.value = []; // Clear previous logs
  
  // Close any existing connection before starting a new one
  if (eventSource) {
    eventSource.close();
  }

  const response = await fetch(`/api/pipeline/${route.params.id}/run/${tool.value.tool_name.toLowerCase()}`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formValues.value)
  });
  const result = await response.json();
  
  if(response.ok) {
    allLogs.value.push({ data: `[SYSTEM] Starting command: ${result.command}` });
    connectToLogStream();
  } else {
    allLogs.value.push({ data: `[SYSTEM] Error: ${result.error}` });
  }
};

let statusInterval = null;

const checkTaskStatus = async () => {
  const projectId = route.params.id;
  if (!projectId) return;
  try {
    const response = await fetch(`/api/pipeline/${projectId}/task-status`);
    if (response.ok) {
      const data = await response.json();
      const newStatus = data.status;
      
      // 只有状态真正改变时才更新
      if (taskStatus.value !== newStatus) {
        taskStatus.value = newStatus;
        
        // 如果任务完成或出错，关闭事件源
        if (newStatus !== 'running' && eventSource) {
          eventSource.close();
          eventSource = null;
        }
      }
    } else {
      console.error('Failed to fetch task status:', response.statusText);
      taskStatus.value = 'error';
    }
  } catch (error) {
    console.error('Error checking task status:', error);
    taskStatus.value = 'error';
  }
};

const connectToLogStream = () => {
  const projectId = route.params.id;
  if (!projectId) return;

  eventSource = new EventSource(`/api/pipeline/${projectId}/stream-logs`);

  eventSource.onmessage = (event) => {
    // 过滤掉无用的日志消息
    if (shouldFilterLog(event.data)) {
      return;
    }
    
    allLogs.value.push({ data: event.data });
    scrollToBottom();
  };

  eventSource.onerror = (err) => {
    console.error('EventSource failed:', err);
  };
};

const getLogLineClass = (log) => {
  if (log.data.startsWith('[SYSTEM]')) return 'system';
  if (log.data.includes('error') || log.data.includes('Error')) return 'error';
  if (log.data.includes('warning') || log.data.includes('Warning')) return 'warning';
  return '';
};

const getLogPrefix = (log) => {
  if (log.data.startsWith('[SYSTEM]')) return 'SYS';
  if (log.data.includes('error') || log.data.includes('Error')) return 'ERR';
  if (log.data.includes('warning') || log.data.includes('Warning')) return 'WRN';
  return 'LOG';
};

const getStatusText = () => {
  const statusMap = {
    'running': 'Running',
    'completed': 'Completed',
    'error': 'Error',
    'not_found': 'Ready',
    'idle': 'Idle',
    'stopped': 'Stopped'
  };
  return statusMap[taskStatus.value] || 'Unknown';
};

const getParamTypeDisplay = (param) => {
  if (param.options && param.options.length > 0) {
    return '选择项';
  }
  
  const typeMap = {
    'file': 'File',
    'directory': 'Directory',
    'integer': 'Integer',
    'float': 'Float',
    'string': 'Text',
    'boolean': 'Boolean',
    'flag': 'Switch'
  };
  return typeMap[param.type] || param.type;
};

const clearLogs = () => {
  allLogs.value = [];
};

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
      const lastSystemMessage = allLogs.value
        .slice(-5) // 检查最近5条消息
        .reverse()
        .find(log => log.data && log.data.includes('[SYSTEM]'));
      
      if (lastSystemMessage && lastSystemMessage.data.includes('Connection closed')) {
        return true; // 过滤重复的连接关闭消息
      }
    }
    
    // 过滤掉过于频繁的 "Ready to receive" 消息
    if (logData.includes('Ready to receive new tasks')) {
      const recentReadyMessages = allLogs.value
        .slice(-3)
        .filter(log => log.data && log.data.includes('Ready to receive new tasks'));
      
      if (recentReadyMessages.length > 0) {
        return true; // 过滤重复的就绪消息
      }
    }
  }
  
  return false;
};

const refreshStatus = async () => {
  isRefreshingStatus.value = true;
  try {
    await checkTaskStatus();
  } finally {
    // 显示加载状态至少300ms，让用户看到反馈
    setTimeout(() => {
      isRefreshingStatus.value = false;
    }, 300);
  }
};

const normalizeSuggestion = (suggestion) => {
  if (suggestion && typeof suggestion === 'object' && !Array.isArray(suggestion) && 'value' in suggestion) {
    return {
      value: suggestion.value,
      reasoning: suggestion.reasoning || ''
    };
  }
  return {
    value: suggestion,
    reasoning: ''
  };
};

const formatValue = (value) => {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : '—';
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch (error) {
      return String(value);
    }
  }
  return String(value);
};

const suggestionEntries = computed(() => {
  if (!suggestionPayload.value || !tool.value) return [];
  const suggestions = suggestionPayload.value.suggestions || {};
  return tool.value.parameters
    .map(param => {
      if (!suggestions.hasOwnProperty(param.name)) return null;
      const normalized = normalizeSuggestion(suggestions[param.name]);
      return {
        name: param.name,
        type: param.type,
        current: formatValue(formValues.value[param.name]),
        suggested: formatValue(normalized.value),
        reasoning: normalized.reasoning
      };
    })
    .filter(Boolean);
});

const openParameterSuggestions = async () => {
  if (!tool.value) return;
  
  isParameterFilling.value = true;
  
  try {
    // 准备工具参数schema
    const toolParameters = {};
    tool.value.parameters.forEach(param => {
      toolParameters[param.name] = {
        type: param.type,
        description: param.description,
        required: param.required || false,
        default: param.default,
        extensions: param.extensions,
        multiple: param.multiple
      };
    });
    
    // 调用参数填充API
    const response = await fetch('/api/parameter-fill/suggest', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        tool_name: tool.value.tool_name,
        tool_parameters: toolParameters,
        project_id: route.params.id,
        user_context: `用户正在配置${tool.value.tool_name}工具的参数`
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    
    if (result.success) {
      suggestionPayload.value = {
        suggestions: result.suggestions || {},
        summary: result.summary || '',
        warnings: result.warnings || [],
        missing_info: result.missing_info || []
      };
      suggestionSelections.value = Object.keys(suggestionPayload.value.suggestions).reduce((acc, key) => {
        acc[key] = true;
        return acc;
      }, {});
      showSuggestionModal.value = true;
    } else {
      throw new Error(result.error || '参数填充失败');
    }
    
  } catch (error) {
    console.error('Parameter fill error:', error);
    showParameterFillError(error.message);
  } finally {
    isParameterFilling.value = false;
  }
};

const closeSuggestionModal = () => {
  resetSuggestionState();
};

const applyParameterSuggestions = () => {
  if (!suggestionPayload.value) return;
  let appliedCount = 0;
  Object.entries(suggestionPayload.value.suggestions || {}).forEach(([paramName, suggestion]) => {
    if (!suggestionSelections.value[paramName]) return;
    if (Object.prototype.hasOwnProperty.call(formValues.value, paramName)) {
      const normalized = normalizeSuggestion(suggestion);
      formValues.value[paramName] = normalized.value;
      appliedCount += 1;
    }
  });

  if (appliedCount === 0) {
    showParameterFillError('No suggestions were selected.');
    return;
  }

  const summary = suggestionPayload.value.summary || `Applied ${appliedCount} suggestion(s).`;
  showParameterFillSuccess(summary, suggestionPayload.value.warnings || []);
  resetSuggestionState();
};

const showParameterFillSuccess = (summary = '', warnings = []) => {
  // Create a temporary success notification
  const successNotification = document.createElement('div');
  successNotification.className = 'parameter-fill-success';
  
  let warningsHtml = '';
  if (warnings.length > 0) {
    warningsHtml = `
      <div class="warnings">
        <small>⚠️ Notes:</small>
        ${warnings.map(w => `<small>• ${w}</small>`).join('')}
      </div>
    `;
  }
  
  successNotification.innerHTML = `
    <div class="success-content">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M20 6L9 17l-5-5"></path>
      </svg>
      <div class="message">
        <span>Parameter filling successful!</span>
        ${summary ? `<small>${summary}</small>` : ''}
        ${warningsHtml}
      </div>
    </div>
  `;
  
  document.body.appendChild(successNotification);
  
  // Auto-remove after 3 seconds
  setTimeout(() => {
    if (successNotification.parentNode) {
      successNotification.parentNode.removeChild(successNotification);
    }
  }, 3000);
};

const showParameterFillError = (errorMessage) => {
  // 创建一个临时的错误提示
  const errorNotification = document.createElement('div');
  errorNotification.className = 'parameter-fill-error';
  errorNotification.innerHTML = `
    <div class="error-content">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="15" y1="9" x2="9" y2="15"></line>
        <line x1="9" y1="9" x2="15" y2="15"></line>
      </svg>
      <div class="message">
        <span>参数填充失败</span>
        <small>${errorMessage}</small>
      </div>
    </div>
  `;
  
  document.body.appendChild(errorNotification);
  
  // 5秒后自动移除
  setTimeout(() => {
    if (errorNotification.parentNode) {
      errorNotification.parentNode.removeChild(errorNotification);
    }
  }, 5000);
};

onMounted(() => {
  fetchToolLibrary().then(() => {
    updateTool();
    checkTaskStatus();
    connectToLogStream();
    statusInterval = setInterval(checkTaskStatus, 2000);
  });
});

onUnmounted(() => {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  if (statusInterval) {
    clearInterval(statusInterval);
  }
});

// 监听工具变化，重置状态
watch(() => route.params.tool, (newTool, oldTool) => {
  if (newTool !== oldTool) {
    // 关闭之前的连接
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    
    // 更新工具配置
    updateTool();
    
    // 如果有新工具，建立新连接
    if (newTool) {
      connectToLogStream();
    }
  }
});

// 监听项目变化，重置所有状态
watch(() => route.params.id, () => {
  taskStatus.value = 'not_found';
  allLogs.value = [];
  
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  
  updateTool();
  checkTaskStatus();
  connectToLogStream();
});

</script>

<style scoped>
/* 全局滚动优化 */
* {
  box-sizing: border-box;
}

html, body {
  overflow-x: hidden;
}

/* 现代化工具界面样式 */
.tool-interface-container {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background: var(--surface-0);
  color: var(--gray-900);
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
}

/* 主容器滚动条样式 */
.tool-interface-container::-webkit-scrollbar {
  width: 12px;
}

.tool-interface-container::-webkit-scrollbar-track {
  background: var(--surface-2);
  border-radius: 6px;
}

.tool-interface-container::-webkit-scrollbar-thumb {
  background: var(--gray-300);
  border-radius: 6px;
  border: 2px solid var(--surface-2);
}

.tool-interface-container::-webkit-scrollbar-thumb:hover {
  background: var(--gray-400);
}

/* 现代化工具头部 */
.tool-header {
  background: var(--surface-1);
  border-bottom: var(--border-width) solid var(--border-color-light);
  padding: var(--spacing-4) var(--spacing-6);
  box-shadow: var(--shadow-xs);
}

.tool-header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.tool-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.tool-icon {
  width: 40px;
  height: 40px;
  background: var(--gradient-primary);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
  box-shadow: 0 10px 20px rgba(var(--accent-rgb), 0.2);
}

.tool-title {
  flex: 1;
  min-width: 0;
}

.tool-title h2 {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--gray-900);
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-title p {
  margin: 4px 0 0 0;
  font-size: var(--text-sm);
  color: var(--gray-500);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tool-status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.refresh-status-btn {
  background: none;
  border: none;
  color: var(--gray-500);
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  min-height: 32px;
}

.refresh-status-btn:hover {
  background: var(--surface-2);
  color: var(--primary-600);
}

.refresh-status-btn:active {
  transform: scale(0.95);
}

.refresh-status-btn.refreshing {
  color: var(--primary-600);
}

.refresh-status-btn.refreshing svg {
  animation: spin 1s linear infinite;
}

.refresh-status-btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.status-indicator.running {
  background: var(--warning-50);
  color: var(--warning-600);
  border: var(--border-width) solid rgba(245, 158, 11, 0.35);
}

.status-indicator.completed {
  background: var(--success-50);
  color: var(--success-600);
  border: var(--border-width) solid rgba(22, 163, 74, 0.3);
}

.status-indicator.error {
  background: var(--error-50);
  color: var(--error-600);
  border: var(--border-width) solid rgba(239, 68, 68, 0.35);
}

.status-indicator.not_found {
  background: var(--surface-2);
  color: var(--gray-600);
  border: var(--border-width) solid var(--border-color);
}

.status-indicator.idle {
  background: rgba(var(--accent-rgb), 0.12);
  color: var(--primary-700);
  border: var(--border-width) solid rgba(var(--accent-rgb), 0.3);
}

.status-indicator.stopped {
  background: var(--surface-2);
  color: var(--gray-600);
  border: var(--border-width) solid var(--border-color);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}

.status-indicator.running .status-dot {
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-weight: 600;
}

/* 工具主体 - 响应式Grid布局 */
.tool-body {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(420px, 1.1fr) minmax(540px, 1fr);
  gap: clamp(16px, 2vw, 32px);
  padding: clamp(16px, 2vw, 36px);
  min-height: 0;
  max-width: none;
  margin: 0;
  align-items: start;
}

.form-section, .logs-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.form-section {
  max-height: calc(100vh - 180px);
  overflow: visible;
}

.logs-section {
  min-height: clamp(380px, 50vh, 640px);
  max-height: calc(100vh - 180px);
}

/* 参数表单区域 */
.form-card {
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  border: var(--border-width) solid var(--border-color-light);
  box-shadow: var(--shadow-xs);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--surface-2);
  border-bottom: var(--border-width) solid var(--border-color-light);
  gap: 12px;
}

.form-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.form-header h4 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.form-header h4 svg {
  color: var(--primary-600);
  flex-shrink: 0;
}

.param-count {
  font-size: 11px;
  color: var(--gray-600);
  background: var(--surface-3);
  padding: 3px 6px;
  border-radius: 10px;
  font-weight: 500;
  white-space: nowrap;
}

.param-list {
  max-height: calc(100vh - 280px);
  overflow-y: auto;
  padding: var(--spacing-4) var(--spacing-6);
  flex: 1;
  -webkit-overflow-scrolling: touch;
}

.param-list::-webkit-scrollbar {
  width: 6px;
}

.param-list::-webkit-scrollbar-track {
  background: var(--surface-2);
  border-radius: 3px;
}

.param-list::-webkit-scrollbar-thumb {
  background: var(--gray-300);
  border-radius: 3px;
}

.param-list::-webkit-scrollbar-thumb:hover {
  background: var(--gray-400);
}

.param-row {
  margin-bottom: 20px;
}

.param-row:last-child {
  margin-bottom: 0;
}

.param-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 8px;
}

.param-label {
  font-weight: var(--font-semibold);
  color: var(--gray-800);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.required-indicator {
  color: var(--error-500);
  font-weight: 700;
}

.param-type {
  font-size: 11px;
  color: var(--gray-500);
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: 6px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.param-description {
  font-size: 12px;
  color: var(--gray-500);
  margin: 0 0 10px 0;
  line-height: 1.4;
}

.input-group {
  position: relative;
}

.param-input {
  width: 100%;
  padding: 10px 14px;
  border: var(--border-width) solid var(--border-color);
  border-radius: 8px;
  font-size: 14px;
  background: var(--surface-1);
  transition: all var(--transition-base);
  box-sizing: border-box;
}

.param-input:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
}

.param-input[type="number"] {
  padding-right: 36px;
}

.param-input:hover {
  border-color: var(--border-color-dark);
}

.param-input:disabled {
  background: var(--surface-2);
  color: var(--gray-400);
  cursor: not-allowed;
}

.input-icon {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--gray-400);
  pointer-events: none;
}

.no-params {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
  color: var(--gray-500);
  text-align: center;
}

.no-params svg {
  color: var(--gray-300);
  margin-bottom: 12px;
}

.no-params p {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

/* 运行按钮 */
.run-button {
  margin: 16px 20px 20px;
  padding: 0;
  border: none;
  border-radius: 10px;
  background: var(--gradient-primary);
  color: white;
  font-weight: var(--font-semibold);
  font-size: 15px;
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: 0 10px 20px rgba(var(--accent-rgb), 0.18);
  position: relative;
  overflow: visible;
  min-height: 48px;
}

.run-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(var(--accent-rgb), 0.25);
}

.run-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
  background: var(--gray-400);
}

.button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px 20px;
  width: 100%;
  height: 100%;
  position: relative;
  z-index: 1;
}

.button-content span {
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
}

.spinner {
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 文件选择区域 */
.file-input-container {
  width: 100%;
}

.file-select-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  background: var(--surface-2);
  border: 1.5px dashed var(--border-color);
  border-radius: 8px;
  font-size: 13px;
  color: var(--gray-600);
  cursor: pointer;
  transition: all var(--transition-base);
  box-sizing: border-box;
  min-height: 40px;
}

.file-select-btn:hover {
  background: var(--surface-1);
  border-color: rgba(var(--accent-rgb), 0.4);
  color: var(--primary-600);
  box-shadow: var(--shadow-xs);
}

.file-select-btn svg {
  flex-shrink: 0;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.selected-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: var(--surface-2);
  border: var(--border-width) solid var(--border-color-light);
  border-radius: 6px;
  font-size: 12px;
  transition: all var(--transition-base);
  gap: 8px;
}

.selected-file:hover {
  background: var(--surface-3);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.file-info svg {
  color: var(--gray-500);
  flex-shrink: 0;
}

.file-path {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--gray-700);
  font-family: var(--font-family-mono);
  font-size: 11px;
}

.remove-file {
  background: none;
  border: none;
  color: var(--gray-500);
  cursor: pointer;
  padding: 3px;
  border-radius: 4px;
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  min-width: 24px;
  min-height: 24px;
}

.remove-file:hover {
  background: var(--error-50);
  color: var(--error-600);
}

/* 日志区域 */
.logs-section {
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  border: var(--border-width) solid var(--border-color-light);
  box-shadow: var(--shadow-xs);
  overflow: hidden;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--surface-2);
  border-bottom: var(--border-width) solid var(--border-color-light);
  gap: 12px;
}

.logs-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.logs-title h4 {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--gray-900);
}

.logs-title svg {
  color: var(--primary-600);
  flex-shrink: 0;
}

.logs-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.clear-logs-btn {
  background: none;
  border: none;
  color: var(--gray-500);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  min-height: 28px;
}

.clear-logs-btn:hover {
  background: var(--surface-3);
  color: var(--error-600);
}

.toggle-verbose-btn {
  background: none;
  border: none;
  color: var(--gray-500);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  min-height: 28px;
}

.toggle-verbose-btn:hover {
  background: var(--surface-3);
  color: var(--gray-700);
}

.toggle-verbose-btn.active {
  background: var(--primary-600);
  color: white;
}

.toggle-verbose-btn.active:hover {
  background: var(--primary-700);
}

.log-count {
  font-size: 11px;
  color: var(--gray-600);
  background: var(--surface-3);
  padding: 3px 6px;
  border-radius: 10px;
  font-weight: 500;
  white-space: nowrap;
}

.logs-container {
  flex: 1;
  background: var(--dark-bg);
  color: var(--text-light);
  font-family: var(--font-family-mono);
  font-size: 12px;
  padding: var(--spacing-4);
  overflow-y: auto;
  min-height: clamp(280px, 38vh, 480px);
  max-height: clamp(460px, 62vh, 760px);
  line-height: 1.5;
  -webkit-overflow-scrolling: touch;
}

.logs-container::-webkit-scrollbar {
  width: 6px;
}

.logs-container::-webkit-scrollbar-track {
  background: var(--dark-bg-secondary);
  border-radius: 3px;
}

.logs-container::-webkit-scrollbar-thumb {
  background: var(--gray-700);
  border-radius: 3px;
}

.logs-container::-webkit-scrollbar-thumb:hover {
  background: var(--gray-600);
}

.logs-container.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-8) var(--spacing-4);
}

.empty-logs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--gray-300);
  text-align: center;
  gap: var(--spacing-3);
  max-width: 360px;
}

.empty-logs svg {
  color: var(--gray-500);
  margin-bottom: var(--spacing-1);
}

.empty-logs p {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-light);
}

.empty-logs span {
  font-size: var(--text-sm);
  color: var(--gray-400);
}

.log-line {
  margin-bottom: 3px;
  padding: 3px 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  border-left: 2px solid transparent;
  padding-left: 6px;
}

.log-line.system {
  border-left-color: var(--primary-500);
  background: rgba(var(--accent-rgb), 0.12);
}

.log-line.error {
  border-left-color: var(--error-500);
  background: rgba(239, 68, 68, 0.12);
}

.log-line.warning {
  border-left-color: var(--warning-500);
  background: rgba(245, 158, 11, 0.12);
}

.log-prefix {
  font-size: 10px;
  font-weight: var(--font-semibold);
  padding: 2px 5px;
  border-radius: 3px;
  min-width: 28px;
  text-align: center;
  flex-shrink: 0;
}

.log-line.system .log-prefix {
  background: var(--primary-500);
  color: white;
}

.log-line.error .log-prefix {
  background: var(--error-500);
  color: white;
}

.log-line.warning .log-prefix {
  background: var(--warning-500);
  color: white;
}

.log-line:not(.system):not(.error):not(.warning) .log-prefix {
  background: var(--gray-500);
  color: white;
}

.log-content {
  flex: 1;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.4;
  font-size: 11px;
}

/* 空状态页面 */
.loading-pane {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 100px);
  padding: 32px 16px;
  color: var(--gray-500);
  text-align: center;
  gap: 12px;
}

.loading-pane svg {
  color: var(--gray-300);
  margin-bottom: 6px;
}

.loading-pane p {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

/* 智能填充按钮 */
.smart-fill-btn {
  background: var(--gradient-primary);
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 80px;
  justify-content: center;
  white-space: nowrap;
}

.smart-fill-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(var(--accent-rgb), 0.3);
}

.smart-fill-btn.active {
  background: linear-gradient(135deg, var(--success-500) 0%, var(--success-600) 100%);
  box-shadow: 0 2px 8px rgba(22, 163, 74, 0.3);
}

.smart-fill-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.smart-fill-btn .spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s ease-in-out infinite;
}

/* 参数填充成功提示 */
.parameter-fill-success {
  position: fixed;
  top: 16px;
  right: 16px;
  background: linear-gradient(135deg, var(--success-500) 0%, var(--success-600) 100%);
  color: white;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(22, 163, 74, 0.3);
  z-index: 10000;
  animation: slideInRight 0.3s ease-out;
  max-width: 320px;
}

.success-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.success-content .message {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.success-content .message span {
  font-weight: 600;
  font-size: 0.8rem;
}

.success-content .message small {
  font-size: 0.7rem;
  opacity: 0.9;
  line-height: 1.3;
}

.success-content .warnings {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.success-content .warnings small {
  display: block;
  margin-bottom: 2px;
}

/* 参数填充错误提示 */
.parameter-fill-error {
  position: fixed;
  top: 16px;
  right: 16px;
  background: linear-gradient(135deg, var(--error-500) 0%, var(--error-600) 100%);
  color: white;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
  z-index: 10000;
  animation: slideInRight 0.3s ease-out;
  max-width: 320px;
}

.error-content {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.error-content .message {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.error-content .message span {
  font-weight: 600;
  font-size: 0.8rem;
}

.error-content .message small {
  font-size: 0.7rem;
  opacity: 0.9;
  line-height: 1.3;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* 参数建议弹窗 */
.parameter-suggestion-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.parameter-suggestion-card {
  width: min(720px, 92vw);
  max-height: 80vh;
  background: var(--surface-1);
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color-light);
  background: linear-gradient(180deg, rgba(var(--accent-rgb), 0.12), rgba(255, 255, 255, 0.9));
}

.suggestion-header h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.suggestion-header p {
  margin: 6px 0 0;
  color: var(--gray-600);
  font-size: 0.85rem;
}

.suggestion-close {
  border: none;
  background: var(--surface-1);
  color: var(--gray-500);
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.suggestion-close:hover {
  background: var(--surface-2);
  color: var(--gray-800);
}

.suggestion-section {
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color-light);
}

.suggestion-section strong {
  display: block;
  margin-bottom: 6px;
  font-size: 0.8rem;
  color: var(--gray-700);
}

.suggestion-section ul {
  margin: 0;
  padding-left: 18px;
  color: var(--gray-600);
  font-size: 0.8rem;
  line-height: 1.4;
}

.suggestion-list {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.suggestion-empty {
  padding: 12px;
  border-radius: 10px;
  background: var(--surface-2);
  color: var(--gray-600);
  font-size: 0.85rem;
  text-align: center;
}

.suggestion-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--border-color-light);
  background: var(--surface-0);
}

.suggestion-item input[type="checkbox"] {
  margin-top: 4px;
}

.suggestion-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.suggestion-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.param-name {
  font-weight: 600;
  color: var(--gray-900);
}

.param-type {
  font-size: 0.7rem;
  color: var(--gray-500);
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: 999px;
}

.suggestion-values {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.78rem;
  color: var(--gray-700);
}

.suggestion-values em {
  font-style: normal;
  color: var(--gray-900);
  font-weight: 500;
}

.suggestion-reasoning {
  margin: 0;
  font-size: 0.78rem;
  color: var(--gray-600);
}

.suggestion-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 20px 18px;
  border-top: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.primary-btn,
.secondary-btn {
  border-radius: 8px;
  font-size: 0.8rem;
  padding: 8px 14px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.primary-btn {
  background: var(--primary-600);
  color: white;
  border-color: var(--primary-600);
}

.primary-btn:hover:not(:disabled) {
  background: var(--primary-700);
  border-color: var(--primary-700);
}

.primary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-btn {
  background: var(--surface-2);
  color: var(--gray-700);
  border-color: var(--border-color-light);
}

.secondary-btn:hover {
  background: var(--surface-3, #eef2f7);
}

/* Flag开关样式 */
.flag-input-container {
  display: flex;
  align-items: center;
}

.flag-switch {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.flag-checkbox {
  display: none;
}

.flag-slider {
  position: relative;
  width: 44px;
  height: 22px;
  background: var(--gray-200);
  border-radius: 11px;
  transition: background var(--transition-base);
  display: flex;
  align-items: center;
}

.flag-checkbox:checked + .flag-slider {
  background: var(--primary-600);
}

.flag-slider-inner {
  width: 18px;
  height: 18px;
  background: var(--surface-1);
  border-radius: 50%;
  box-shadow: var(--shadow-xs);
  transition: transform var(--transition-base);
  margin-left: 2px;
}

.flag-checkbox:checked + .flag-slider .flag-slider-inner {
  transform: translateX(22px);
}

.flag-label {
  font-size: 13px;
  font-weight: var(--font-medium);
  color: var(--gray-800);
}

/* Select下拉框样式 */
.select-input-container {
  position: relative;
}

.select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.param-select {
  width: 100%;
  padding: 10px 36px 10px 14px;
  border: var(--border-width) solid var(--border-color);
  border-radius: 8px;
  font-size: 13px;
  background: var(--surface-1);
  color: var(--gray-800);
  cursor: pointer;
  transition: all var(--transition-base);
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  min-height: 40px;
}

.param-select:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
}

.param-select:hover {
  border-color: var(--border-color-dark);
}

.param-select:disabled {
  background: var(--surface-2);
  color: var(--gray-400);
  cursor: not-allowed;
}

.param-select option {
  padding: 6px 10px;
  color: var(--gray-800);
}

.select-icon {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--gray-400);
  pointer-events: none;
  transition: transform var(--transition-base);
}

.param-select:focus + .select-icon {
  transform: translateY(-50%) rotate(180deg);
}

/* ============= 响应式断点 ============= */

/* 平板端 (768px - 1024px) */
@media (max-width: 1024px) {
  .tool-body {
    grid-template-columns: 320px 1fr;
    gap: 16px;
    padding: 16px;
  }
  
  .tool-header {
    padding: 12px 16px;
  }
  
  .tool-icon {
    width: 36px;
    height: 36px;
  }
  
  .tool-title h2 {
    font-size: 18px;
  }
  
  .form-header {
    padding: 12px 16px;
  }
  
  .param-list {
    padding: 12px 16px;
  }
  
  .logs-header {
    padding: 12px 16px;
  }
  
  .logs-container {
    font-size: 11px;
    padding: 10px;
  }
}

/* 移动端 (最大768px) */
@media (max-width: 768px) {
  .tool-body {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
    gap: 12px;
    padding: 12px;
    min-height: calc(100vh - 80px);
  }
  
  .tool-header {
    padding: 8px 12px;
  }
  
  .tool-header-content {
    gap: 8px;
  }
  
  .tool-info {
    gap: 8px;
  }
  
  .tool-icon {
    width: 32px;
    height: 32px;
  }
  
  .tool-title h2 {
    font-size: 16px;
  }
  
  .tool-title p {
    font-size: 12px;
  }
  
  .status-indicator {
    padding: 4px 8px;
    font-size: 11px;
    gap: 4px;
  }
  
  .status-dot {
    width: 5px;
    height: 5px;
  }
  
  .form-section {
    order: 1;
    max-height: none;
  }
  
  .logs-section {
    order: 2;
    min-height: 300px;
    max-height: 50vh;
  }
  
  .form-card {
    border-radius: 8px;
  }
  
  .form-header {
    padding: 10px 12px;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  
  .form-header-actions {
    justify-content: space-between;
    gap: 8px;
  }
  
  .form-header h4 {
    font-size: 14px;
  }
  
  .smart-fill-btn {
    padding: 5px 8px;
    font-size: 0.7rem;
    min-width: 70px;
  }
  
  .param-list {
    padding: 10px 12px;
    max-height: 40vh;
  }
  
  .param-row {
    margin-bottom: 16px;
  }
  
  .param-header {
    flex-direction: column;
    align-items: stretch;
    gap: 4px;
  }
  
  .param-label {
    font-size: 12px;
  }
  
  .param-type {
    align-self: flex-start;
    font-size: 10px;
  }
  
  .param-description {
    font-size: 11px;
    margin-bottom: 8px;
  }
  
  .param-input {
    padding: 8px 12px;
    font-size: 13px;
  }
  
  .file-select-btn {
    padding: 8px 10px;
    font-size: 12px;
  }
  
  .selected-file {
    padding: 6px 8px;
    font-size: 11px;
  }
  
  .file-path {
    font-size: 10px;
  }
  
  .flag-slider {
    width: 40px;
    height: 20px;
  }
  
  .flag-slider-inner {
    width: 16px;
    height: 16px;
  }
  
  .flag-checkbox:checked + .flag-slider .flag-slider-inner {
    transform: translateX(20px);
  }
  
  .flag-label {
    font-size: 12px;
  }
  
  .param-select {
    padding: 8px 32px 8px 12px;
    font-size: 12px;
  }
  
  .run-button {
    margin: 12px;
    min-height: 44px;
    border-radius: 8px;
  }
  
  .button-content {
    padding: 12px 16px;
  }
  
  .button-content span {
    font-size: 14px;
  }
  
  .logs-section {
    border-radius: 8px;
  }
  
  .logs-header {
    padding: 10px 12px;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  
  .logs-actions {
    justify-content: space-between;
  }
  
  .logs-title h4 {
    font-size: 14px;
  }
  
  .logs-container {
    padding: 8px;
    font-size: 10px;
    max-height: calc(50vh - 80px);
  }
  
  .log-line {
    gap: 6px;
    padding-left: 4px;
  }
  
  .log-prefix {
    font-size: 9px;
    min-width: 24px;
    padding: 1px 3px;
  }
  
  .log-content {
    font-size: 10px;
  }
  
  .loading-pane {
    padding: 20px 12px;
    min-height: calc(100vh - 80px);
  }
  
  .loading-pane p {
    font-size: 14px;
  }
  
  .parameter-fill-success,
  .parameter-fill-error {
    top: 8px;
    right: 8px;
    left: 8px;
    max-width: none;
    padding: 10px 12px;
  }
  
  .success-content,
  .error-content {
    gap: 8px;
  }
  
  .success-content .message span,
  .error-content .message span {
    font-size: 0.75rem;
  }
  
  .success-content .message small,
  .error-content .message small {
    font-size: 0.65rem;
  }
}

/* 小屏移动端 (最大480px) */
@media (max-width: 480px) {
  .tool-body {
    padding: 8px;
    gap: 8px;
  }
  
  .tool-header {
    padding: 6px 8px;
  }
  
  .tool-title h2 {
    font-size: 14px;
  }
  
  .tool-title p {
    font-size: 11px;
  }
  
  .form-header {
    padding: 8px 10px;
  }
  
  .param-list {
    padding: 8px 10px;
  }
  
  .param-input {
    padding: 6px 10px;
    font-size: 12px;
  }
  
  .run-button {
    margin: 8px;
    min-height: 40px;
  }
  
  .button-content {
    padding: 10px 12px;
  }
  
  .button-content span {
    font-size: 13px;
  }
  
  .logs-header {
    padding: 8px 10px;
  }
  
  .logs-container {
    padding: 6px;
    font-size: 9px;
  }
  
  .log-prefix {
    font-size: 8px;
    min-width: 20px;
  }
  
  .log-content {
    font-size: 9px;
  }
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .refresh-status-btn,
  .clear-logs-btn,
  .toggle-verbose-btn,
  .remove-file {
    min-width: 44px;
    min-height: 44px;
  }
  
  .param-input,
  .param-select,
  .file-select-btn {
    min-height: 44px;
  }
  
  .run-button {
    min-height: 48px;
  }
  
  .flag-slider {
    width: 48px;
    height: 24px;
  }
  
  .flag-slider-inner {
    width: 20px;
    height: 20px;
  }
  
  .flag-checkbox:checked + .flag-slider .flag-slider-inner {
    transform: translateX(24px);
  }
}
</style>
