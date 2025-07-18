<template>
  <div class="documentation-container">
    <div class="doc-layout">
      <!-- 浮动侧边导航 -->
      <nav class="doc-sidebar" :class="{ 'sidebar-hidden': !sidebarExpanded }">
        <div class="nav-toggle" @click="toggleSidebar">
          <span class="nav-icon">{{ sidebarExpanded ? '✕' : '📑' }}</span>
        </div>
        <div class="nav-content">
          <div class="nav-header">
            <span>Contents</span>
            <button class="close-btn" @click="closeSidebar" title="关闭目录">
              <span>✕</span>
            </button>
          </div>
          <ul class="nav-list">
            <li v-for="tocItem in tocItems" :key="tocItem.id">
              <a 
                :href="`#${tocItem.id}`" 
                class="nav-link"
                :class="{ 
                  'active': activeSection === tocItem.id,
                  [`level-${tocItem.level}`]: true
                }"
                @click="scrollToSection(tocItem.id)"
              >
                {{ tocItem.text }}
              </a>
            </li>
          </ul>
        </div>
      </nav>
      
      <!-- 主内容区 -->
      <main class="doc-main">
         <div class="content-article">
           <div v-if="loading" class="loading-state">
             <div class="loading-spinner"></div>
             <p>Loading documentation...</p>
           </div>
           <div v-else-if="error" class="error-state">
             <h3>⚠️ Loading Failed</h3>
             <p>{{ error }}</p>
             <button @click="loadMarkdown" class="retry-btn">Retry</button>
           </div>
           <div v-else class="markdown-content" v-html="htmlContent"></div>
         </div>
       </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted, computed } from 'vue';
import { marked } from 'marked';

const htmlContent = ref('');
const loading = ref(true);
const error = ref('');
const sidebarExpanded = ref(true); // 默认展开，保持常驻
const tocItems = ref([]);
const activeSection = ref('');

// 切换侧边栏展开状态
const toggleSidebar = () => {
  sidebarExpanded.value = !sidebarExpanded.value;
};

// 关闭侧边栏
const closeSidebar = () => {
  sidebarExpanded.value = false;
};

// 从markdown内容中提取TOC
const extractTOC = (markdown) => {
  const lines = markdown.split('\n');
  const toc = [];
  
  lines.forEach(line => {
    // 只匹配二级标题 (##)
    const headerMatch = line.match(/^(##)\s+(.+)$/);
    if (headerMatch) {
      const level = headerMatch[1].length;
      const text = headerMatch[2].trim();
      const id = generateId(text);
      
      toc.push({
        id,
        text,
        level,
        originalText: text
      });
    }
  });
  
  return toc;
};

// 生成标题ID
const generateId = (text) => {
  return text
    .toLowerCase()
    .replace(/[^\w\s\u4e00-\u9fff-]/g, '') // 保留中文、英文、数字、空格、连字符
    .replace(/\s+/g, '-') // 空格替换为连字符
    .replace(/-+/g, '-') // 多个连字符替换为单个
    .replace(/^-|-$/g, '') // 移除首尾连字符
    .trim();
};

// 为HTML内容添加ID
const addIdsToHTML = (html, tocItems) => {
  let modifiedHtml = html;
  
  tocItems.forEach(item => {
    const escapedText = item.originalText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`<h${item.level}>${escapedText}</h${item.level}>`, 'g');
    modifiedHtml = modifiedHtml.replace(regex, `<h${item.level} id="${item.id}">${item.originalText}</h${item.level}>`);
  });
  
  return modifiedHtml;
};

const loadMarkdown = async () => {
  try {
    const response = await fetch('/docs/documentation.md');
    if (!response.ok) {
      throw new Error('Unable to load documentation file');
    }
    let markdown = await response.text();
    
    // 提取TOC
    const extractedTOC = extractTOC(markdown);
    tocItems.value = extractedTOC;
    
    console.log('Extracted TOC:', extractedTOC);
    
    // 配置marked选项
    marked.setOptions({
      headerIds: true,
      mangle: false,
      gfm: true,
      breaks: true
    });
    
    // 转换为HTML
    let html = marked(markdown);
    
    // 为标题添加ID（如果marked没有自动添加）
    html = addIdsToHTML(html, extractedTOC);
    
    htmlContent.value = html;
    loading.value = false;
    
    // 等待DOM更新后设置滚动行为
    await nextTick();
    setupSmoothScrolling();
  } catch (err) {
    error.value = err.message;
    loading.value = false;
    console.error('Error loading markdown:', err);
  }
};

// 滚动到指定章节
const scrollToSection = (sectionId) => {
  const targetElement = document.getElementById(sectionId);
  if (targetElement) {
    targetElement.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
    // 更新URL但不触发路由
    window.history.replaceState(null, '', `#${sectionId}`);
    updateActiveNavLink(sectionId);
    // 点击后不收起导航，保持常驻
  }
};

// 设置平滑滚动
const setupSmoothScrolling = () => {
  const navLinks = document.querySelectorAll('.nav-link[href^="#"]');
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = link.getAttribute('href').substring(1);
      scrollToSection(targetId);
    });
  });
  
  // 设置滚动监听
  setupScrollSpy();
};

