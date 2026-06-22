<!--
  ──────────────────────────────────────────────
  CandidateGroup — 3 variant 후보 버튼
  - prompt : 예시 프롬프트 카드 (▸ 아이콘)
  - card   : 궁능/코스 카드 (min-w 160px)
  - pill   : 일반 pill (flex-wrap)
  clickable=false 칩은 hover/클릭 없이 참고만 (가이드 예시용)
  ──────────────────────────────────────────────
-->
<script setup lang="ts">
import type { Candidate } from '~/types/api'

defineProps<{
  title?: string
  candidates: Candidate[]
  variant?: 'pill' | 'card' | 'prompt'
}>()
const emit = defineEmits<{ (e: 'pick', code: string, label?: string, hint?: string): void }>()

// ── 클릭 가능 여부 (undefined면 기본 true)
function isClickable(c: Candidate): boolean {
  return c.clickable !== false
}
</script>

<template>
  <div class="space-y-2">
    <div v-if="title" class="text-xs text-gray-500 pl-1">{{ title }}</div>

    <!-- ── prompt variant: 예시 프롬프트 카드 ── -->
    <div v-if="variant === 'prompt'" class="flex flex-col gap-2">
      <template v-for="c in candidates" :key="c.code">
        <button
          v-if="isClickable(c)"
          class="px-3 py-2 rounded-xl border border-royal-200 bg-white/80 hover:bg-royal-100 text-left transition-colors"
          @click="emit('pick', c.code, c.label, c.hint || undefined)"
        >
          <div class="text-sm text-gray-800">
            <span class="text-royal-400 mr-1">▸</span>
            {{ c.label }}
          </div>
        </button>
        <!-- 클릭 불가 (가이드 예시용) — 동일 외양 유지하되 hover/커서 없음 -->
        <div
          v-else
          class="px-3 py-2 rounded-xl border border-royal-200 bg-white/60 text-left cursor-default select-text"
          aria-disabled="true"
        >
          <div class="text-sm text-gray-600">
            <span class="text-royal-400 mr-1">▸</span>
            {{ c.label }}
          </div>
        </div>
      </template>
    </div>

    <!-- ── pill/card variant: 일반 후보 버튼 ── -->
    <div v-else class="flex flex-wrap gap-2">
      <template v-for="c in candidates" :key="c.code">
        <button
          v-if="isClickable(c)"
          class="px-3 py-2 rounded-xl border border-royal-200 bg-white/80 hover:bg-royal-50 text-sm text-left"
          :class="variant === 'card' ? 'min-w-[160px]' : ''"
          @click="emit('pick', c.code, c.label, c.hint || undefined)"
        >
          <div class="font-medium text-gray-800">{{ c.label }}</div>
          <div v-if="c.hint" class="text-xs text-gray-500 mt-0.5">{{ c.hint }}</div>
        </button>
        <div
          v-else
          class="px-3 py-2 rounded-xl border border-royal-200 bg-white/60 text-sm text-left cursor-default select-text"
          :class="variant === 'card' ? 'min-w-[160px]' : ''"
          aria-disabled="true"
        >
          <div class="font-medium text-gray-600">{{ c.label }}</div>
          <div v-if="c.hint" class="text-xs text-gray-400 mt-0.5">{{ c.hint }}</div>
        </div>
      </template>
    </div>
  </div>
</template>
