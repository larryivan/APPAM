<template>
  <!-- Floating Button -->
  <div class="chatbot-trigger" v-if="!isOpen">
    <button @click="openChat" class="chat-button" title="AI Assistant">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
      <span class="status-dot" :class="connectionStatus"></span>
    </button>
  </div>

  <!-- Chat Window -->
  <div 
    v-if="isOpen"
    class="chatbot-window"
    :style="windowStyle"
  >
    <!-- Header -->
    <header class="chat-header" :class="{ mobile: isMobile }" @mousedown="handleHeaderMouseDown">
      <div class="header-info">
        <h3>AI Assistant</h3>
        <div class="status-indicator" :class="connectionStatus">
          <span class="status-dot"></span>
          <span class="status-text">{{ getStatusText() }}</span>
        </div>
        <!-- Project ID Status Display -->
        <div v-if="currentProjectId" class="project-info">
          <span class="project-id">🗂️ Project: {{ currentProjectId.slice(0, 8) }}...</span>
        </div>
        <div v-else class="project-info">
          <span class="no-project">⚠️ No Project Selected</span>
        </div>
      </div>
      <div class="header-actions">
        <button @click="clearConversation" class="control-btn" title="Clear Conversation">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"></polyline>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
        <button v-if="!isMobile" @click="toggleFullscreen" class="control-btn" title="Toggle Fullscreen">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="!isFullscreen" d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
            <path v-else d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path>
          </svg>
        </button>
        <button @click="closeChat" class="control-btn close-btn" title="Close">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </header>
    
    <!-- Chat Messages Area -->
    <div class="chat-messages" ref="chatWindow">
      <div v-for="(message, index) in messages" :key="index" class="message-wrapper" :class="message.sender">
        <div class="message-bubble">
          <div class="message-content" v-html="formatMessage(message.data)"></div>
          <div class="message-time">{{ formatTime(message.timestamp) }}</div>
          
          <!-- Tool Suggestion Button -->
          <button 
            v-if="message.tool_info" 
            @click="navigateToTool(message.tool_info.tool_name)" 
            class="tool-btn"
          >
            🔧 Use {{ message.tool_info.tool_name }}
          </button>
          

        </div>
      </div>
      
      <!-- Typing Indicator -->
      <div v-if="isTyping" class="message-wrapper bot">
        <div class="message-bubble typing">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
      
      <!-- Tool Suggestion Card -->
      <div v-if="toolSuggestion" class="tool-suggestion">
        <div class="suggestion-header">
          <span>🔧 AI Tool Recommendation</span>
          <button @click="clearToolSuggestion" class="close-btn">×</button>
        </div>
        <div class="suggestion-content">
          <h4>{{ toolSuggestion.tool.tool_name }}</h4>
          <p>{{ toolSuggestion.tool.description }}</p>
          
          <!-- Recommendation Reason -->
          <div class="recommendation-reason">
            <small><strong>Recommendation Reason:</strong> {{ toolSuggestion.reasoning || toolSuggestion.reason || 'Intelligent analysis recommendation' }}</small>
          </div>
          
          <!-- Confidence Display -->
          <div class="confidence-indicator">
            <div class="confidence-bar">
              <div class="confidence-fill" :style="{ width: (toolSuggestion.confidence * 100) + '%' }"></div>
            </div>
            <small>Confidence: {{ Math.round(toolSuggestion.confidence * 100) }}%</small>
          </div>
          
          <!-- Alternative Tools -->
          <div v-if="toolSuggestion.alternative_tools && toolSuggestion.alternative_tools.length > 0" class="alternative-tools">
            <h5>Other Related Tools:</h5>
            <div class="alternative-list">
              <button 
                v-for="altTool in toolSuggestion.alternative_tools" 
                :key="altTool" 
                @click="navigateToTool(altTool)"
                class="alternative-btn"
              >
                {{ altTool }}
              </button>
            </div>
          </div>
          
          <div class="suggestion-actions">
            <button @click="navigateToTool(toolSuggestion.tool.tool_name)" class="use-btn">Use This Tool</button>
            <button @click="clearToolSuggestion" class="dismiss-btn">Dismiss</button>
          </div>
        </div>
      </div>
      

      
      <!-- Smart Parameter Suggestion Card -->
      <div v-if="parameterSuggestion" class="parameter-suggestion">
        <div class="suggestion-header">
          <span>🔧 Smart Parameter Suggestion</span>
          <button @click="clearParameterSuggestion" class="close-btn">×</button>
        </div>
        <div class="suggestion-content">
          <h4>{{ parameterSuggestion.tool_name }}</h4>
          <p>{{ parameterSuggestion.summary }}</p>
          
          <!-- Parameter Preview -->
          <div class="parameter-preview">
            <h5>Suggested Parameter Settings:</h5>
            <div class="parameter-list">
              <div v-for="(param, name) in parameterSuggestion.suggested_parameters" :key="name" class="parameter-item">
                <div class="parameter-name">{{ name }}</div>
                <div class="parameter-value">{{ param.value }}</div>
                <div class="parameter-reason">{{ param.reasoning }}</div>
              </div>
            </div>
          </div>
          
          <div class="suggestion-actions">
            <button @click="acceptParameterSuggestion" class="use-btn">✓ Accept Suggestion</button>
            <button @click="clearParameterSuggestion" class="dismiss-btn">Dismiss</button>
          </div>
        </div>
      </div>

    </div>
    
    <!-- Input Area -->
    <footer class="chat-input">
      <div class="input-wrapper">
        <textarea 
          v-model="newMessage"
          @keydown="handleKeyDown"
          @input="adjustTextareaHeight"
          ref="messageInput"
          placeholder="Ask bioinformatics questions..."
          rows="1"
          :disabled="isTyping"
        ></textarea>
        <button 
          @click="sendMessage" 
          :disabled="!newMessage.trim() || isTyping"
          class="send-btn"
        >
          <svg v-if="!isTyping" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
          <div v-else class="spinner"></div>
        </button>
      </div>
    </footer>
    
    <!-- Resize Handles -->
    <div v-if="!isMobile && !isFullscreen" class="resize-handles">
      <div class="resize-handle resize-n" @mousedown="(e) => startResize('n', e)"></div>
      <div class="resize-handle resize-e" @mousedown="(e) => startResize('e', e)"></div>
      <div class="resize-handle resize-s" @mousedown="(e) => startResize('s', e)"></div>
      <div class="resize-handle resize-w" @mousedown="(e) => startResize('w', e)"></div>
      <div class="resize-handle resize-ne" @mousedown="(e) => startResize('ne', e)"></div>
      <div class="resize-handle resize-nw" @mousedown="(e) => startResize('nw', e)"></div>
      <div class="resize-handle resize-se" @mousedown="(e) => startResize('se', e)"></div>
      <div class="resize-handle resize-sw" @mousedown="(e) => startResize('sw', e)"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { marked } from 'marked';