// 滚动监听，高亮当前章节
const setupScrollSpy = () => {
  const headings = document.querySelectorAll('.markdown-content h2[id]');
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        updateActiveNavLink(entry.target.id);
      }
    });
  }, {
    rootMargin: '-100px 0px -50% 0px',
    threshold: 0
  });
  
  headings.forEach(heading => observer.observe(heading));
};

// 更新导航高亮
const updateActiveNavLink = (activeId) => {
  activeSection.value = activeId;
  const navLinks = document.querySelectorAll('.nav-link');
  navLinks.forEach(link => {
    link.classList.remove('active');
    if (link.getAttribute('href') === `#${activeId}`) {
      link.classList.add('active');
    }
  });
};

// 页面加载时检查hash并滚动到对应位置
const scrollToHash = () => {
  if (window.location.hash) {
    const targetId = window.location.hash.substring(1);
    const targetElement = document.getElementById(targetId);
    if (targetElement) {
      setTimeout(() => {
        targetElement.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
        updateActiveNavLink(targetId);
      }, 300);
    }
  }
};

// 点击外部区域不关闭导航，保持常驻

onMounted(() => {
  loadMarkdown().then(() => {
    nextTick(() => {
      scrollToHash();
    });
  });
});

// 组件卸载时清理事件监听器
onUnmounted(() => {
  // 清理其他事件监听器（如果有的话）
});
</script>

<style scoped>
.documentation-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.doc-layout {
  width: 100%;
  height: 100%;
  position: relative;
  overflow-y: auto;
  scroll-behavior: smooth;
}

/* 浮动侧边栏样式 */
.doc-sidebar {
  position: fixed;
  top: 50%;
  left: 20px;
  transform: translateY(-50%);
  z-index: 1000;
  display: flex;
  align-items: center;
}

.nav-toggle {
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.nav-toggle:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 25px rgba(0, 0, 0, 0.15);
}

.nav-icon {
  font-size: 18px;
  transition: transform 0.3s ease;
}

.nav-content {
  position: absolute;
  left: 60px;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  min-width: 160px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(0, 0, 0, 0.05);
  opacity: 1;
  visibility: visible;
  transform: translateY(-50%) translateX(0);
  transition: all 0.3s ease;
}

/* 侧边栏隐藏状态 */
.doc-sidebar.sidebar-hidden .nav-content {
  opacity: 0;
  visibility: hidden;
  transform: translateY(-50%) translateX(-10px);
}

