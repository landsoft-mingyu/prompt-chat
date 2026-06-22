<script setup lang="ts">
import type { FormSchema } from '~/types/api'

const props = defineProps<{
  schema: FormSchema | null
  item: Record<string, any> | null
}>()

const chat = useRoyalChat()

// ── 날짜/회차 로컬 선택 상태
const selectedDate = ref<string>('')
const selectedPartIdx = ref<number | null>(null)

// 날짜 옵션 (schema.date_options)
const dateOptions = computed<string[]>(() => (props.schema as any)?.date_options ?? [])

// 회차 옵션 — 선택된 날짜에 해당하는 것만
const allParts = computed<Record<string, any>[]>(() => (props.schema as any)?.part_options ?? [])
const partOptions = computed(() => {
  if (!selectedDate.value) return allParts.value
  return allParts.value.filter((p) => {
    const d = String(p.res_part_date ?? '').slice(0, 10)
    return d === selectedDate.value
  })
})

// 날짜 선택 시 회차 초기화
watch(selectedDate, () => { selectedPartIdx.value = null })

// 채팅 파서가 _selected_date 를 넣어주면 날짜 자동 선택
watch(
  () => (chat.formFields.value as Record<string, any>)?._selected_date,
  (d) => {
    if (typeof d === 'string' && d && dateOptions.value.includes(d)) {
      selectedDate.value = d
    }
  },
  { immediate: true },
)

// ── 폼 필드 values (LLM 파싱 결과 + 수동 입력 공유)
const values = reactive<Record<string, any>>({ ...(chat.formFields.value as Record<string, any>) })

watch(() => chat.formFields.value, (v) => {
  for (const k of Object.keys(v || {})) {
    if (values[k] !== v[k]) values[k] = v[k]
  }
}, { deep: true })

watch(values, (v) => { chat.formFields.value = { ...v } }, { deep: true })

watch(() => props.schema, (s) => {
  if (!s) return
  for (const f of s.fields || []) {
    const ff = f as typeof f & { value?: any }
    if (ff.value !== undefined && ff.value !== null && ff.value !== '') {
      values[f.name] = ff.value
    } else if (values[f.name] === undefined) {
      values[f.name] = f.type === 'number' ? f.min ?? 1 : ''
    }
  }
  for (const f of s.extra_fields || []) {
    const ff = f as typeof f & { value?: any }
    if (ff.value !== undefined && ff.value !== null && ff.value !== '') {
      values[f.name] = ff.value
    } else if (values[f.name] === undefined) {
      values[f.name] = ''
    }
  }
}, { immediate: true, deep: true })

// 날짜 포맷 (MM/DD 요일)
const DAY_KO = ['일', '월', '화', '수', '목', '금', '토']
function fmtDate(iso: string): string {
  const d = new Date(iso)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const dow = DAY_KO[d.getDay()]
  return `${mm}/${dd}(${dow})`
}

const submitting = ref(false)
const result = ref<{ ok: boolean; message: string } | null>(null)

// 폼 제출 가능 여부
const canSubmit = computed(() => {
  if (dateOptions.value.length > 0 && !selectedDate.value) return false
  if (partOptions.value.length > 0 && selectedPartIdx.value === null) return false
  return true
})