import toolManager from '../utils/toolManager.js';

// Router
const router = useRouter();

// State
const isOpen = ref(false);
const isFullscreen = ref(false);
const isMobile = ref(false);
const messages = ref([]);
const newMessage = ref('');
const chatWindow = ref(null);
const messageInput = ref(null);
const isTyping = ref(false);
const connectionStatus = ref('disconnected');
const currentStreamMessage = ref('');
const toolSuggestion = ref(null);
const currentToolContext = ref(null);

const parameterSuggestion = ref(null);

// 参数填充相关状态已移除

// 工具推荐持久化存储
const TOOL_SUGGESTION_STORAGE_KEY = 'chatbot_tool_suggestion';

// 从localStorage加载工具推荐
const loadToolSuggestion = () => {
  try {
    const stored = localStorage.getItem(TOOL_SUGGESTION_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // 检查是否是当前项目的推荐
      if (parsed.projectId === currentProjectId.value) {
        toolSuggestion.value = parsed.suggestion;
      }
    }
  } catch (e) {
    console.error('Error loading tool suggestion:', e);
  }
};

// 保存工具推荐到localStorage
const saveToolSuggestion = (suggestion) => {
  try {
    const toStore = {
      suggestion: suggestion,
      projectId: currentProjectId.value,
      timestamp: Date.now()
    };
    localStorage.setItem(TOOL_SUGGESTION_STORAGE_KEY, JSON.stringify(toStore));
  } catch (e) {
    console.error('Error saving tool suggestion:', e);
  }
};

// 自动检测工具页面上下文
const detectToolContext = () => {
  const route = router.currentRoute.value;
  console.log('[CHATBOT] Detecting tool context...');
  console.log('[CHATBOT] Current route:', route);
  console.log('[CHATBOT] Route name:', route.name);
  console.log('[CHATBOT] Route params:', route.params);
  
  if (route.name === 'PipelineTool' && route.params.tool) {
    // 在工具页面，请求工具信息
    console.log('[CHATBOT] Detected tool page:', route.params.tool);
    console.log('[CHATBOT] Project ID:', route.params.id);
    requestToolContext(route.params.tool, route.params.id);
  } else {
    console.log('[CHATBOT] Not on a tool page or missing tool param');
    currentToolContext.value = null;
  }
};

// 请求工具页面的上下文信息
const requestToolContext = (toolName, projectId) => {
  // 发送消息请求工具页面提供上下文
  const message = {
    type: 'REQUEST_TOOL_CONTEXT',
    toolName: toolName,
    projectId: projectId
  };
  
  console.log(`[CHATBOT] Requesting tool context for ${toolName}`);
  console.log(`[CHATBOT] Sending message:`, message);
  
  window.postMessage(message, '*');
  
  // 设置超时，如果3秒内没有收到响应则警告
  setTimeout(() => {
    if (!currentToolContext.value) {
      console.warn(`[CHATBOT] No tool context response received for ${toolName} within 3 seconds`);
    }
  }, 3000);
};

// 处理来自工具页面的消息
const handleToolContextMessage = (event) => {
  console.log('Received message in chatbot:', event.data);
  
  if (event.data && event.data.type === 'OPEN_CHATBOT_FOR_PARAMETER_CONFIG') {
    console.log('Opening chatbot for parameter config:', event.data.toolContext);
    
    // 设置工具上下文
    currentToolContext.value = event.data.toolContext;
    
    // 打开聊天窗口
    isOpen.value = true;
    
    // 如果有建议消息，填入输入框
    if (event.data.suggestedMessage) {
      newMessage.value = event.data.suggestedMessage;
      
      // 检查是否需要自动发送
      if (event.data.autoSend !== false) {
        // 等待DOM更新后发送消息
        nextTick(() => {
          console.log('Auto-sending message:', event.data.suggestedMessage);
          sendMessage();
        });
      } else {
        // 只填入输入框，不自动发送
        console.log('Message filled in input box:', event.data.suggestedMessage);
        // 聚焦到输入框
        nextTick(() => {
          if (messageInput.value) {
            messageInput.value.focus();
          }
        });
      }
    }
  } else if (event.data && event.data.type === 'TOOL_CONTEXT_RESPONSE') {
    console.log('[CHATBOT] Received tool context response:', event.data);
    console.log('[CHATBOT] Tool context data:', event.data.toolContext);
    // 设置工具上下文
    currentToolContext.value = event.data.toolContext;
    console.log('[CHATBOT] Current tool context set to:', currentToolContext.value);
  }
};

// 清除工具推荐
const clearToolSuggestion = () => {
  toolSuggestion.value = null;
  try {
    localStorage.removeItem(TOOL_SUGGESTION_STORAGE_KEY);
  } catch (e) {
    console.error('Error clearing tool suggestion:', e);
  }
};

// 智能参数建议相关函数
const clearParameterSuggestion = () => {
  parameterSuggestion.value = null;
};

