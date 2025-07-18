<template>
  <aside class="sidebar-nav">
    <div class="logo">
      <img src="/assets/logo.svg" alt="APPAM Logo" />
      <h1>APPAM</h1>
    </div>
    <nav>
      <div class="nav-section">
        <h3 class="section-title">Workspace</h3>
        <ul>
          <li>
            <router-link :to="`/workspace/${route.params.id}/webdrive`" class="nav-link">Webdrive</router-link>
          </li>
        </ul>
      </div>
      <div class="nav-section" v-for="section in pipeline" :key="section.title">
        <h3 class="section-title">{{ section.title }}</h3>
        <ul>
          <li v-for="tool in section.tools" :key="tool">
            <router-link :to="getToolLink(tool)" class="nav-link">
              {{ tool }}
            </router-link>
          </li>
        </ul>
      </div>
    </nav>
  </aside>
</template>

<script setup>
import { useRoute } from 'vue-router';

const route = useRoute();

const pipeline = [
  {
    title: '1. Pre-processing',
    tools: ['FastQC', 'MultiQC', 'AdapterRemoval']
  },
  {
    title: '2. Read-based Analysis',
    tools: ['bwa', 'PMDtools', 'bedtools', 'KrakenUniq', 'Krona']
  },
  {
    title: '3. Assembly & Binning',
    tools: ['MEGAHIT', 'SPAdes', 'QUAST', 'Bowtie2', 'Samtools', 'PyDamage', 'MetaBAT2', 'MaxBin2']
  },
  {
    title: '4. MAG Analysis',
    tools: ['CheckM', 'GTDB-Tk', 'PROKKA', 'RGI', 'antiSMASH']
  }
];

const getToolLink = (tool) => {
  return `/workspace/${route.params.id}/tool/${tool.toLowerCase()}`;
};

</script>

<style scoped>
.sidebar-nav {
  width: 280px;
  background: linear-gradient(180deg, var(--dark-bg) 0%, var(--dark-bg-secondary) 100%);
  color: var(--text-light);
  padding: var(--spacing-lg) var(--spacing) var(--spacing-lg) var(--spacing-lg);
  display: flex;
  flex-direction: column;
  height: 100vh;
  box-shadow: 4px 0 12px rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
  border-right: 1px solid var(--border-color-dark);
}

.logo {
  display: flex;
  align-items: center;
  margin-bottom: var(--spacing-2xl);
  padding: var(--spacing) var(--spacing-md);
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(12px);
}

.logo img {
  width: 44px;
  height: 44px;
  margin-right: var(--spacing-md);
  filter: brightness(1.2) drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.logo h1 {
  font-size: 1.625rem;
  margin: 0;
  font-weight: 700;
  background: linear-gradient(135deg, #ffffff, #e2e8f0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.01em;
}

nav {
  flex-grow: 1;
  overflow-y: auto;
  min-height: 0;
  padding-right: var(--spacing);
  scrollbar-width: thin;
  scrollbar-color: var(--text-muted) transparent;
}

.nav-section {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing) 0;
}

.section-title {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #94a3b8;
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  font-weight: 600;
  position: relative;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: -var(--spacing-sm);
  left: var(--spacing-md);
  right: var(--spacing-md);
  height: 1px;
  background: linear-gradient(90deg, #475569, transparent);
}

ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-link {
  display: block;
  padding: var(--spacing-md) var(--spacing-lg);
  color: #cbd5e1;
  text-decoration: none;
  border-radius: var(--radius-md);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 0.9rem;
  font-weight: 500;
  position: relative;
  margin: var(--spacing-xs) 0;
  border: 1px solid transparent;
  letter-spacing: 0.025em;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  transform: translateX(4px);
  border-color: rgba(255, 255, 255, 0.2);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.router-link-exact-active {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  color: #ffffff;
  font-weight: 600;
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
  border-color: rgba(255, 255, 255, 0.3);
}

.router-link-exact-active::before {
  content: '';
  position: absolute;
  left: -2px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 60%;
  background: #ffffff;
  border-radius: 0 2px 2px 0;
}
</style>