async function submit() {
  if (!props.schema || !canSubmit.value) return
  submitting.value = true
  result.value = null
  try {
    // 선택된 날짜를 formFields 에 미리 주입 — 백엔드가 submit 처리 시 사용
    if (selectedDate.value) {
      chat.formFields.value = { ...chat.formFields.value, _selected_date: selectedDate.value }
    }
    // 채팅 "예약해줘" 와 동일 경로로 제출 → 백엔드가 reservation_submitted 응답
    // → useRoyalChat 이 예약목록에 자동 기록 + 패널 닫기 + AI 확인 메시지 렌더
    await chat.send('예약해줘')
  } catch (e: any) {
    result.value = { ok: false, message: e?.message || '제출 중 오류' }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="schema && item">
    <h3 class="font-semibold text-gray-800 mb-1">{{ item.vw_title || item.res_title || '예약 신청' }}</h3>
    <p class="text-xs text-gray-500 mb-4">날짜와 정보를 입력해주세요.</p>

    <!-- ── 날짜 선택 ── -->
    <div v-if="dateOptions.length > 0" class="mb-4">
      <div class="text-xs font-medium text-gray-600 mb-2">날짜 선택 <span class="text-royal-500">*</span></div>
      <div class="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto">
        <button
          v-for="d in dateOptions"
          :key="d"
          type="button"
          class="px-2.5 py-1.5 rounded-lg text-xs border transition-colors"
          :class="selectedDate === d
            ? 'bg-royal-500 text-white border-royal-500'
            : 'bg-white text-gray-700 border-royal-200 hover:bg-royal-50'"
          @click="selectedDate = d"
        >
          {{ fmtDate(d) }}
        </button>
      </div>
    </div>

    <!-- ── 회차 선택 ── -->
    <div v-if="selectedDate && partOptions.length > 0" class="mb-4">
      <div class="text-xs font-medium text-gray-600 mb-2">회차 선택 <span class="text-royal-500">*</span></div>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="p in partOptions"
          :key="p.pt_idx"
          type="button"
          class="px-2.5 py-1.5 rounded-lg text-xs border transition-colors"
          :class="selectedPartIdx === p.pt_idx
            ? 'bg-royal-500 text-white border-royal-500'
            : 'bg-white text-gray-700 border-royal-200 hover:bg-royal-50'"
          @click="selectedPartIdx = p.pt_idx"
        >
          <span v-if="p.res_part != null" class="font-medium">{{ p.res_part }}회차</span>
          <span v-if="p.res_part != null"> · </span>
          {{ p.res_part_start_time ?? '' }} ~ {{ p.res_part_end_time ?? '' }}
        </button>
      </div>
    </div>

    <!-- ── 날짜 선택됐거나 날짜 옵션 없을 때 폼 표시 ── -->
    <form
      v-if="!dateOptions.length || selectedDate"
      class="space-y-3"
      @submit.prevent="submit"
    >
      <div v-for="f in schema.fields" :key="f.name" class="flex flex-col">
        <label class="text-xs text-gray-600 mb-1">
          {{ f.label }}
          <span v-if="f.required" class="text-royal-500">*</span>
        </label>
        <input
          v-if="f.type === 'number'"
          v-model.number="values[f.name]"
          type="number"
          :min="f.min"
          :max="f.max"
          :required="f.required"
          class="border border-royal-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-royal-400"
        >
        <input
          v-else-if="f.type === 'tel' || f.type === 'email' || f.type === 'text'"
          v-model="values[f.name]"
          :type="f.type"
          :required="f.required"
          class="border border-royal-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-royal-400"
        >
        <textarea
          v-else-if="f.type === 'textarea'"
          v-model="values[f.name]"
          :required="f.required"
          rows="3"
          class="border border-royal-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-royal-400"
        />
        <select
          v-else-if="f.type === 'select'"
          v-model="values[f.name]"
          :required="f.required"
          class="border border-royal-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-royal-400"
        >
          <option v-for="opt in f.options || []" :key="opt" :value="opt">{{ opt }}</option>
        </select>
      </div>

      <div v-if="schema.address_required" class="text-xs text-royal-500">· 주소 입력이 필요합니다.</div>
      <div v-if="schema.id_verifi_required" class="text-xs text-royal-500">· 본인인증이 필요합니다.</div>

      <!-- 선택된 날짜/회차 요약 -->
      <div v-if="selectedDate" class="text-xs text-gray-500 bg-royal-50 rounded-lg px-3 py-2">
        <span class="font-medium">선택:</span>
        {{ fmtDate(selectedDate) }}
        <span v-if="selectedPartIdx !== null">
          <template v-if="partOptions.find(p => p.pt_idx === selectedPartIdx)?.res_part != null">
            · {{ partOptions.find(p => p.pt_idx === selectedPartIdx)?.res_part }}회차
          </template>
          · {{ partOptions.find(p => p.pt_idx === selectedPartIdx)?.res_part_start_time }} ~
            {{ partOptions.find(p => p.pt_idx === selectedPartIdx)?.res_part_end_time }}
        </span>
      </div>

      <button
        type="submit"
        :disabled="submitting || !canSubmit"
        class="w-full py-2 rounded-xl bg-royal-500 text-white hover:bg-royal-600 disabled:opacity-50"
      >
        {{ submitting ? '신청 중…' : '예약 신청' }}
      </button>

      <div
        v-if="result"
        class="text-xs p-2 rounded-lg"
        :class="result.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'"
      >
        {{ result.message }}
      </div>
    </form>
  </div>
  <div v-else class="text-sm text-gray-400">예약 폼을 불러오는 중…</div>
</template>
