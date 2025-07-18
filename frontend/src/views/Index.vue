<template>
  <div class="index-container">
    <div class="index-content">
      <div class="hero-section">
        <div class="hero-content">
          <h1>欢迎使用 APPAM</h1>
          <p class="hero-subtitle">一个强大的项目管理和分析平台</p>
          <div class="hero-buttons">
            <router-link to="/projects" class="btn btn-primary">
              查看项目
            </router-link>
            <router-link to="/documentation" class="btn btn-secondary">
              查看文档
            </router-link>
          </div>
        </div>
      </div>
      
      <div class="features-section">
        <h2>主要功能</h2>
        <div class="features-grid">
          <div class="feature-card">
            <div class="feature-icon">📊</div>
            <h3>项目管理</h3>
            <p>创建、管理和跟踪您的项目进度</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">🛠️</div>
            <h3>流水线工具</h3>
            <p>使用强大的流水线工具进行数据处理</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">💬</div>
            <h3>智能聊天</h3>
            <p>与AI助手交流，获得即时帮助</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">🌐</div>
            <h3>网络驱动</h3>
            <p>强大的网络爬虫和数据收集工具</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// No script needed for this static page
</script>

<style scoped>
.index-container {
  height: 100%;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.index-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-4);
}

.hero-section {
  text-align: center;
  padding: var(--spacing-16) 0;
  background: var(--gradient-primary);
  border-radius: var(--radius-xl);
  margin-bottom: var(--spacing-16);
  color: white;
  box-shadow: var(--shadow-lg);
}

.hero-content {
  max-width: 600px;
  margin: 0 auto;
}

.hero-content h1 {
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  margin-bottom: var(--spacing-5);
  text-shadow: var(--shadow-sm);
  line-height: var(--leading-tight);
}

.hero-subtitle {
  font-size: var(--text-xl);
  margin-bottom: var(--spacing-10);
  opacity: 0.9;
  line-height: var(--leading-relaxed);
}

.hero-buttons {
  display: flex;
  gap: var(--spacing-5);
  justify-content: center;
  flex-wrap: wrap;
}

.btn {
  padding: var(--spacing-3) var(--spacing-6);
  border-radius: var(--radius-base);
  text-decoration: none;
  font-weight: var(--font-semibold);
  font-size: var(--text-base);
  transition: all var(--transition-base);
  border: var(--border-width-2) solid transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-primary {
  background: white;
  color: var(--primary-600);
  border-color: white;
}

.btn-primary:hover {
  background: var(--gray-50);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.btn-secondary {
  background: transparent;
  color: white;
  border-color: white;
}

.btn-secondary:hover {
  background: white;
  color: var(--primary-600);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.features-section {
  padding: 40px 0;
}

.features-section h2 {
  text-align: center;
  font-size: var(--text-3xl);
  font-weight: var(--font-semibold);
  margin-bottom: var(--spacing-12);
  color: var(--gray-800);
  line-height: var(--leading-tight);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-6);
}

.feature-card {
  background: white;
  padding: var(--spacing-6);
  border-radius: var(--radius-md);
  text-align: center;
  border: var(--border-width) solid var(--border-color);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary-200);
}

.feature-icon {
  font-size: var(--text-4xl);
  margin-bottom: var(--spacing-5);
  filter: grayscale(0.3);
  transition: filter var(--transition-base);
}

.feature-card:hover .feature-icon {
  filter: grayscale(0);
  transform: scale(1.1);
}

.feature-card h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-bottom: var(--spacing-3);
  color: var(--gray-800);
  line-height: var(--leading-tight);
}

.feature-card p {
  color: var(--gray-600);
  line-height: var(--leading-relaxed);
  font-size: var(--text-sm);
}
</style> 