const acceptParameterSuggestion = () => {
  if (!parameterSuggestion.value) return;
  
  // 创建纯JavaScript对象，避免Vue响应式对象的序列化问题
  const messageData = {
    type: 'PARAMETER_APPLICATION',
    tool_name: String(parameterSuggestion.value.tool_name),
    parameters: JSON.parse(JSON.stringify(parameterSuggestion.value.suggested_parameters)),
    summary: String(parameterSuggestion.value.summary || '')
  };
  
  console.log('Sending parameter application message:', messageData);
  
  // 发送参数到工具页面
  window.postMessage(messageData, '*');
  
  // 清除建议
  clearParameterSuggestion();
};





// 项目ID计算属性
const currentProjectId = computed(() => {
  const route = router.currentRoute.value;
  return route.params.id || null;
});

// 窗口位置和大小
const windowPosition = ref({ x: window.innerWidth - 520, y: 100 });
const windowSize = ref({ width: 480, height: 600 });

// 拖拽状态
const isDragging = ref(false);
const dragOffset = ref({ x: 0, y: 0 });

// 调整大小状态
const isResizing = ref(false);
const resizeDirection = ref('');
const resizeStartPos = ref({ x: 0, y: 0 });
const resizeStartSize = ref({ width: 0, height: 0 });
const resizeStartWindowPos = ref({ x: 0, y: 0 });

// Socket connection - REMOVED, now using HTTP streaming
// const socket = io('ws://localhost:5000/chat', {
//   transports: ['websocket', 'polling']
// });

// Session ID
const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);

// 移动端检测
const detectMobile = () => {
  const userAgent = navigator.userAgent.toLowerCase();
  const mobileKeywords = ['mobile', 'iphone', 'android', 'blackberry', 'nokia', 'opera mini', 'windows mobile', 'windows phone', 'iemobile'];
  return mobileKeywords.some(keyword => userAgent.includes(keyword)) || window.innerWidth <= 768;
};

// 计算窗口样式
const windowStyle = computed(() => {
  if (isMobile.value || isFullscreen.value) {
    return {
      position: 'fixed',
      top: '0',
      left: '0',
      width: '100vw',
      height: '100vh',
      zIndex: 9999,
      borderRadius: isMobile.value ? '0' : '12px'
    };
  }
  
  return {
    position: 'fixed',
    top: `${windowPosition.value.y}px`,
    left: `${windowPosition.value.x}px`,
    width: `${windowSize.value.width}px`,
    height: `${windowSize.value.height}px`,
    zIndex: 1000
  };
});

// Methods
const openChat = () => {
  isMobile.value = detectMobile();
  
  if (isMobile.value) {
    isFullscreen.value = true;
  }
  
  isOpen.value = true;
  
  // 自动检测当前工具页面上下文
  detectToolContext();
  
  nextTick(() => {
    messageInput.value?.focus();
    scrollToBottom();
  });
};

const closeChat = () => {
  isOpen.value = false;
  isFullscreen.value = false;
};

const toggleFullscreen = () => {
  if (isMobile.value) return;
  isFullscreen.value = !isFullscreen.value;
};

const scrollToBottom = () => {
  nextTick(() => {
    if (chatWindow.value) {
      chatWindow.value.scrollTop = chatWindow.value.scrollHeight;
    }
  });
};

const formatMessage = (text) => {
  if (!text) return '';
  
  // Filter out debug information
  const cleanText = text
    .replace(/🔄 Iteration \d+\n/g, '')
    .replace(/🛠️ Calling tool:.*?\n/g, '')
    .replace(/📊 Tool Result:.*?\n/g, '')
    .replace(/🏁 Final Analysis:\n/g, '')
    .replace(/No tool calls were made\. Finishing\./g, '')
    .trim();
  
  marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false,
    highlight: function(code, lang) {
      // Basic syntax highlighting for common languages
      if (lang === 'python' || lang === 'py') {
        return `<code class="language-python">${escapeHtml(code)}</code>`;
      } else if (lang === 'bash' || lang === 'sh') {
        return `<code class="language-bash">${escapeHtml(code)}</code>`;
      } else if (lang === 'r' || lang === 'R') {
        return `<code class="language-r">${escapeHtml(code)}</code>`;
      } else {
        return `<code class="language-${lang || 'text'}">${escapeHtml(code)}</code>`;
      }
    }
  });
  
  return marked(cleanText);
};

const escapeHtml = (text) => {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, (m) => map[m]);
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
};

const getStatusText = () => {
  const statusMap = {
    connected: 'Online',
    connecting: 'Connecting',
    disconnected: 'Offline',
    error: 'Error'
  };
  return statusMap[connectionStatus.value] || 'Unknown';
};

const adjustTextareaHeight = () => {
  nextTick(() => {
    if (messageInput.value) {
      messageInput.value.style.height = 'auto';
      messageInput.value.style.height = Math.min(messageInput.value.scrollHeight, 100) + 'px';
    }
  });
};

