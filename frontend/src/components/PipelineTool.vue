<template>
  <div class="tool-interface-container" v-if="tool">
    <header class="tool-header">
      <div class="tool-header-content">
        <div class="tool-info">
          <div class="tool-icon">
            <Icon name="wrench" :size="22" />
          </div>
          <div class="tool-title">
            <h2>{{ tool.tool_name }}</h2>
            <div class="tool-meta">
              <span v-if="tool.section_title" class="meta-badge section">{{ tool.section_title }}</span>
            </div>
            <p :title="tool.description">{{ tool.description }}</p>
          </div>
        </div>
        <div class="tool-status">
          <div class="status-indicator" :class="tool.available === false ? 'failed' : taskStatus" :title="tool.availability_message || ''">
            <span class="status-dot"></span>
            <span class="status-text">{{ getStatusText() }}</span>
          </div>
        </div>
      </div>
    </header>

    <div class="tool-body">
      <!-- 参数配置区域 -->
      <div class="form-section">
        <div class="form-card">
          <div class="form-header">
            <h4>
              <Icon name="sliders-horizontal" :size="17" />
              Setup
            </h4>
          </div>

          
          <div v-if="tool.parameters.length > 0" class="param-list">
            <div v-for="param in visibleParameters" :key="param.name" class="param-row">
              <div class="param-header">
                <label :for="param.name" class="param-label">
                  {{ toolParameterLabel(param) }}
                  <span v-if="param.required" class="required-indicator">*</span>
                </label>
              </div>
              <p class="param-description">{{ param.description }}</p>
              
              <!-- File input type -->
              <div v-if="param.type === 'file'" class="file-input-container">
                <div v-if="param.multiple && Array.isArray(formValues[param.name])" class="file-list">
                  <div v-for="(file, index) in formValues[param.name]" :key="index" class="selected-file">
                    <div class="file-info">
                      <Icon name="file" :size="16" />
                      <span class="file-path">{{ file }}</span>
                    </div>
                    <button type="button" @click="removeFile(param.name, index)" class="remove-file" title="Remove file" aria-label="Remove file">
                      <Icon name="x" :size="15" />
                    </button>
                  </div>
                </div>
                <div v-else-if="!param.multiple && formValues[param.name]" class="selected-file">
                  <div class="file-info">
                    <Icon name="file" :size="16" />
                    <span class="file-path">{{ formValues[param.name] }}</span>
                  </div>
                  <button type="button" @click="formValues[param.name] = ''" class="remove-file" title="Remove file" aria-label="Remove file">
                    <Icon name="x" :size="15" />
                  </button>
                </div>
                <button type="button" @click="openFilePicker(param)" class="file-select-btn">
                  <Icon name="file" :size="16" />
                  {{ param.multiple ? 'Choose Files' : 'Choose File' }}
                </button>
              </div>
              
              <!-- Directory input type -->
              <div v-else-if="param.type === 'directory' && param.path_role !== 'output'" class="file-input-container">
                <div v-if="param.multiple && Array.isArray(formValues[param.name])" class="file-list">
                  <div v-for="(dir, index) in formValues[param.name]" :key="index" class="selected-file">
                    <div class="file-info">
                      <Icon name="folder" :size="16" />
                      <span class="file-path">{{ dir }}</span>
                    </div>
                    <button type="button" @click="removeFile(param.name, index)" class="remove-file" title="Remove directory" aria-label="Remove directory">
                      <Icon name="x" :size="15" />
                    </button>
                  </div>
                </div>
                <div v-else-if="!param.multiple && formValues[param.name]" class="selected-file">
                  <div class="file-info">
                    <Icon name="folder" :size="16" />
                    <span class="file-path">{{ formValues[param.name] }}</span>
                  </div>
                  <button type="button" @click="formValues[param.name] = ''" class="remove-file" title="Remove directory" aria-label="Remove directory">
                    <Icon name="x" :size="15" />
                  </button>
                </div>
                <button type="button" @click="openFilePicker(param)" class="file-select-btn">
                  <Icon name="folder" :size="16" />
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
                    <option value="" disabled>Select an option</option>
                    <option 
                      v-for="option in param.options" 
                      :key="option" 
                      :value="option"
                    >
                      {{ option }}
                    </option>
                  </select>
                  <div class="select-icon">
                    <Icon name="chevron-down" :size="16" />
                  </div>
                </div>
              </div>
              
              <!-- Other input types -->
              <div v-else class="input-group">
                <input 
                  :type="param.type === 'integer' ? 'number' : param.type === 'float' ? 'number' : 'text'"
                  :step="param.type === 'float' ? '0.01' : param.type === 'integer' ? '1' : undefined"
                  :min="param.minimum"
                  :max="param.maximum"
                  :id="param.name"
                  v-model="formValues[param.name]"
                  class="param-input"
                  :placeholder="param.default ?? toolParameterLabel(param)"
                />
              </div>
            </div>
          </div>
          <button
            v-if="optionalParameterCount"
            type="button"
            class="optional-parameters-toggle"
            @click="showOptionalParameters = !showOptionalParameters"
          >
            {{ showOptionalParameters ? 'Hide optional parameters' : `Optional parameters (${optionalParameterCount})` }}
          </button>
          <div v-if="tool.notes?.length" class="tool-notes">
            <h5>Execution Notes</h5>
            <ul>
              <li v-for="note in tool.notes" :key="note">{{ note }}</li>
            </ul>
          </div>
          <div v-else-if="tool.parameters.length === 0" class="no-params">
            <Icon name="circle-check" :size="32" />
            <p>This tool does not require parameter configuration</p>
          </div>
        </div>
        
        <!-- 运行按钮 -->
        <button
          @click="runTool"
          class="run-button"
          :disabled="runDisabled"
          :title="tool.available === false ? tool.availability_message : hasMissingRequiredParameters ? 'Complete the required parameters first' : runButtonLabel"
        >
          <div class="button-content">
            <Icon v-if="taskStatus === 'starting' || taskStatus === 'running'" name="rotate-ccw" :size="18" spin />
            <Icon v-else name="play" :size="18" />
            <span>
              {{ taskStatus === 'starting' ? 'Starting...' : taskStatus === 'running' ? 'Running...' : taskStatus === 'queued' ? 'Queued...' : runButtonLabel }}
            </span>
          </div>
        </button>
      </div>

      <details v-if="allLogs.length || isTaskActive" class="logs-section" :open="isTaskActive">
        <summary class="logs-summary">
          <span>Run details</span>
          <span>{{ getStatusText() }}</span>
        </summary>
        <div class="logs-header">
          <div class="logs-actions">
            <button type="button" @click="clearLogs" class="clear-logs-btn" title="Clear logs" aria-label="Clear logs">
              <Icon name="trash-2" :size="16" />
            </button>
                  <button type="button" @click="showVerboseLogs = !showVerboseLogs"
                          class="toggle-verbose-btn" 
                          :class="{ active: showVerboseLogs }"
                          :title="showVerboseLogs ? 'Hide system messages' : 'Show system messages'">
              <Icon name="list" :size="16" />
            </button>
            <span class="log-count">{{ filteredLogs.length }} / {{ allLogs.length }} logs</span>
          </div>
        </div>
        <div class="logs-container" ref="logsContainer" :class="{ empty: filteredLogs.length === 0 }">
          <div v-if="filteredLogs.length === 0" class="empty-logs">
            <Icon name="square-terminal" :size="36" />
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
      </details>
    </div>
  </div>
  
  <!-- 空状态 -->
  <div v-else class="loading-pane">
    <Icon name="rotate-ccw" :size="28" spin />
    <p>Loading tool...</p>
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

