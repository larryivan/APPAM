<template>
  <div class="tool-library">
    <div class="tool-library__inner">
      <PageHeader eyebrow="Project" title="Tools" description="Individual analysis tools">
        <template #meta>
          <span>{{ visibleToolCount }} {{ visibleToolCount === 1 ? 'tool' : 'tools' }}</span>
        </template>
      </PageHeader>

      <div class="tool-controls">
        <label class="search-field">
          <Icon name="search" :size="17" />
          <input v-model.trim="searchQuery" type="search" placeholder="Search tools" aria-label="Search tools">
          <button v-if="searchQuery" type="button" title="Clear search" aria-label="Clear search" @click="searchQuery = ''">
            <Icon name="x" :size="15" />
          </button>
        </label>
        <select v-model="selectedSection" aria-label="Tool category">
          <option value="">All categories</option>
          <option v-for="section in catalogSections" :key="section.id" :value="section.id">
            {{ section.title }}
          </option>
        </select>
      </div>

      <div v-if="loading" class="tool-state" aria-live="polite">
        <Icon name="rotate-ccw" :size="24" spin />
        <span>Loading tools...</span>
      </div>

      <div v-else-if="errorMessage" class="tool-state error" role="alert">
        <span>{{ errorMessage }}</span>
        <button type="button" @click="loadTools">Try again</button>
      </div>

      <div v-else-if="!filteredSections.length" class="tool-state">
        <Icon name="search" :size="24" />
        <span>No matching tools</span>
      </div>

      <div v-else class="tool-sections">
        <section v-for="section in filteredSections" :key="section.id" class="tool-section">
          <header class="section-heading">
            <div>
              <h2>{{ section.title }}</h2>
              <p>{{ section.description }}</p>
            </div>
            <span>{{ section.tools.length }}</span>
          </header>

          <div class="tool-list">
            <router-link
              v-for="tool in section.tools"
              :key="tool.id"
              :to="toolRoute(tool, section.id)"
              class="tool-row"
            >
              <div class="tool-icon">
                <Icon :name="sectionIcon(section.icon)" :size="20" />
              </div>
              <div class="tool-copy">
                <div class="tool-title-line">
                  <h3>{{ tool.tool_name }}</h3>
                  <span v-if="tool.available === false" class="unavailable">Unavailable</span>
                </div>
                <p>{{ tool.description }}</p>
              </div>
              <span class="open-tool">Open</span>
            </router-link>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import { filterToolSections, normalizeToolSection } from '@/lib/toolUi.js'

const route = useRoute()
const router = useRouter()
const sections = ref([])
const searchQuery = ref('')
const selectedSection = ref(normalizeToolSection(route.query.section))
const loading = ref(true)
const errorMessage = ref('')
const catalogSections = computed(() => sections.value.filter((section) => section.id !== 'workflow-automation'))

const filteredSections = computed(() => filterToolSections(sections.value, {
  query: searchQuery.value,
  sectionId: selectedSection.value,
}))

const visibleToolCount = computed(() => filteredSections.value.reduce((total, section) => total + section.tools.length, 0))

function sectionIcon(icon) {
  return {
    reads: 'file-text',
    taxonomy: 'dna',
    assembly: 'layout-grid',
    binning: 'box',
    annotation: 'clipboard-list',
    proteomics: 'activity',
  }[icon] || 'wrench'
}

function toolRoute(tool, sectionId) {
  return {
    name: 'PipelineTool',
    params: { id: route.params.id, tool: tool.id },
    query: { section: sectionId },
  }
}

async function loadTools() {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await fetch('/api/tools')
    const payload = await response.json().catch(() => ({}))
    if (!response.ok || !payload.success) throw new Error(payload.error || 'Tools could not be loaded')
    sections.value = payload.sections || []
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : String(error)
  } finally {
    loading.value = false
  }
}

onMounted(loadTools)

watch(() => route.query.section, (sectionId) => {
  const normalized = normalizeToolSection(sectionId)
  if (selectedSection.value !== normalized) selectedSection.value = normalized
})

watch(selectedSection, (sectionId) => {
  if (sectionId === normalizeToolSection(route.query.section)) return
  const query = { ...route.query }
  if (sectionId) query.section = sectionId
  else delete query.section
  router.replace({ name: 'ToolLibrary', params: { id: route.params.id }, query })
})
</script>

<style scoped>
.tool-library {
  height: 100%;
  overflow-y: auto;
  background: var(--surface-0);
}

.tool-library__inner {
  width: min(1040px, 100%);
  margin: 0 auto;
  padding: var(--spacing-6);
}

.tool-controls {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 220px;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-6);
}

.search-field,
.tool-controls select {
  min-height: var(--control-height);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
}

.search-field {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: 0 var(--spacing-3);
  color: var(--gray-400);
}

.search-field input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--gray-900);
  font: inherit;
}

.search-field button {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
}

.tool-controls select {
  padding: 0 var(--spacing-3);
  color: var(--gray-700);
  font: inherit;
}

.tool-sections {
  display: grid;
  gap: var(--spacing-6);
}

.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-3);
}

.section-heading h2 {
  margin: 0;
  color: var(--gray-900);
  font-size: var(--text-lg);
}

.section-heading p {
  margin: 3px 0 0;
  color: var(--gray-500);
  font-size: var(--text-sm);
}

.section-heading > span {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.tool-list {
  display: grid;
  gap: var(--spacing-2);
}

.tool-row {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--spacing-3);
  min-height: 72px;
  padding: var(--spacing-3) var(--spacing-4);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
  color: inherit;
  text-decoration: none;
}

.tool-row:hover {
  border-color: rgba(var(--accent-rgb), 0.3);
  background: var(--surface-2);
}

.tool-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  color: var(--primary-700);
}

.tool-title-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.tool-copy h3 {
  margin: 0;
  color: var(--gray-900);
  font-size: var(--text-base);
}

.tool-copy p {
  display: -webkit-box;
  overflow: hidden;
  margin: 4px 0 0;
  color: var(--gray-600);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.unavailable {
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--warning-50);
  color: var(--warning-600);
  font-size: 11px;
  font-weight: var(--font-semibold);
}

.open-tool {
  color: var(--primary-700);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.tool-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-3);
  min-height: 180px;
  color: var(--gray-500);
}

.tool-state.error {
  color: var(--error-600);
}

.tool-state button {
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: var(--font-semibold);
  cursor: pointer;
}

@media (max-width: 680px) {
  .tool-library__inner { padding: var(--spacing-4); }
  .tool-controls { grid-template-columns: 1fr; }
  .tool-row { grid-template-columns: 36px minmax(0, 1fr); }
  .tool-icon { width: 36px; height: 36px; }
  .open-tool { display: none; }
}
</style>