const sendMessage = async () => {
  if (!newMessage.value.trim() || isTyping.value) return;
  
  const userMessage = newMessage.value.trim();
  

  
  messages.value.push({ 
    sender: 'user', 
    data: userMessage,
    timestamp: Date.now() / 1000
  });
  
  newMessage.value = '';
  adjustTextareaHeight();
  scrollToBottom();
  
  isTyping.value = true;
  currentStreamMessage.value = '';
  
  // Add a streaming message placeholder
  messages.value.push({
    sender: 'bot',
    data: '',
    timestamp: Date.now() / 1000,
    streaming: true
  });
  
      console.log('Sending message with tool context:', {
      message: userMessage,
      projectId: currentProjectId.value,
      sessionId: sessionId,
      toolContext: currentToolContext.value
    });

    try {
    const response = await fetch('/api/chatbot/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: userMessage,
        projectId: currentProjectId.value,
        sessionId: sessionId,
        toolContext: currentToolContext.value
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    // Handle streaming response
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      // Check for special markers
      if (buffer.includes('__TOOL_RECOMMENDATION__:') || buffer.includes('__PARAMETER_APPLICATION__:') || buffer.includes('__PARAMETER_SUGGESTION__:')) {
        let mainContent = buffer;
        
        // Process tool recommendation
        if (buffer.includes('__TOOL_RECOMMENDATION__:')) {
          const parts = buffer.split('__TOOL_RECOMMENDATION__:');
          mainContent = parts[0];
          const recommendationJson = parts[1];
          
          if (recommendationJson) {
            try {
              const recommendationData = JSON.parse(recommendationJson);
              if (recommendationData.type === 'tool_recommendation') {
                const newSuggestion = {
                  tool: recommendationData.recommendation,
                  confidence: recommendationData.recommendation.confidence,
                  reasoning: recommendationData.recommendation.reasoning,
                  alternative_tools: recommendationData.recommendation.alternative_tools || []
                };
                toolSuggestion.value = newSuggestion;
                // 保存到localStorage
                saveToolSuggestion(newSuggestion);
              }
            } catch (e) {
              console.error('Error parsing tool recommendation:', e);
            }
          }
        }
        
        // Process parameter suggestion
        if (buffer.includes('__PARAMETER_SUGGESTION__:')) {
          const parts = buffer.split('__PARAMETER_SUGGESTION__:');
          mainContent = parts[0];
          const suggestionJson = parts[1];
          
          if (suggestionJson) {
            try {
              const suggestionData = JSON.parse(suggestionJson);
              if (suggestionData.type === 'parameter_suggestion') {
                // 确保对象是纯JavaScript对象，避免响应式包装导致序列化问题
                parameterSuggestion.value = JSON.parse(JSON.stringify({
                  tool_name: suggestionData.tool_name,
                  suggested_parameters: suggestionData.suggested_parameters,
                  summary: suggestionData.summary,
                  timestamp: suggestionData.timestamp
                }));
              }
            } catch (e) {
              console.error('Error parsing parameter suggestion:', e);
            }
          }
        }
        
        // Process parameter application
        if (buffer.includes('__PARAMETER_APPLICATION__:')) {
          const parts = buffer.split('__PARAMETER_APPLICATION__:');
          mainContent = parts[0];
          const parameterJson = parts[1];
          
          if (parameterJson) {
            try {
              const parameterData = JSON.parse(parameterJson);
              if (parameterData.type === 'parameter_application') {
                // Send parameter application to tool page
                window.postMessage({
                  type: 'PARAMETER_APPLICATION',
                  tool_name: parameterData.tool_name,
                  parameters: parameterData.parameters,
                  summary: parameterData.summary
                }, '*');
              }
            } catch (e) {
              console.error('Error parsing parameter application:', e);
            }
          }
        }
        
        // Update the streaming message with main content
        if (messages.value.length > 0) {
          const lastMessage = messages.value[messages.value.length - 1];
          if (lastMessage.streaming) {
            lastMessage.data = mainContent;
          }
        }
      } else {
        // Update the streaming message normally
        if (messages.value.length > 0) {
          const lastMessage = messages.value[messages.value.length - 1];
          if (lastMessage.streaming) {
            lastMessage.data = buffer;
          }
        }
      }
      
      scrollToBottom();
    }
    
    // Finalize the message
    if (messages.value.length > 0) {
      const lastMessage = messages.value[messages.value.length - 1];
      if (lastMessage.streaming) {
        lastMessage.streaming = false;
        // Remove tool recommendation marker from final message if present
        if (lastMessage.data.includes('__TOOL_RECOMMENDATION__:')) {
          lastMessage.data = lastMessage.data.split('__TOOL_RECOMMENDATION__:')[0];
        }
      }
    }
    
  } catch (error) {
    console.error('Error sending message:', error);
    messages.value.push({
      sender: 'bot',
      data: `Failed to send message: ${error.message}`,
      timestamp: Date.now() / 1000,
      isError: true
    });
  } finally {
    isTyping.value = false;
    scrollToBottom();
  }
};

const handleKeyDown = (event) => {
  if (event.ctrlKey && event.key === 'Enter') {
    event.preventDefault();
    sendMessage();
  } else if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
};

const clearConversation = () => {
  if (confirm('Are you sure you want to clear the conversation?')) {
    messages.value = [];
    currentStreamMessage.value = '';
    // 工具推荐保持不变，不清除
    // Session is managed on the backend, just clear local state
  }
};

const navigateToTool = (toolName) => {
  isOpen.value = false;
  
  const currentRoute = router.currentRoute.value;
  let workspaceId = currentRoute.params.id;
  
  if (!workspaceId) {
    const recentWorkspace = localStorage.getItem('recentWorkspace');
    if (recentWorkspace) {
      workspaceId = recentWorkspace;
    } else {
      router.push('/projects');
      return;
    }
  }
  
  router.push({
    name: 'PipelineTool',
    params: {
      id: workspaceId,
      tool: toolName.toLowerCase()
    }
  });
  
  localStorage.setItem('recentWorkspace', workspaceId);
  toolSuggestion.value = null;
};

// 参数填充相关函数已移除

const getCurrentPageContext = () => {
  const currentRoute = router.currentRoute.value;
  const context = {
    route: currentRoute.path,
    params: currentRoute.params,
    query: currentRoute.query
  };
  
  if (currentRoute.name === 'PipelineTool') {
    const toolName = currentRoute.params.tool;
    const workspaceId = currentRoute.params.id;
    const toolInfo = toolManager.getToolByName(toolName);
    
    context.toolPage = {
      toolName: toolName,
      workspaceId: workspaceId,
      toolInfo: toolInfo,
      currentParameters: toolManager.currentParameters || {},
      needsParameters: true
    };
    
    requestCurrentToolParameters();
  }
  
  return context;
};

const requestCurrentToolParameters = () => {
  const currentRoute = router.currentRoute.value;
  
  if (currentRoute.name === 'PipelineTool') {
    const toolName = currentRoute.params.tool;
    
    window.parent.postMessage({
      type: 'REQUEST_CURRENT_PARAMETERS',
      toolName: toolName,
      source: 'chatbot'
    }, '*');
  }
};

const handleHeaderMouseDown = (e) => {
  if (isMobile.value || isFullscreen.value || e.target.closest('.control-btn')) {
    return;
  }
  
  isDragging.value = true;
  dragOffset.value = { 
    x: e.clientX - windowPosition.value.x, 
    y: e.clientY - windowPosition.value.y 
  };
  
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
};

