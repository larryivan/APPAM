<template>
  <div class="index-container">
    <div class="index-content">
      <div class="hero-section">
        <div class="hero-content">
          <h1>欢迎使用 APPAM</h1>
          <p class="hero-subtitle">一个强大的项目管理和分析平台</p>
          <div class="hero-buttons">
            <router-link :to="authState.user ? '/projects' : '/login'" class="btn btn-primary">
              {{ authState.user ? '进入项目' : '登录 APPAM' }}
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
            <div class="feature-icon"><Icon name="layout-dashboard" :size="28" :stroke-width="1.5" /></div>
            <h3>项目管理</h3>
            <p>创建、管理和跟踪您的项目进度</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon"><Icon name="wrench" :size="28" :stroke-width="1.5" /></div>
            <h3>流水线工具</h3>
            <p>使用强大的流水线工具进行数据处理</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon"><Icon name="message-circle" :size="28" :stroke-width="1.5" /></div>
            <h3>智能聊天</h3>
            <p>与AI助手交流，获得即时帮助</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon"><Icon name="globe" :size="28" :stroke-width="1.5" /></div>
            <h3>网络驱动</h3>
            <p>强大的网络爬虫和数据收集工具</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { authState } from '../lib/auth'
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
  padding: var(--spacing-6);
}

.hero-section {
  text-align: center;
  padding: var(--spacing-16) var(--spacing-10);
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color-light);
  border-radius: var(--radius-xl);
  margin-bottom: var(--spacing-16);
  color: var(--gray-900);
  box-shadow: var(--shadow-base);
  position: relative;
  overflow: hidden;
}

.hero-section::before {
  content: '';
  position: absolute;
  inset: 0;
  background: var(--primary-50);
  pointer-events: none;
}

.hero-content {
  max-width: 600px;
  margin: 0 auto;
  position: relative;
  z-index: 1;
}

.hero-content h1 {
  font-size: var(--text-4xl);
  font-weight: var(--font-bold);
  margin-bottom: var(--spacing-5);
  line-height: var(--leading-tight);
}

.hero-subtitle {
  font-size: var(--text-xl);
  margin-bottom: var(--spacing-10);
  color: var(--gray-600);
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
  backdrop-filter: blur(6px);
}

.btn-primary {
  background: var(--primary-600);
  color: white;
  border-color: transparent;
}

.btn-primary:hover {
  background: var(--primary-700);
}

.btn-secondary {
  background: var(--surface-1);
  color: var(--gray-800);
  border-color: var(--border-color);
}

.btn-secondary:hover {
  background: var(--surface-2);
  color: var(--gray-900);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.features-section {
  padding: 40px 0;
}

.features-section h2 {
  text-align: center;
  font-size: var(--text-3xl);
  font-weight: var(--font-semibold);
  margin-bottom: var(--spacing-12);
  color: var(--gray-900);
  line-height: var(--leading-tight);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-6);
}

.feature-card {
  background: var(--surface-1);
  padding: var(--spacing-6);
  border-radius: var(--radius-md);
  text-align: center;
  border: var(--border-width) solid var(--border-color-light);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-base);
  border-color: rgba(var(--accent-rgb), 0.25);
}

.feature-icon {
  font-size: var(--text-3xl);
  margin-bottom: var(--spacing-5);
  transition: transform var(--transition-base);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  background: rgba(var(--accent-rgb), 0.12);
  color: var(--primary-700);
}

.feature-card:hover .feature-icon {
  transform: scale(1.1);
}

.feature-card h3 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin-bottom: var(--spacing-3);
  color: var(--gray-900);
  line-height: var(--leading-tight);
}

.feature-card p {
  color: var(--gray-600);
  line-height: var(--leading-relaxed);
  font-size: var(--text-sm);
}
</style> 
