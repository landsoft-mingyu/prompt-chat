<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'

const props = defineProps<{ item: Record<string, any> | null }>()
const emit = defineEmits<{ (e: 'go-form', res_idx: string): void }>()

const title = computed<string>(() => (
  props.item?.vw_title
  || props.item?.vwTitle
  || props.item?.res_title
  || props.item?.resTitle
  || '관람정보'
))
const resIdx = computed<string>(() => String(props.item?.res_idx ?? props.item?.resIdx ?? ''))

marked.setOptions({ breaks: true, gfm: true })

const contentHtml = computed(() => {
  const text = props.item?.res_content_text || props.item?.resContentText || ''
  if (!text) return ''
  const raw = marked.parse(text) as string
  if (import.meta.client) return DOMPurify.sanitize(raw)
  return raw
})

function fmt(v: any): string {
  if (!v) return ''
  return String(v).replace('T', ' ').slice(0, 16)
}

const dayLabel = computed(() => {
  const g = props.item?.res_day_gubun ?? props.item?.resDayGubun
  return { W: '평일', D: '매일', H: '공휴일 포함' }[g as string] || ''
})
</script>

<template>
  <div v-if="item">
    <h3 class="font-semibold text-gray-800 mb-3">{{ title }}</h3>
    <dl class="text-xs text-gray-600 space-y-1 mb-4 border-b border-royal-100 pb-3">
      <div v-if="item.res_start_dt || item.resStartDt || item.res_end_dt || item.resEndDt">
        <span class="text-gray-400">예약기간</span> · {{ fmt(item.res_start_dt ?? item.resStartDt) }} ~ {{ fmt(item.res_end_dt ?? item.resEndDt) }}
      </div>
      <div v-if="item.res_user_min_cnt || item.resUserMinCnt">
        <span class="text-gray-400">신청인원</span> · {{ item.res_user_min_cnt ?? item.resUserMinCnt }}~{{ item.res_user_max_cnt ?? item.resUserMaxCnt }}명
      </div>
      <div v-if="item.res_limit_user || item.resLimitUser">
        <span class="text-gray-400">회당 정원</span> · {{ item.res_limit_user ?? item.resLimitUser }}명
      </div>
      <div v-if="dayLabel">
        <span class="text-gray-400">운영</span> · {{ dayLabel }}
      </div>
      <div v-if="(item.id_verifi_yn ?? item.idVerifiYn) === 'Y'" class="text-royal-500">
        · 본인인증 필요
      </div>
      <div v-if="(item.address_use_yn ?? item.addressUseYn) === 'Y'" class="text-royal-500">
        · 주소 입력 필요
      </div>
    </dl>

    <div v-if="contentHtml" class="royal-md text-sm" v-html="contentHtml" />
    <div v-else class="text-sm text-gray-400">상세 안내가 등록되어 있지 않습니다.</div>

    <div class="mt-6">
      <button
        class="w-full py-2 rounded-xl bg-royal-500 text-white hover:bg-royal-600"
        @click="emit('go-form', resIdx)"
      >
        예약하기
      </button>
    </div>
  </div>
</template>