const handleMouseMove = (e) => {
  if (isDragging.value) {
    windowPosition.value = {
      x: Math.max(0, Math.min(e.clientX - dragOffset.value.x, window.innerWidth - windowSize.value.width)),
      y: Math.max(0, Math.min(e.clientY - dragOffset.value.y, window.innerHeight - windowSize.value.height))
    };
  }
  
  if (isResizing.value) {
    handleResizeDrag(e);
  }
};

const handleMouseUp = () => {
  isDragging.value = false;
  isResizing.value = false;
  resizeDirection.value = '';
  document.removeEventListener('mousemove', handleMouseMove);
  document.removeEventListener('mouseup', handleMouseUp);
};

const startResize = (direction, event) => {
  event.preventDefault();
  event.stopPropagation();
  
  isResizing.value = true;
  resizeDirection.value = direction;
  resizeStartPos.value = { x: event.clientX, y: event.clientY };
  resizeStartSize.value = { ...windowSize.value };
  resizeStartWindowPos.value = { ...windowPosition.value };
  
  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
};

const handleResizeDrag = (e) => {
  const deltaX = e.clientX - resizeStartPos.value.x;
  const deltaY = e.clientY - resizeStartPos.value.y;
  
  let newWidth = resizeStartSize.value.width;
  let newHeight = resizeStartSize.value.height;
  let newX = resizeStartWindowPos.value.x;
  let newY = resizeStartWindowPos.value.y;
  
  const minWidth = 400;
  const minHeight = 300;
  const maxWidth = window.innerWidth - 20;
  const maxHeight = window.innerHeight - 20;
  
  if (resizeDirection.value.includes('e')) {
    newWidth = Math.max(minWidth, Math.min(maxWidth, resizeStartSize.value.width + deltaX));
  }
  if (resizeDirection.value.includes('w')) {
    newWidth = Math.max(minWidth, Math.min(maxWidth, resizeStartSize.value.width - deltaX));
    newX = resizeStartWindowPos.value.x + (resizeStartSize.value.width - newWidth);
  }
  if (resizeDirection.value.includes('s')) {
    newHeight = Math.max(minHeight, Math.min(maxHeight, resizeStartSize.value.height + deltaY));
  }
  if (resizeDirection.value.includes('n')) {
    newHeight = Math.max(minHeight, Math.min(maxHeight, resizeStartSize.value.height - deltaY));
    newY = resizeStartWindowPos.value.y + (resizeStartSize.value.height - newHeight);
  }
  
  if (newX < 0) {
    newWidth += newX;
    newX = 0;
  }
  if (newY < 0) {
    newHeight += newY;
    newY = 0;
  }
  if (newX + newWidth > window.innerWidth) {
    newWidth = window.innerWidth - newX;
  }
  if (newY + newHeight > window.innerHeight) {
    newHeight = window.innerHeight - newY;
  }
  
  windowSize.value = { width: newWidth, height: newHeight };
  windowPosition.value = { x: newX, y: newY };
};

const handleWindowResize = () => {
  const wasMobile = isMobile.value;
  isMobile.value = detectMobile();
  
  if (!wasMobile && isMobile.value && isOpen.value) {
    isFullscreen.value = true;
  }
  
  if (!isMobile.value && !isFullscreen.value) {
    windowPosition.value = {
      x: Math.max(0, Math.min(windowPosition.value.x, window.innerWidth - windowSize.value.width)),
      y: Math.max(0, Math.min(windowPosition.value.y, window.innerHeight - windowSize.value.height))
    };
  }
};

const handleParameterResponse = (event) => {
  if (event.data.type === 'CURRENT_PARAMETERS_RESPONSE') {
    const { toolName, parameters, toolInfo } = event.data;
    
    toolManager.currentParameters = parameters;
    toolManager.currentToolInfo = toolInfo;
    
    console.log('Received current parameter state:', { toolName, parameters, toolInfo });
  }
};

// Socket events - REMOVED, now using HTTP streaming
// socket.on('connect', () => {
//   connectionStatus.value = 'connected';
// });

// socket.on('disconnect', () => {
//   connectionStatus.value = 'disconnected';
// });

// socket.on('connect_error', () => {
//   connectionStatus.value = 'error';
// });

// socket.on('chat_response', (data) => {
//   switch (data.type) {
//     case 'message':
//       messages.value.push({
//         sender: 'bot',
//         data: data.data,
//         timestamp: data.timestamp,
//         tool_info: data.tool_info
//       });
//       break;
      
//     case 'stream_start':
//       isTyping.value = true;
//       currentStreamMessage.value = '';
//       messages.value.push({
//         sender: 'bot',
//         data: '',
//         timestamp: data.timestamp,
//         streaming: true
//       });
//       break;
      
//     case 'stream_chunk':
//       currentStreamMessage.value += data.data;
//       if (messages.value.length > 0) {
//         const lastMessage = messages.value[messages.value.length - 1];
//         if (lastMessage.streaming) {
//           lastMessage.data = currentStreamMessage.value;
//         }
//       }
//       break;
      
//     case 'stream_end':
//       isTyping.value = false;
//       currentStreamMessage.value = '';
//       if (messages.value.length > 0) {
//         const lastMessage = messages.value[messages.value.length - 1];
//         if (lastMessage.streaming) {
//           lastMessage.data = data.full_response;
//           lastMessage.streaming = false;
//         }
//       }
//       break;
      
//     case 'error':
//       isTyping.value = false;
//       messages.value.push({
//         sender: 'bot',
//         data: data.data,
//         timestamp: data.timestamp,
//         isError: true
//       });
//       break;
//   }
  
//   scrollToBottom();
// });

// socket.on('tool_suggestion', (data) => {
//   toolSuggestion.value = data;
  
//   if (messages.value.length > 0) {
//     const lastMessage = messages.value[messages.value.length - 1];
//     if (lastMessage.sender === 'bot') {
//       lastMessage.tool_info = data.tool;
//     }
//   }
  
