<template>
  <div class="home-view">
    <main class="home-main">
      <section class="home-intro" aria-labelledby="home-title">
        <img class="home-logo" :src="logoUrl" alt="">
        <span class="home-eyebrow">Laboratory analysis platform</span>
        <h1 id="home-title">APPAM</h1>
        <p>
          Ancient metagenomics and paleoproteomics in one focused,
          reproducible workspace.
        </p>

        <div class="home-actions">
          <router-link :to="primaryRoute" class="home-primary-action">
            <Icon :name="authState.user ? 'folder-open' : 'log-in'" :size="17" />
            <span>{{ authState.user ? 'Open projects' : 'Sign in' }}</span>
            <Icon name="chevron-right" :size="16" />
          </router-link>
          <router-link to="/documentation" class="home-secondary-action">
            <Icon name="file-text" :size="17" />
            <span>Documentation</span>
          </router-link>
        </div>
      </section>

      <section class="home-workflows" aria-label="Available analyses">
        <article v-for="workflow in workflows" :key="workflow.id" class="home-workflow">
          <span class="workflow-icon">
            <Icon :name="workflow.id === 'appam-smk' ? 'dna' : 'activity'" :size="20" />
          </span>
          <div>
            <h2>{{ workflow.label }}</h2>
            <p>{{ workflow.description }}</p>
            <span>{{ workflow.inputHint }}</span>
          </div>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import Icon from '../components/ui/Icon.vue'
import { authState } from '../lib/auth.js'
import { WORKFLOW_OPTIONS } from '../lib/workflowUi.js'
import { withBase } from '../lib/basePath.js'

const logoUrl = withBase('/assets/logo.svg')

const workflows = WORKFLOW_OPTIONS
const primaryRoute = computed(() => authState.user ? '/projects' : '/login')
</script>

<style scoped>
.home-view {
  height: 100%;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--surface-0);
  color: var(--gray-900);
}

.home-main {
  display: flex;
  min-width: 0;
  width: min(960px, 100%);
  min-height: 100%;
  margin: 0 auto;
  padding: 56px 24px 44px;
  flex-direction: column;
  justify-content: center;
}

.home-intro {
  min-width: 0;
}

/* Hold the reading measure without shifting the block off the container axis. */
.home-intro > p {
  max-width: 52ch;
}

.home-logo {
  display: block;
  width: 44px;
  height: 44px;
  margin-bottom: 20px;
}

.home-eyebrow {
  color: var(--gray-500);
  font-size: 11px;
  font-weight: var(--font-medium);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.home-intro h1 {
  margin: 6px 0 10px;
  font-size: 48px;
  line-height: 1.05;
}

.home-intro > p {
  max-width: 620px;
  margin: 0;
  color: var(--gray-600);
  font-size: var(--text-lg);
  line-height: 1.6;
}

.home-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 26px;
}

.home-primary-action,
.home-secondary-action {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  text-decoration: none;
  transition: background var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast);
}

.home-primary-action {
  border-color: var(--primary-600);
  background: var(--primary-600);
  color: white;
}

.home-primary-action:hover {
  border-color: var(--primary-700);
  background: var(--primary-700);
}

.home-secondary-action {
  background: var(--surface-1);
  color: var(--gray-700);
}

.home-secondary-action:hover {
  border-color: var(--border-color-dark);
  background: var(--surface-2);
  color: var(--gray-900);
}

.home-workflows {
  display: grid;
  min-width: 0;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin-top: var(--spacing-12);
  border-block: 1px solid var(--border-color);
}

.home-workflow {
  display: grid;
  min-width: 0;
  grid-template-columns: 38px minmax(0, 1fr);
  gap: 12px;
  padding: 22px 24px 22px 0;
}

.home-workflow + .home-workflow {
  padding-left: 24px;
  border-left: 1px solid var(--border-color);
}

.workflow-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: var(--radius-base);
  background: var(--surface-2);
  color: var(--primary-600);
}

.home-workflow h2 {
  margin: 0 0 5px;
  font-size: var(--text-base);
}

.home-workflow > div {
  min-width: 0;
}

.home-workflow p {
  margin: 0;
  color: var(--gray-600);
  font-size: var(--text-sm);
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.home-workflow div > span {
  display: block;
  margin-top: 9px;
  color: var(--gray-400);
  font-size: var(--text-xs);
}

@media (max-width: 680px) {
  .home-main {
    justify-content: flex-start;
    padding: 38px 18px 34px;
  }

  .home-logo {
    width: 40px;
    height: 40px;
    margin-bottom: 18px;
  }

  .home-intro h1 {
    font-size: 40px;
  }

  .home-intro > p {
    font-size: var(--text-base);
  }

  .home-actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    margin-top: 22px;
  }

  .home-primary-action,
  .home-secondary-action {
    width: 100%;
  }

  .home-workflows {
    grid-template-columns: minmax(0, 1fr);
    margin-top: 38px;
  }

  .home-workflow {
    padding: 18px 0;
  }

  .home-workflow + .home-workflow {
    padding-left: 0;
    border-top: 1px solid var(--border-color);
    border-left: 0;
  }
}
</style>