.nav-header {
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.close-btn {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  font-size: 14px;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  background-color: #f1f5f9;
  color: #ef4444;
  transform: scale(1.1);
}

.nav-list {
  list-style: none;
  padding: 8px;
  margin: 0;
}

.nav-list li {
  margin-bottom: 2px;
}

.nav-list li:last-child {
  margin-bottom: 0;
}

.nav-link {
  color: #475569;
  text-decoration: none;
  display: block;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
  font-size: 14px;
  font-weight: 500;
  line-height: 1.2;
}

.nav-link:hover {
  background-color: #f1f5f9;
  color: #1e293b;
  transform: translateX(2px);
}

.nav-link.active {
  background-color: #3b82f6;
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

/* TOC层级样式 */
.nav-link.level-2 {
  font-size: 14px;
  font-weight: 500;
  color: #475569;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.nav-link.level-2:hover {
  background-color: #f1f5f9;
  color: #1e293b;
  transform: translateX(2px);
}

.nav-link.level-2.active {
  background-color: #3b82f6;
  color: white;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}


/* 主内容区样式 */
.doc-main {
  width: 100%;
  overflow-y: auto;
  background: white;
}

.content-article {
  padding: 40px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
}

/* 加载和错误状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #64748b;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #e2e8f0;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  text-align: center;
  padding: 60px;
  color: #ef4444;
}

.retry-btn {
  margin-top: 16px;
  padding: 8px 20px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}



/* 响应式设计 */
@media (max-width: 1024px) {
  .content-article {
    padding: 32px;
    max-width: 800px;
  }
}

@media (max-width: 768px) {
  .doc-sidebar {
    left: 16px;
  }
  
  .nav-toggle {
    width: 44px;
    height: 44px;
  }
  
  .nav-content {
    left: 56px;
    min-width: 140px;
  }
  
  .content-article {
    padding: 24px 20px;
  }
  
  .markdown-content {
    font-size: 15px;
  }
  
  .markdown-content :deep(h1) {
    font-size: 1.875rem;
    margin-bottom: 24px;
  }
  
  .markdown-content :deep(h2) {
    font-size: 1.5rem;
    margin: 32px 0 20px 0;
  }
  
  .markdown-content :deep(h2):before {
    left: -16px;
    width: 3px;
    height: 20px;
  }
  
  .markdown-content :deep(h3) {
    font-size: 1.25rem;
    margin: 24px 0 12px 0;
  }
}

@media (max-width: 480px) {
  .doc-sidebar {
    left: 12px;
  }
  
  .nav-toggle {
    width: 40px;
    height: 40px;
  }
  
  .nav-icon {
    font-size: 16px;
  }
  
  .nav-content {
    left: 48px;
    min-width: 120px;
  }
  
  .nav-link {
    padding: 6px 10px;
    font-size: 13px;
  }
  
  .content-article {
    padding: 20px 16px;
  }
}

.markdown-content {
  line-height: 1.7;
  font-size: 16px;
  color: #374151;
}

.markdown-content :deep(h1) {
  font-size: 2.25rem;
  font-weight: 700;
  margin: 0 0 32px 0;
  color: #111827;
  border-bottom: 3px solid #e5e7eb;
  padding-bottom: 16px;
  scroll-margin-top: 20px;
}

.markdown-content :deep(h2) {
  font-size: 1.75rem;
  font-weight: 600;
  margin: 48px 0 24px 0;
  color: #1f2937;
  scroll-margin-top: 20px;
  position: relative;
}

.markdown-content :deep(h2):before {
  content: '';
  position: absolute;
  left: -24px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 24px;
  background: #3b82f6;
  border-radius: 2px;
}

.markdown-content :deep(h3) {
  font-size: 1.375rem;
  font-weight: 600;
  margin: 32px 0 16px 0;
  color: #374151;
  scroll-margin-top: 20px;
}

.markdown-content :deep(p) {
  margin-bottom: 20px;
  color: #4b5563;
  line-height: 1.75;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 20px;
  padding-left: 28px;
}

.markdown-content :deep(li) {
  margin-bottom: 8px;
  color: #4b5563;
  line-height: 1.6;
}

.markdown-content :deep(li):last-child {
  margin-bottom: 0;
}

.markdown-content :deep(strong) {
  font-weight: 600;
  color: #1f2937;
}

.markdown-content :deep(em) {
  font-style: italic;
  color: #6b7280;
}

.markdown-content :deep(code) {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 0.875em;
  color: #e11d48;
  border: 1px solid #e2e8f0;
}

.markdown-content :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 20px 24px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 24px 0;
  border: 1px solid #334155;
}

.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
  border: none;
  color: inherit;
  font-size: 0.875rem;
  line-height: 1.5;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid #3b82f6;
  padding: 16px 20px;
  margin: 24px 0;
  background: #f8fafc;
  border-radius: 0 6px 6px 0;
  font-style: italic;
  color: #475569;
}

.markdown-content :deep(blockquote p) {
  margin-bottom: 0;
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 24px 0;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 12px 16px;
  text-align: left;
}

.markdown-content :deep(th) {
  background: #f9fafb;
  font-weight: 600;
  color: #374151;
}

.markdown-content :deep(td) {
  color: #4b5563;
}

.markdown-content :deep(hr) {
  border: none;
  height: 1px;
  background: linear-gradient(to right, transparent, #e5e7eb, transparent);
  margin: 32px 0;
}

/* 为标题添加锚点样式 */
.markdown-content :deep(h1):hover,
.markdown-content :deep(h2):hover,
.markdown-content :deep(h3):hover {
  cursor: pointer;
}

/* 添加一些视觉层次 */
.markdown-content :deep(h1) + p,
.markdown-content :deep(h2) + p,
.markdown-content :deep(h3) + p {
  color: #6b7280;
  font-size: 1.05em;
}

/* 添加打印样式 */
@media print {
  .doc-sidebar {
    display: none;
  }
  
  .doc-main {
    width: 100%;
  }
  
  .content-article {
    padding: 0;
    max-width: none;
  }
  
  .markdown-content {
    font-size: 12pt;
    line-height: 1.5;
  }
  
  .markdown-content :deep(h1),
  .markdown-content :deep(h2),
  .markdown-content :deep(h3) {
    break-after: avoid;
  }
  
  .markdown-content :deep(pre) {
    background: #f5f5f5 !important;
    color: #000 !important;
    border: 1px solid #ccc;
  }
}
</style> 