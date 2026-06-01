<script setup lang="ts">
import type { Candidate } from '../types'

defineProps<{ candidate: Candidate }>()
const emit = defineEmits<{ dismiss: [] }>()

function onBackdropClick(e: MouseEvent) {
  if ((e.target as HTMLElement).classList.contains('dialog-backdrop')) {
    emit('dismiss')
  }
}

function scorePercent(score: number): number {
  return Math.round(score * 100)
}
</script>

<template>
  <div
    class="dialog-backdrop fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/30"
    @click="onBackdropClick"
  >
    <div class="bg-surface rounded-t-2xl sm:rounded-2xl w-full sm:max-w-lg max-h-[85vh] overflow-y-auto shadow-xl">
      <div class="p-5">
        <img
          :src="candidate.image_url"
          :alt="candidate.title"
          class="w-full h-[240px] object-cover rounded-xl"
        />
        <h3 class="text-base font-semibold text-on-surface mt-4">{{ candidate.title }}</h3>
        <p v-if="candidate.price != null" class="text-2xl font-bold text-primary mt-1">
          ¥{{ candidate.price }}
        </p>
        <p class="text-sm text-on-surface-variant mt-2">
          相似度: {{ scorePercent(candidate.score) }}%
        </p>
        <div v-if="candidate.attrs && Object.keys(candidate.attrs).length > 0" class="mt-4">
          <h4 class="text-sm font-medium text-on-surface mb-1.5">关键属性</h4>
          <div v-for="(val, key) in candidate.attrs" :key="key" class="flex gap-1 py-0.5">
            <span class="text-sm text-on-surface-variant shrink-0">{{ key }}:</span>
            <span class="text-sm text-on-surface">{{ val }}</span>
          </div>
        </div>
        <div class="mt-6 flex justify-end">
          <button
            class="text-sm font-medium text-on-surface-variant hover:text-on-surface transition-colors"
            @click="emit('dismiss')"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