//   scrollToBottom();
// });

// socket.on('autofill_params', (data) => {
//   console.log('Tool configured:', data);
// });

// socket.on('parameter_fill_suggestion', (data) => {
//   parameterSuggestion.value = data;
//   isParameterFillPending.value = false;
//   scrollToBottom();
// });

// socket.on('parameter_fill_error', (data) => {
//   isParameterFillPending.value = false;
//   messages.value.push({
//     sender: 'bot',
//     data: `参数填充失败: ${data.error}`,
//     timestamp: Date.now(),
//     isError: true
//   });
//   scrollToBottom();
// });

// socket.on('parameter_suggestions', (data) => {
//   messages.value.push({
//     sender: 'bot',
//     data: `已为 ${data.tool_name} 生成参数建议。${data.summary}`,
//     timestamp: data.timestamp,
//     parameterData: data
//   });
//   scrollToBottom();
// });

// Lifecycle
onMounted(() => {
  connectionStatus.value = 'connected'; // Always connected with HTTP
  isMobile.value = detectMobile();
  window.addEventListener('resize', handleWindowResize);
  
  // 加载保存的工具推荐
  loadToolSuggestion();
  
  // 监听来自工具页面的消息
  window.addEventListener('message', handleToolContextMessage);
  
  // Test connection with a simple health check
  fetch('/api/chatbot/health')
    .then(response => {
      if (response.ok) {
        connectionStatus.value = 'connected';
      } else {
        connectionStatus.value = 'error';
      }
    })
    .catch(() => {
      connectionStatus.value = 'error';
    });
});

// 监听项目ID变化，切换项目时加载对应的工具推荐
watch(currentProjectId, (newProjectId, oldProjectId) => {
  if (newProjectId !== oldProjectId) {
    loadToolSuggestion();
  }
});

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize);
});
</script>

<style scoped>
/* Floating Trigger Button */
.chatbot-trigger {
  position: fixed;
  bottom: 24px;
  right: 88px;
  z-index: 1000;
}

.chat-button {
  background: var(--surface-1);
  border: var(--border-width) solid rgba(var(--accent-rgb), 0.25);
  border-radius: 50%;
  width: 48px;
  height: 48px;
  color: var(--primary-600);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.chat-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  background: var(--surface-2);
}

.chat-button .status-dot {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--surface-1);
}

.chat-button .status-dot.connected {
  background: var(--success-500);
}

.chat-button .status-dot.connecting {
  background: var(--warning-500);
  animation: pulse 2s infinite;
}

.chat-button .status-dot.disconnected,
.chat-button .status-dot.error {
  background: var(--error-500);
}

/* Chat Window */
.chatbot-window {
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: var(--border-width) solid var(--border-color-light);
  animation: scaleIn 0.2s ease-out;
}

/* Header */
.chat-header {
  background: linear-gradient(180deg, rgba(var(--accent-rgb), 0.12) 0%, rgba(255, 255, 255, 0.96) 85%);
  color: var(--gray-900);
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: var(--border-width) solid var(--border-color-light);
  cursor: move;
  user-select: none;
}

.header-info h3 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: var(--font-semibold);
  font-family: var(--font-family-display);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--gray-600);
}

.status-indicator .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-indicator.connected .status-dot {
  background: var(--success-500);
}

.status-indicator.connecting .status-dot {
  background: var(--warning-500);
  animation: pulse 2s infinite;
}

.status-indicator.disconnected .status-dot,
.status-indicator.error .status-dot {
  background: var(--error-500);
}

.project-info {
  font-size: 11px;
  margin-top: 2px;
  color: var(--gray-600);
}

.project-id {
  color: var(--primary-700);
  background: rgba(var(--accent-rgb), 0.12);
  border: var(--border-width) solid rgba(var(--accent-rgb), 0.24);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-family-mono);
}

.no-project {
  color: var(--warning-600);
  font-weight: var(--font-medium);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.control-btn {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color-light);
  color: var(--gray-600);
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-xs);
}

.control-btn:hover {
  background: var(--surface-2);
  color: var(--gray-800);
  border-color: var(--border-color);
  transform: translateY(-1px);
}

.close-btn:hover {
  background: var(--error-50);
  border-color: rgba(239, 68, 68, 0.25);
  color: var(--error-600);
}

/* Message Area */
.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background: linear-gradient(180deg, var(--surface-2) 0%, var(--surface-0) 100%);
}

.chat-messages::-webkit-scrollbar {
  width: 4px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: var(--gray-400);
  border-radius: 2px;
}

.message-wrapper {
  display: flex;
  margin-bottom: 12px;
  animation: slideInUp 0.3s ease;
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 16px;
  line-height: 1.5;
  position: relative;
  word-wrap: break-word;
  border: var(--border-width) solid transparent;
}

.message-wrapper.bot .message-bubble {
  background: var(--surface-1);
  color: var(--gray-800);
  border-bottom-left-radius: 4px;
  border-color: var(--border-color-light);
  box-shadow: var(--shadow-xs);
}

.message-wrapper.user .message-bubble {
  background: var(--gradient-primary);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 12px 24px rgba(var(--accent-rgb), 0.2);
}

.message-content :deep(p) {
  margin: 0 0 8px 0;
}

.message-content :deep(p:last-child) {
  margin-bottom: 0;
}

.message-content :deep(code) {
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.875em;
  font-family: var(--font-family-mono);
  color: var(--gray-700);
}

.message-content :deep(pre) {
  background: var(--surface-2);
  border: var(--border-width) solid var(--border-color-light);
  border-radius: 8px;
  padding: 16px;
  margin: 12px 0;
  overflow-x: auto;
  font-family: var(--font-family-mono);
  font-size: 0.875em;
  line-height: 1.5;
}

.message-content :deep(pre code) {
  background: transparent;
  padding: 0;
  border-radius: 0;
  font-size: inherit;
}

.message-content :deep(.language-python) {
  color: var(--primary-600);
}

.message-content :deep(.language-bash) {
  color: var(--gray-800);
}

