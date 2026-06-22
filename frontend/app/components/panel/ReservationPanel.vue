<script setup lang="ts">
import type { PanelStateOut } from '~/types/api'

const props = defineProps<{
  panel: PanelStateOut | null
  palaceCode: string
}>()

const emit = defineEmits<{
  (e: 'select', res_idx: string): void
  (e: 'go-form', res_idx: string): void
  (e: 'back-list'): void
}>()

const step = computed(() => props.panel?.step ?? 'list')
const items = computed(() => props.panel?.items ?? [])
const selected = computed(() => props.panel?.selected ?? {})
const formSchema = computed(() => props.panel?.form_schema ?? null)

// items[0]을 상세/폼 단계에서 사용
const currentItem = computed(() => (items.value as any[])[0] ?? null)

function resolveImg(url: string): string {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  return url.startsWith('/') ? url : `/${url}`
}
</script>

<template>
  <aside class="w-[560px] shrink-0 h-full bg-white border-l border-royal-100 flex flex-col">
    <header class="flex items-center justify-between px-4 py-3 border-b border-royal-100 bg-royal-50/50">
      <div class="flex items-center gap-2">
        <button
          v-if="step !== 'list'"
          class="text-gray-500 hover:text-royal-500 text-sm"
          @click="emit('back-list')"
        >
          &#8592; 목록
        </button>
        <h2 class="font-semibold text-gray-800">
          <span v-if="step === 'list'">예약 상품 목록</span>
          <span v-else-if="step === 'info'">관람정보</span>
          <span v-else-if="step === 'form'">예약 신청</span>
        </h2>
      </div>
    </header>

    <!-- 1. 카드 리스트 -->
    <div v-if="step === 'list'" class="flex-1 overflow-y-auto p-4 space-y-3">
      <div v-if="items.length === 0" class="text-sm text-gray-500 text-center py-8">
        현재 예약 가능한 상품이 없습니다.
      </div>
      <PanelReservationCard
        v-for="(it, i) in items"
        :key="(it as any).res_idx || i"
        :item="it"
        @select="(res_idx) => emit('select', res_idx)"
        @go-form="(res_idx) => emit('go-form', res_idx)"
      />
    </div>

    <!-- 2. 관람정보 -->
    <div v-else-if="step === 'info'" class="flex-1 overflow-y-auto p-4">
      <PanelReservationDetail
        :item="currentItem"
        @go-form="(res_idx) => emit('go-form', res_idx)"
      />
    </div>

    <!-- 3. 예약 폼 -->
    <div v-else-if="step === 'form'" class="flex-1 overflow-y-auto p-4">
      <PanelReservationForm
        :schema="formSchema"
        :item="currentItem"
      />
    </div>
  </aside>
</template>