</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import FilePicker from './FilePicker.vue';
import Icon from './ui/Icon.vue';
import { primaryToolParameters, toolParameterLabel } from '../lib/toolUi.js';

const route = useRoute();
const tool = ref(null);
const formValues = ref({});
const allLogs = ref([]); // 存储所有日志
const taskStatus = ref('not_found');
const logsContainer = ref(null);
const showVerboseLogs = ref(false); // 控制是否显示详细日志
const toolLibrary = ref({});
const showOptionalParameters = ref(false);

const primaryParameters = computed(() => primaryToolParameters(tool.value || {}));

const optionalParameterCount = computed(() => Math.max(0, (tool.value?.parameters?.length || 0) - primaryParameters.value.length));
const visibleParameters = computed(() => showOptionalParameters.value ? (tool.value?.parameters || []) : primaryParameters.value);
const isTaskActive = computed(() => ['queued', 'starting', 'running'].includes(taskStatus.value));

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
             log.data.includes('Queued job:') ||
             log.data.includes("Task '") ||
             log.data.includes('Cancellation requested');
    }
    
    return true; // 保留其他日志
  });
});

// File picker state
const showFilePicker = ref(false);
const currentPickerParam = ref(null);
const tempFileSelection = ref(null);

// 连接管理
let logPollTimer = null;
const currentJobId = ref(null);
const logOffset = ref(0);

const scrollToBottom = () => {
  nextTick(() => {
    if (logsContainer.value) {
      logsContainer.value.scrollTop = logsContainer.value.scrollHeight;
    }
  });
};

