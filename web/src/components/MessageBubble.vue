<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { ChatMessage } from '../types'
import CandidateCard from './CandidateCard.vue'
import CitationSection from './CitationSection.vue'
import ClarifySection from './ClarifySection.vue'
import SkeletonCard from './SkeletonCard.vue'
import { useCardStagger } from '../composables/useGSAP'

const props = defineProps<{ message: ChatMessage }>()
const emit = defineEmits<{ clarifySend: [text: string] }>()
const candidatesRef = ref<HTMLElement | null>(null)
const { animateCards } = useCardStagger()

// 候选商品出现时交错入场
watch(
  () => props.message.candidates?.length ?? 0,
  async (n) => {
    if (n > 0) {
      await nextTick()
      const els = candidatesRef.value?.querySelectorAll<HTMLElement>('.candidate-card')
      if (els && els.length) animateCards(Array.from(els))
    }
  },
)
</script>

<template>
  <div class="message-bubble flex w-full" :class="message.role === 'user' ? 'justify-end' : 'justify-start'">
    <div :class="message.role === 'user' ? 'items-end' : 'items-start'" class="flex flex-col max-w-[75%] sm:max-w-[70%]">
      <!-- User image -->
      <img
        v-if="message.imageLocalUri && message.role === 'user'"
        :src="message.imageLocalUri"
        alt="用户图片"
        class="w-28 h-28 object-cover rounded-xl mb-1.5"
      />

      <div class="flex gap-2.5" :class="message.role === 'assistant' ? '' : ''">
        <!-- Bot avatar -->
        <div
          v-if="message.role === 'assistant'"
          class="shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
          style="background-color: rgba(44, 44, 46, 0.08)"
        >
          <svg class="w-[18px] h-[18px] text-on-surface/40" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 14.5m14.8.8l1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0112 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5" />
          </svg>
        </div>

        <!-- Bubble content -->
        <div
          class="rounded-2xl px-3.5 py-3"
          :class="message.role === 'user' ? 'rounded-br-sm' : 'rounded-bl-sm'"
          :style="{
            backgroundColor: message.role === 'user' ? 'rgba(44, 44, 46, 0.08)' : 'var(--color-surface)',
            boxShadow: message.role === 'user' ? 'none' : '0 1px 3px rgba(0,0,0,0.08)',
          }"
        >
          <!-- Candidates -->
          <div ref="candidatesRef" v-if="message.candidates && message.candidates.length > 0" class="mb-2.5">
            <p class="text-xs font-medium text-on-surface-variant/70 mb-2">候选商品</p>
            <div class="flex gap-2.5 overflow-x-auto scrollbar-hide">
              <CandidateCard
                v-for="c in message.candidates"
                :key="c.sku_id"
                :candidate="c"
              />
            </div>
          </div>

          <!-- Loading skeleton -->
          <div v-if="message.isLoading && !message.isStreaming" class="mb-2">
            <p class="text-xs text-on-surface-variant/60 mb-2">正在搜索...</p>
            <div class="flex gap-2">
              <SkeletonCard v-for="i in 3" :key="i" />
            </div>
          </div>

          <!-- Text -->
          <p
            v-if="message.text"
            class="text-sm leading-relaxed text-on-surface whitespace-pre-wrap break-words"
          >
            {{ message.text }}
          </p>

          <!-- Citations -->
          <CitationSection
            v-if="message.citations && message.citations.length > 0"
            :citations="message.citations"
          />

          <!-- Error -->
          <div v-if="message.isError" class="flex items-center gap-1 mt-1">
            <svg class="w-3.5 h-3.5 shrink-0" style="color: #BA3B3B" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 5.636a9 9 0 11-12.728 0 9 9 0 0112.728 0zM12 9v4m0 4h.01" />
            </svg>
            <span class="text-xs" style="color: #BA3B3B">{{ message.errorMessage || '出错了' }}</span>
          </div>
        </div>
      </div>

      <!-- Clarify -->
      <ClarifySection
        v-if="message.needClarify && message.clarifyQuestion"
        :question="message.clarifyQuestion"
        @send="emit('clarifySend', $event)"
      />
    </div>
  </div>
</template>
