<script setup lang="ts">
const props = defineProps<{ item: Record<string, any> }>()
const emit = defineEmits<{
  (e: 'select', res_idx: string): void
  (e: 'go-form', res_idx: string): void
}>()

const resIdx = computed<string>(() => String(props.item?.res_idx ?? props.item?.resIdx ?? ''))
const title = computed<string>(() => (
  props.item?.vw_title
  || props.item?.vwTitle
  || props.item?.res_title
  || props.item?.resTitle
  || '(무제)'
))

function fmt(v: any): string {
  if (!v) return ''
  const s = String(v).replace('T', ' ')
  return s.slice(0, 16)
}

const dayLabel = computed(() => {
  const g = props.item?.res_day_gubun ?? props.item?.resDayGubun
  return { W: '평일', D: '매일', H: '공휴일 포함' }[g as string] || ''
})

const minC = computed(() => props.item?.res_user_min_cnt ?? props.item?.resUserMinCnt)
const maxC = computed(() => props.item?.res_user_max_cnt ?? props.item?.resUserMaxCnt)
const limitU = computed(() => props.item?.res_limit_user ?? props.item?.resLimitUser)
</script>

<template>
  <div class="rounded-xl border border-royal-200 p-3 bg-white hover:bg-royal-50/50 transition-colors">
    <div class="font-medium text-gray-800 mb-2">{{ title }}</div>
    <dl class="text-xs text-gray-600 space-y-0.5">
      <div v-if="item?.res_start_dt || item?.resStartDt || item?.res_end_dt || item?.resEndDt">
        <span class="text-gray-400">예약기간</span> · {{ fmt(item?.res_start_dt ?? item?.resStartDt) }} ~ {{ fmt(item?.res_end_dt ?? item?.resEndDt) }}
      </div>
      <div v-if="minC && maxC">
        <span class="text-gray-400">신청인원</span> · {{ minC }}~{{ maxC }}명
      </div>
      <div v-if="limitU">
        <span class="text-gray-400">회당 정원</span> · {{ limitU }}명
      </div>
      <div v-if="dayLabel">
        <span class="text-gray-400">운영</span> · {{ dayLabel }}
      </div>
    </dl>
    <div class="flex gap-2 mt-3">
      <button
        class="flex-1 py-1.5 px-2 text-xs rounded-lg border border-royal-300 text-royal-600 hover:bg-royal-50"
        @click="emit('select', resIdx)"
      >
        관람정보
      </button>
      <button
        class="flex-1 py-1.5 px-2 text-xs rounded-lg bg-royal-500 text-white hover:bg-royal-600"
        @click="emit('go-form', resIdx)"
      >
        예약하기
      </button>
    </div>
  </div>
</template>