const stopLogPolling = () => {
  if (logPollTimer) {
    clearInterval(logPollTimer);
    logPollTimer = null;
  }
};

const pollLogs = async () => {
  if (!currentJobId.value) return;
  try {
    const response = await fetch(`/api/jobs/${currentJobId.value}/logs?offset=${logOffset.value}`);
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    if (typeof data.offset === 'number') {
      logOffset.value = data.offset;
    }
    if (data.content) {
      const lines = data.content.split('\n').filter(line => line !== '');
      if (lines.length > 0) {
        lines.forEach(line => {
          allLogs.value.push({ data: line });
        });
        scrollToBottom();
      }
    }
    if (data.status && !['starting', 'running', 'queued'].includes(data.status)) {
      taskStatus.value = data.status;
      stopLogPolling();
    }
  } catch (error) {
    console.error('Log polling failed:', error);
  }
};

const startLogPolling = () => {
  stopLogPolling();
  pollLogs();
  logPollTimer = setInterval(pollLogs, 2000);
};

const fetchToolLibrary = async () => {
  try {
    const response = await fetch('/api/tools');
    const payload = await response.json();
    if (!response.ok || !payload.success) {
      throw new Error(payload.error || 'Failed to load tool library');
    }
    toolLibrary.value = payload.tools_by_key || {};
  } catch (error) {
    console.error('Failed to load tool library:', error);
  }
};