.message-content :deep(.language-r) {
  color: var(--secondary-color);
}

.message-content :deep(h1),
.message-content :deep(h2),
.message-content :deep(h3) {
  margin: 16px 0 8px 0;
  font-weight: var(--font-semibold);
}

.message-content :deep(h1) {
  font-size: 1.25em;
  border-bottom: var(--border-width) solid var(--border-color-light);
  padding-bottom: 4px;
}

.message-content :deep(h2) {
  font-size: 1.125em;
}

.message-content :deep(h3) {
  font-size: 1em;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.message-content :deep(li) {
  margin: 4px 0;
}

.message-content :deep(blockquote) {
  border-left: 4px solid var(--border-color-light);
  padding-left: 16px;
  margin: 12px 0;
  color: var(--gray-600);
  font-style: italic;
}

.message-time {
  font-size: 0.75rem;
  color: var(--gray-500);
  margin-top: 4px;
}

.message-wrapper.user .message-time {
  color: rgba(255, 255, 255, 0.75);
}

.tool-btn {
  background: var(--primary-600);
  color: white;
  border: var(--border-width) solid rgba(var(--accent-rgb), 0.25);
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  box-shadow: var(--shadow-xs);
}

.tool-btn:hover {
  transform: translateY(-1px);
  background: var(--primary-700);
  box-shadow: 0 8px 18px rgba(var(--accent-rgb), 0.25);
}

.param-btn {
  background: var(--surface-1);
  border: var(--border-width) solid rgba(var(--accent-rgb), 0.2);
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--primary-700);
  box-shadow: var(--shadow-xs);
}

.param-btn:hover {
  transform: translateY(-1px);
  background: var(--surface-2);
  box-shadow: 0 8px 18px rgba(var(--accent-rgb), 0.18);
}

/* Typing Indicator */
.typing {
  background: var(--surface-1) !important;
  box-shadow: var(--shadow-xs) !important;
}

.typing-indicator {
  display: flex;
  gap: 4px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--gray-400);
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

/* Tool Suggestion */
.tool-suggestion {
  margin: 16px 0;
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color-light);
  border-left: 4px solid rgba(var(--accent-rgb), 0.35);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  animation: slideInUp 0.3s ease-out;
}

.suggestion-header {
  background: var(--surface-2);
  color: var(--gray-900);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: var(--font-medium);
  font-size: 0.875rem;
  border-bottom: var(--border-width) solid var(--border-color-light);
}

.suggestion-header .close-btn {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color-light);
  color: var(--gray-600);
  font-size: 18px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all var(--transition-fast);
}

.suggestion-header .close-btn:hover {
  background: var(--surface-2);
  border-color: var(--border-color);
  color: var(--gray-800);
}

.suggestion-content {
  padding: 16px;
}

.suggestion-content h4 {
  margin: 0 0 8px 0;
  font-size: 1rem;
  color: var(--gray-900);
  font-weight: var(--font-semibold);
}

.suggestion-content p {
  margin: 0 0 16px 0;
  color: var(--gray-600);
  font-size: 0.875rem;
  line-height: 1.5;
}

.suggestion-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.use-btn {
  background: var(--primary-600);
  color: white;
  border: var(--border-width) solid rgba(var(--accent-rgb), 0.25);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: var(--shadow-xs);
}

.use-btn:hover {
  transform: translateY(-1px);
  background: var(--primary-700);
  box-shadow: 0 10px 20px rgba(var(--accent-rgb), 0.25);
}

.param-fill-btn {
  background: var(--surface-1);
  color: var(--primary-700);
  border: var(--border-width) solid rgba(var(--accent-rgb), 0.25);
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 4px;
  box-shadow: var(--shadow-xs);
}

.param-fill-btn:hover {
  transform: translateY(-1px);
  background: var(--surface-2);
  box-shadow: 0 10px 20px rgba(var(--accent-rgb), 0.2);
}

.dismiss-btn {
  background: var(--surface-1);
  color: var(--gray-600);
  border: var(--border-width) solid var(--border-color-light);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.dismiss-btn:hover {
  background: var(--surface-2);
  border-color: var(--border-color);
  color: var(--gray-800);
}



/* Tool Recommendation New Style */
.recommendation-reason {
  margin: 12px 0;
  padding: 12px 16px;
  background: var(--surface-2);
  border-left: 4px solid var(--primary-500);
  border-radius: 8px;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--gray-700);
}

.confidence-indicator {
  margin: 16px 0;
  font-size: 0.8rem;
  color: var(--gray-600);
}

.confidence-bar {
  width: 100%;
  height: 6px;
  background: var(--surface-3);
  border-radius: 3px;
  overflow: hidden;
  margin: 6px 0;
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.12);
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(135deg, var(--primary-500) 0%, var(--primary-700) 100%);
  transition: width 0.5s ease;
  border-radius: 3px;
  box-shadow: 0 1px 2px rgba(var(--accent-rgb), 0.3);
}

.alternative-tools {
  margin: 16px 0;
}

.alternative-tools h5 {
  margin: 0 0 8px 0;
  font-size: 0.875rem;
  color: var(--gray-700);
  font-weight: var(--font-medium);
}

.alternative-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.alternative-btn {
  background: var(--surface-2);
  color: var(--gray-700);
  border: var(--border-width) solid var(--border-color-light);
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75rem;
  transition: all var(--transition-fast);
}

.alternative-btn:hover {
  background: var(--surface-1);
  border-color: var(--border-color);
  color: var(--gray-800);
  transform: translateY(-1px);
}

/* Parameter Suggestion */
.parameter-suggestion {
  margin: 16px 0;
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color-light);
  border-left: 4px solid rgba(var(--accent-rgb), 0.35);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  animation: slideInUp 0.3s ease-out;
}

.parameter-suggestion .suggestion-header {
  background: var(--surface-2);
  color: var(--gray-900);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: var(--font-medium);
  font-size: 0.875rem;
  border-bottom: var(--border-width) solid var(--border-color-light);
}

.parameter-suggestion .suggestion-content {
  padding: 16px;
}

