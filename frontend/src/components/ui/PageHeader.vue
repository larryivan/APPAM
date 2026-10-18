<template>
  <header class="page-header">
    <div class="page-header__copy">
      <div v-if="eyebrow" class="page-header__eyebrow">{{ eyebrow }}</div>
      <h1 class="page-header__title">
        <slot name="title">{{ title }}</slot>
      </h1>
      <p v-if="description || $slots.description" class="page-header__desc">
        <slot name="description">{{ description }}</slot>
      </p>
      <div v-if="$slots.meta" class="page-header__meta">
        <slot name="meta" />
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup>
/**
 * 统一页头:eyebrow 小标签 + 标题 + 描述 + 右侧动作。
 * 所有顶层视图复用,取代各页自定义的 .page-header / __hero / .card-header 等多套写法。
 */
defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-4);
  padding-bottom: 14px;
  border-bottom: var(--border-width) solid var(--border-color-light);
  margin-bottom: 18px;
}

.page-header__eyebrow {
  color: var(--gray-500);
  font-size: 11px;
  font-weight: var(--font-medium);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.page-header__title {
  margin: 2px 0 0;
  font-size: 22px;
  font-weight: var(--font-semibold);
  color: var(--gray-900);
}

.page-header__desc {
  margin: 3px 0 0;
  font-size: var(--text-sm);
  color: var(--gray-500);
  max-width: 60ch;
}

.page-header__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-2) var(--spacing-3);
  margin-top: 8px;
  font-size: var(--text-xs);
  color: var(--gray-500);
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  flex-shrink: 0;
}

@media (max-width: 640px) {
  .page-header {
    flex-direction: column;
  }
  .page-header__actions {
    width: 100%;
  }
}
</style>