const updateTool = () => {
  const toolName = decodeURIComponent(String(route.params.tool || '')).toLowerCase();
  if (!toolName) {
    tool.value = null;
    return;
  }
  const foundTool = toolLibrary.value[toolName.toLowerCase()];
  if (foundTool) {
    tool.value = foundTool;
    formValues.value = {};
    showOptionalParameters.value = false;
    tool.value.parameters.forEach(p => {
      if (p.type === 'file' || p.type === 'directory') {
        formValues.value[p.name] = p.multiple ? [] : '';
      } else if (p.type === 'flag') {
        formValues.value[p.name] = p.default ?? false;
      } else if (p.options && p.options.length > 0) {
        // For parameters with options, use default if specified and valid, otherwise use first option
        if (p.default !== undefined && p.default !== null && p.options.includes(p.default)) {
          formValues.value[p.name] = p.default;
        } else {
          formValues.value[p.name] = p.options[0];
        }
      } else {
        formValues.value[p.name] = p.default ?? '';
      }
    });
    
    // 重置工具状态和日志
    taskStatus.value = 'not_found';
    
    // 重新检查状态
    checkTaskStatus();
  } else {
    tool.value = null;
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
  stopLogPolling();

  if (hasMissingRequiredParameters.value) {
    allLogs.value.push({ data: '[SYSTEM] Error: Complete the required parameters before running.' });
    return;
  }

  try {
    const response = await fetch(`/api/pipeline/${route.params.id}/run/${encodeURIComponent(tool.value.id)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formValues.value)
    });
    const result = await response.json();

    if (response.ok) {
      currentJobId.value = result.job_id || null;
      logOffset.value = 0;
      taskStatus.value = result.status || 'queued';
      allLogs.value.push({ data: `[SYSTEM] Queued job: ${result.job_id}` });
      startLogPolling();
    } else {
      const details = Array.isArray(result.details) && result.details.length
        ? ` ${result.details.join('; ')}`
        : '';
      allLogs.value.push({ data: `[SYSTEM] Error: ${result.error || 'Failed to start task'}.${details}` });
    }
  } catch (error) {
    taskStatus.value = 'error';
    allLogs.value.push({ data: `[SYSTEM] Error: ${error.message || 'Backend is unavailable.'}` });
  }
};

const hasFormValue = (value) => Array.isArray(value)
  ? value.length > 0
  : value !== null && value !== undefined && value !== '';

const hasMissingRequiredParameters = computed(() => {
  if (!tool.value) return true;
  const missingExplicit = tool.value.parameters.some(
    (parameter) => parameter.required && !hasFormValue(formValues.value[parameter.name])
  );
  const requiredAny = tool.value.required_any || [];
  const missingRequiredGroup = requiredAny.length > 0
    && !requiredAny.some((name) => hasFormValue(formValues.value[name]));
  return missingExplicit || missingRequiredGroup;
});

const runDisabled = computed(() => (
  ['starting', 'running', 'queued'].includes(taskStatus.value)
  || hasMissingRequiredParameters.value
  || tool.value?.available === false
));

const runButtonLabel = computed(() => {
  return tool.value ? `Run ${tool.value.tool_name}` : 'Run';
});

let statusInterval = null;

const checkTaskStatus = async () => {
  const projectId = route.params.id;
  if (!projectId) return;
  try {
    const response = await fetch(`/api/pipeline/${projectId}/task-status`);
    if (response.ok) {
      const data = await response.json();
      const newStatus = data.status;
      if (data.job_id) {
        currentJobId.value = data.job_id;
      } else if (newStatus === 'not_found') {
        currentJobId.value = null;
      }

      // 只有状态真正改变时才更新
      if (taskStatus.value !== newStatus) {
        taskStatus.value = newStatus;
      }

      if (['starting', 'running', 'queued'].includes(newStatus)) {
        startLogPolling();
      } else {
        stopLogPolling();
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
  if (tool.value?.available === false) return 'Unavailable';
  const statusMap = {
    'queued': 'Queued',
    'starting': 'Starting',
    'running': 'Running',
    'completed': 'Completed',
    'error': 'Error',
    'failed': 'Failed',
    'canceled': 'Canceled',
    'not_found': 'Ready',
    'idle': 'Idle',
    'stopped': 'Stopped'
  };
  return statusMap[taskStatus.value] || 'Unknown';
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

let unmounted = false;

onMounted(() => {
  fetchToolLibrary().then(() => {
    // onUnmounted may already have run while this request was in flight, in
    // which case the interval created here would never be cleared.
    if (unmounted) return;
    updateTool();
    checkTaskStatus();
    statusInterval = setInterval(checkTaskStatus, 2000);
  });
});

onUnmounted(() => {
  unmounted = true;
  stopLogPolling();
  if (statusInterval) {
    clearInterval(statusInterval);
    statusInterval = null;
  }
});

// 监听工具变化，重置状态
watch(() => route.params.tool, (newTool, oldTool) => {
  if (newTool !== oldTool) {
    stopLogPolling();
    
    // 更新工具配置
    updateTool();
    
    logOffset.value = 0;
    currentJobId.value = null;
  }
});

// 监听项目变化，重置所有状态
watch(() => route.params.id, () => {
  taskStatus.value = 'not_found';
  allLogs.value = [];
  stopLogPolling();
  
  updateTool();
  checkTaskStatus();
  logOffset.value = 0;
  currentJobId.value = null;
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

/* 现代化工具头部 */
.tool-header {
  background: var(--surface-1);
  border-bottom: var(--border-width) solid var(--border-color-light);
  padding: 16px 20px;
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
  width: 36px;
  height: 36px;
  background: var(--primary-50);
  border: 1px solid var(--primary-100);
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-700);
  flex-shrink: 0;
}

.tool-title {
  flex: 1;
  min-width: 0;
}

.tool-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin: 4px 0 0;
}

.meta-badge {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0;
  white-space: nowrap;
}

.meta-badge.kind {
  background: rgba(var(--accent-rgb), 0.12);
  color: var(--primary-700);
}

.meta-badge.section {
  background: var(--surface-2);
  color: var(--gray-600);
  border: 1px solid var(--border-color-light);
}

.meta-badge.unavailable {
  background: var(--warning-50, #fff7ed);
  color: var(--warning-700, #9a3412);
  border: 1px solid var(--warning-200, #fed7aa);
}

.tool-title h2 {
  margin: 0;
  font-size: 22px;
  font-weight: var(--font-bold);
  color: var(--gray-900);
  line-height: 1.15;
}

.tool-title p {
  margin: 5px 0 0;
  font-size: 13px;
  color: var(--gray-500);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
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
  min-height: 26px;
  padding: 4px 9px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 500;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.status-indicator.starting {
  background: var(--accent-50);
  color: var(--accent-700);
  border: var(--border-width) solid var(--accent-200);
}

.status-indicator.running {
  background: var(--warning-50);
  color: var(--warning-600);
  border: var(--border-width) solid rgba(245, 158, 11, 0.35);
}

.status-indicator.queued {
  background: var(--warning-50);
  color: var(--warning-600);
  border: var(--border-width) solid rgba(245, 158, 11, 0.2);
}

.status-indicator.completed {
  background: var(--success-50);
  color: var(--success-600);
  border: var(--border-width) solid rgba(22, 163, 74, 0.3);
}

.status-indicator.failed {
  background: var(--error-50);
  color: var(--error-600);
  border: var(--border-width) solid rgba(239, 68, 68, 0.35);
}

.status-indicator.canceled {
  background: var(--surface-2);
  color: var(--gray-600);
  border: var(--border-width) solid var(--border-color);
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
  grid-template-columns: minmax(0, 760px);
  justify-content: center;
  gap: 16px;
  padding: clamp(16px, 2vw, 24px);
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
  gap: 14px;
  max-height: calc(100vh - 168px);
}

.logs-section {
  min-height: 0;
  max-height: none;
}

/* 参数表单区域 */
.form-card {
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  border: var(--border-width) solid var(--border-color-light);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 13px 16px;
  background: var(--surface-1);
  border-bottom: var(--border-width) solid var(--border-color-light);
  gap: 10px;
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

.param-list {
  padding: 16px;
  flex: 0 0 auto;
}

.param-row {
  margin-bottom: 16px;
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

.param-description {
  font-size: 12px;
  color: var(--gray-500);
  margin: 0 0 8px 0;
  line-height: 1.4;
}

.input-group {
  position: relative;
}

.param-input {
  width: 100%;
  height: var(--control-height);
  padding: 0 11px;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-base);
  font-size: 14px;
  background: var(--surface-1);
  transition: all var(--transition-base);
  box-sizing: border-box;
}

.param-input:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.14);
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

.optional-parameters-toggle {
  align-self: flex-start;
  margin: 0 var(--spacing-4) var(--spacing-4);
  padding: 7px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
  color: var(--gray-600);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
}

.optional-parameters-toggle:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

/* 运行按钮 */
.run-button {
  margin: 0;
  padding: 0;
  border: none;
  border-radius: var(--radius-base);
  background: var(--primary-600);
  color: white;
  font-weight: var(--font-semibold);
  font-size: 15px;
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast);
  position: relative;
  overflow: visible;
  min-height: 40px;
}

.run-button:hover:not(:disabled) {
  background: var(--primary-700);
}

.run-button:disabled {
  cursor: not-allowed;
  background: var(--gray-300);
  color: var(--gray-500);
}

.button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 16px;
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
  padding: 0 11px;
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  font-size: 13px;
  color: var(--gray-600);
  cursor: pointer;
  transition: all var(--transition-base);
  box-sizing: border-box;
  min-height: var(--control-height);
}

.file-select-btn:hover {
  background: var(--primary-50);
  border-color: var(--primary-300);
  color: var(--primary-600);
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
  overflow: hidden;
}

.logs-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-3);
  min-height: 46px;
  padding: 0 var(--spacing-4);
  color: var(--gray-700);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  list-style: none;
}

.logs-summary::-webkit-details-marker { display: none; }

.logs-summary span:last-child {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.logs-section[open] .logs-summary {
  border-bottom: 1px solid var(--border-color-light);
}

.logs-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 8px 12px;
  background: var(--surface-1);
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
  border-radius: var(--radius-full);
  font-weight: 500;
  white-space: nowrap;
}

.logs-container {
  flex: 1;
  background: var(--dark-bg);
  color: var(--text-light);
  font-family: var(--font-family-mono);
  font-size: 12px;
  padding: 16px;
  overflow-y: auto;
  min-height: clamp(260px, 34vh, 420px);
  max-height: clamp(400px, 54vh, 620px);
  line-height: 1.5;
  -webkit-overflow-scrolling: touch;
}

.tool-notes {
  padding: 0 18px 18px;
  color: var(--gray-700);
}

.tool-notes h5 {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 700;
  color: var(--gray-800);
}

.tool-notes ul {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
}

.tool-notes li {
  line-height: 1.5;
  color: var(--gray-600);
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
  font-size: 11px;
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
  min-height: 320px;
  padding: 32px 16px;
  color: var(--gray-500);
  text-align: center;
  gap: 12px;
}

.loading-pane svg {
  color: var(--gray-300);
}

.loading-pane p {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
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
  padding: 0 36px 0 11px;
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-base);
  font-size: 13px;
  background: var(--surface-1);
  color: var(--gray-800);
  cursor: pointer;
  transition: all var(--transition-base);
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  min-height: var(--control-height);
}

.param-select:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.14);
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
    grid-template-columns: minmax(0, 760px);
    justify-content: center;
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
  
  .form-header h4 {
    font-size: 14px;
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
    font-size: 11px;
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
    font-size: 11px;
    max-height: calc(50vh - 80px);
  }
  
  .log-line {
    gap: 6px;
    padding-left: 4px;
  }
  
  .log-prefix {
    font-size: 11px;
    min-width: 24px;
    padding: 1px 3px;
  }
  
  .log-content {
    font-size: 11px;
  }
  
  .loading-pane {
    padding: 20px 12px;
    min-height: calc(100vh - 80px);
  }
  
  .loading-pane p {
    font-size: 14px;
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
    font-size: 11px;
  }
  
  .log-prefix {
    font-size: 8px;
    min-width: 20px;
  }
  
  .log-content {
    font-size: 11px;
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