.parameter-suggestion .summary {
  font-size: 0.875rem;
  color: var(--gray-600);
  margin-bottom: 16px;
  font-style: italic;
}

.parameter-preview {
  margin-bottom: 16px;
}

.parameter-preview h5 {
  margin: 0 0 12px 0;
  font-size: 0.875rem;
  color: var(--gray-700);
  font-weight: var(--font-semibold);
}

.parameter-list {
  background: var(--surface-2);
  border-radius: 8px;
  padding: 12px;
  border: var(--border-width) solid var(--border-color-light);
  max-height: 200px;
  overflow-y: auto;
}

.parameter-item {
  padding: 8px 0;
  border-bottom: var(--border-width) solid var(--border-color-light);
}

.parameter-item:last-child {
  border-bottom: none;
}

.param-name, .parameter-name {
  font-weight: var(--font-semibold);
  color: var(--gray-800);
  font-size: 0.875rem;
}

.param-value, .parameter-value {
  color: var(--primary-700);
  font-family: var(--font-family-mono);
  font-size: 0.875rem;
  margin: 4px 0;
  background: var(--surface-1);
  padding: 2px 6px;
  border-radius: 4px;
  display: inline-block;
  border: var(--border-width) solid var(--border-color-light);
}

.param-reason, .parameter-reason {
  color: var(--gray-600);
  font-size: 0.75rem;
  line-height: 1.4;
}

.fill-btn {
  background: var(--primary-600);
  color: white;
  border: var(--border-width) solid rgba(var(--accent-rgb), 0.25);
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: var(--shadow-xs);
}

.fill-btn:hover {
  transform: translateY(-1px);
  background: var(--primary-700);
  box-shadow: 0 10px 20px rgba(var(--accent-rgb), 0.25);
}

.cancel-btn {
  background: var(--surface-1);
  color: var(--gray-600);
  border: var(--border-width) solid var(--border-color-light);
  padding: 10px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: var(--font-medium);
  transition: all var(--transition-fast);
}

.cancel-btn:hover {
  background: var(--surface-2);
  border-color: var(--border-color);
  color: var(--gray-800);
}

.parameter-pending {
  margin: 16px 0;
  background: var(--surface-2);
  border: var(--border-width) solid var(--border-color-light);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.pending-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--gray-600);
  font-size: 0.875rem;
}

.pending-content .spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color-light);
  border-top: 2px solid var(--primary-500);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Input Area */
.chat-input {
  padding: 16px;
  border-top: var(--border-width) solid var(--border-color-light);
  background: var(--surface-1);
}

.input-wrapper {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.input-wrapper textarea {
  flex: 1;
  border: var(--border-width) solid var(--border-color);
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 0.875rem;
  resize: none;
  outline: none;
  transition: all var(--transition-fast);
  font-family: inherit;
  line-height: 1.4;
  min-height: 20px;
  max-height: 100px;
  background: var(--surface-1);
  color: var(--gray-800);
}

.input-wrapper textarea:focus {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
}

.input-wrapper textarea:disabled {
  background: var(--surface-2);
  color: var(--gray-400);
  cursor: not-allowed;
}

.send-btn {
  background: var(--primary-600);
  color: white;
  border: none;
  padding: 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  height: 40px;
  box-shadow: var(--shadow-xs);
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  background: var(--primary-700);
  box-shadow: 0 10px 20px rgba(var(--accent-rgb), 0.25);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Resize Handles */
.resize-handles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.resize-handle {
  position: absolute;
  pointer-events: auto;
  background: transparent;
}

.resize-n {
  top: 0;
  left: 8px;
  right: 8px;
  height: 4px;
  cursor: n-resize;
}

.resize-s {
  bottom: 0;
  left: 8px;
  right: 8px;
  height: 4px;
  cursor: s-resize;
}

.resize-e {
  top: 8px;
  right: 0;
  bottom: 8px;
  width: 4px;
  cursor: e-resize;
}

.resize-w {
  top: 8px;
  left: 0;
  bottom: 8px;
  width: 4px;
  cursor: w-resize;
}

.resize-ne {
  top: 0;
  right: 0;
  width: 8px;
  height: 8px;
  cursor: ne-resize;
}

.resize-nw {
  top: 0;
  left: 0;
  width: 8px;
  height: 8px;
  cursor: nw-resize;
}

.resize-se {
  bottom: 0;
  right: 0;
  width: 8px;
  height: 8px;
  cursor: se-resize;
}

.resize-sw {
  bottom: 0;
  left: 0;
  width: 8px;
  height: 8px;
  cursor: sw-resize;
}

/* Animation Effects */
@keyframes scaleIn {
  from {
    transform: scale(0.95);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Responsive Design */
@media (max-width: 768px) {
  .chatbot-trigger {
    bottom: max(20px, env(safe-area-inset-bottom));
    right: max(48px, calc(48px + env(safe-area-inset-right)));
  }
  
  .chat-button {
    width: 44px;
    height: 44px;
  }
  
  .chat-button .status-dot {
    top: 1px;
    right: 1px;
    width: 8px;
    height: 8px;
  }
  
  .chatbot-window {
    left: 4px !important;
    right: 4px !important;
    top: 4px !important;
    bottom: 4px !important;
    width: auto !important;
    height: auto !important;
    border-radius: 0;
    box-shadow: none;
  }
  
  .chat-header {
    border-radius: 0;
    padding: 16px 20px;
    cursor: default;
  }
  
  .chat-header h3 {
    font-size: 16px;
  }
  
  .status-indicator {
    font-size: 14px;
  }
  
  .chat-input {
    border-radius: 0;
    padding-bottom: env(safe-area-inset-bottom, 16px);
  }
  
  .chatbot-window {
    padding-bottom: env(safe-area-inset-bottom);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
}

@media (max-width: 480px) {
  .chatbot-trigger {
    bottom: max(20px, env(safe-area-inset-bottom));
    right: max(20px, calc(20px + env(safe-area-inset-right)));
  }
  
  .chat-button {
    width: 48px;
    height: 48px;
  }
}
</style> 
