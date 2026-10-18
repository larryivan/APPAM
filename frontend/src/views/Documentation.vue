<template>
  <div class="documentation-container">
    <div class="doc-layout">
      <nav class="doc-sidebar" :class="{ 'sidebar-hidden': !sidebarExpanded }">
        <button
          type="button"
          class="nav-toggle"
          :title="sidebarExpanded ? 'Collapse contents' : 'Expand contents'"
          :aria-label="sidebarExpanded ? 'Collapse contents' : 'Expand contents'"
          :aria-expanded="sidebarExpanded"
          @click="toggleSidebar"
        >
          <Icon :name="sidebarExpanded ? 'panel-left-close' : 'panel-left-open'" :size="18" />
        </button>
        <div class="nav-content">
          <div class="nav-header">
            <span>Contents</span>
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
             <h3><Icon name="triangle-alert" :size="18" /> Loading Failed</h3>
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
import DOMPurify from 'dompurify';

const htmlContent = ref('');
const loading = ref(true);
const error = ref('');
const sidebarExpanded = ref(true);
const tocItems = ref([]);
const activeSection = ref('');

const toggleSidebar = () => {
  sidebarExpanded.value = !sidebarExpanded.value;
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
    
    htmlContent.value = DOMPurify.sanitize(html, { USE_PROFILES: { html: true } });
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
  background: var(--surface-0);
}

.doc-layout {
  width: 100%;
  height: 100%;
  display: flex;
  overflow: hidden;
}

.doc-sidebar {
  width: 240px;
  flex: 0 0 240px;
  display: flex;
  flex-direction: column;
  background: var(--surface-1);
  border-right: 1px solid var(--border-color-light);
  transition: width var(--transition-base), flex-basis var(--transition-base);
  overflow: hidden;
}

.nav-toggle {
  min-height: 32px;
  padding: 0;
  width: 32px;
  height: 32px;
  margin: 10px 12px;
  background: var(--surface-1);
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--gray-600);
  border: 1px solid var(--border-color);
  transition: background var(--transition-fast), color var(--transition-fast);
}

.nav-toggle:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.nav-content {
  min-width: 240px;
  flex: 1;
  overflow-y: auto;
}

.doc-sidebar.sidebar-hidden {
  width: 56px;
  flex-basis: 56px;
}

.doc-sidebar.sidebar-hidden .nav-content {
  display: none;
}

.nav-header {
  min-height: 38px;
  padding: 0 12px 0 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-500);
  letter-spacing: 0;
  border-bottom: 1px solid var(--border-color-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  color: var(--gray-600);
  text-decoration: none;
  display: block;
  padding: 8px 12px;
  border-radius: 6px;
  transition: background var(--transition-fast), color var(--transition-fast);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
}

.nav-link:hover {
  background-color: var(--surface-2);
  color: var(--gray-900);
}

.nav-link.active {
  background-color: var(--primary-50);
  color: var(--primary-700);
}

/* TOC层级样式 */
.nav-link.level-2 {
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-600);
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.nav-link.level-2:hover {
  background-color: var(--surface-2);
  color: var(--gray-900);
}

.nav-link.level-2.active {
  background-color: var(--primary-50);
  color: var(--primary-700);
}


/* 主内容区样式 */
.doc-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  background: var(--surface-1);
  scroll-behavior: smooth;
}

.content-article {
  padding: 36px 40px 72px;
  max-width: 920px;
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
  color: var(--gray-500);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color-light);
  border-top: 3px solid var(--primary-500);
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
  color: var(--error-600);
}

.retry-btn {
  margin-top: 16px;
  padding: 8px 20px;
  background: var(--primary-600);
  color: white;
  border: none;
  border-radius: var(--radius-base);
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
    position: absolute;
    inset: 0 auto 0 0;
    z-index: 20;
    box-shadow: var(--shadow-md);
  }
  
  .nav-toggle {
    width: 32px;
    height: 32px;
  }
  
  .content-article {
    padding: 28px 20px 56px 76px;
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
  .nav-link {
    padding: 6px 10px;
    font-size: 13px;
  }
  
  .content-article {
    padding: 24px 16px 48px 72px;
  }
}

.markdown-content {
  line-height: 1.7;
  font-size: 15px;
  color: var(--gray-700);
}

.markdown-content :deep(h1) {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 32px 0;
  color: var(--gray-900);
  border-bottom: 1px solid var(--border-color-light);
  padding-bottom: 14px;
  scroll-margin-top: 20px;
}

.markdown-content :deep(h2) {
  font-size: 22px;
  font-weight: 600;
  margin: 48px 0 24px 0;
  color: var(--gray-900);
  scroll-margin-top: 20px;
  position: relative;
}

.markdown-content :deep(h3) {
  font-size: 18px;
  font-weight: 600;
  margin: 32px 0 16px 0;
  color: var(--gray-800);
  scroll-margin-top: 20px;
}

.markdown-content :deep(p) {
  margin-bottom: 20px;
  color: var(--gray-600);
  line-height: 1.75;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin-bottom: 20px;
  padding-left: 28px;
}

.markdown-content :deep(li) {
  margin-bottom: 8px;
  color: var(--gray-600);
  line-height: 1.6;
}

.markdown-content :deep(li):last-child {
  margin-bottom: 0;
}

.markdown-content :deep(strong) {
  font-weight: 600;
  color: var(--gray-800);
}

.markdown-content :deep(em) {
  font-style: italic;
  color: var(--gray-500);
}

.markdown-content :deep(code) {
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-family-mono);
  font-size: 0.875em;
  color: var(--primary-700);
  border: 1px solid var(--border-color-light);
}

.markdown-content :deep(pre) {
  background: var(--dark-bg);
  color: var(--text-light);
  padding: 20px 24px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 24px 0;
  border: 1px solid var(--dark-border);
}

.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
  border: none;
  color: inherit;
  font-size: var(--text-sm);
  line-height: 1.5;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid var(--primary-500);
  padding: 16px 20px;
  margin: 24px 0;
  background: var(--surface-2);
  border-radius: 0 6px 6px 0;
  font-style: italic;
  color: var(--gray-600);
}

.markdown-content :deep(blockquote p) {
  margin-bottom: 0;
}

.markdown-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 24px 0;
  border: 1px solid var(--border-color-light);
  border-radius: 8px;
  overflow: hidden;
}

.markdown-content :deep(th),
.markdown-content :deep(td) {
  border: 1px solid var(--border-color-light);
  padding: 12px 16px;
  text-align: left;
}

.markdown-content :deep(th) {
  background: var(--surface-2);
  font-weight: 600;
  color: var(--gray-700);
}

.markdown-content :deep(td) {
  color: var(--gray-600);
}

.markdown-content :deep(hr) {
  border: none;
  height: 1px;
  background: var(--border-color-light);
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
  color: var(--gray-500);
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
