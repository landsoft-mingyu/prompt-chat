<script setup lang="ts">
import type { BranchId, Stage } from '~/types/api'

definePageMeta({ layout: 'default' })

const chat = useRoyalChat()
const text = ref('')
const scrollEl = ref<HTMLElement | null>(null)

function onSubmit() {
  const v = text.value.trim()
  if (!v) return
  chat.send(v)
  text.value = ''
}

function onHeroSend(prompt: string) {
  chat.send(prompt)
}

function onMessagePick(code: string, stage: Stage, label?: string, hint?: string) {
  if (stage === 'top_level') chat.pickTopLevel(code as BranchId)
  else if (stage === 'palace') chat.pickPalace(code)
  else if (stage === 'content') {
    // 추천 칩 / 예시 프롬프트 — label(전체 문장)을 사용자 메시지로 전송
    const prompt = label || hint || code
    chat.send(prompt)
  }
  else if (stage === 'visit_sub') chat.pickContent(code)
  else if (stage === 'course_category') chat.pickCourseCategory(code)
  else if (stage === 'course_spot') chat.pickCourseSpot(code)
}

// 채팅 내 예약 카드 버튼(관람정보/예약하기) 클릭 → 우측 패널 상태 전환
function onPanelAction(action: 'info' | 'form', res_idx: string) {
  chat.updatePanel({ res_idx, step: action })
}

// ── 우측 예약 패널 출현 조건:
//    예약 목록/상세/신청 상태가 만들어지면 우측 패널을 함께 노출.
const showPanel = computed(() => {
  return !!chat.panel.value && chat.messages.value.length > 0
})

// ──────────────────────────────────────────────
// 스트리밍/타이프라이터 중 자동 스크롤 — MutationObserver로 DOM 변화 감지
// 사용자가 위로 올리면 해제, 하단 근처(80px)로 내려오면 재개
const stickToBottom = ref(true)
let observer: MutationObserver | null = null
let programmaticScroll = false

function onUserScroll() {
  if (programmaticScroll) {
    programmaticScroll = false
    return
  }
  const el = scrollEl.value
  if (!el) return
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
  stickToBottom.value = nearBottom
}

function scrollToBottom() {
  const el = scrollEl.value
  if (!el || !stickToBottom.value) return
  programmaticScroll = true
  el.scrollTop = el.scrollHeight
}

// scrollEl이 mount/unmount 될 때 observer 재연결
watch(scrollEl, (el) => {
  if (observer) { observer.disconnect(); observer = null }
  if (!el) return
  observer = new MutationObserver(() => scrollToBottom())
  observer.observe(el, { childList: true, subtree: true, characterData: true })
  // 최초 연결 시 하단 이동
  nextTick(() => { scrollToBottom() })
})

// 새 메시지 시작 시점엔 무조건 하단 고정 복구
watch(
  () => chat.messages.value.length,
  () => {
    stickToBottom.value = true
    nextTick(() => scrollToBottom())
  },
)

onUnmounted(() => {
  if (observer) { observer.disconnect(); observer = null }
})
</script>

<template>
  <div class="h-full w-full flex">
    <!-- 채팅 영역 (메인) -->
    <div class="flex-1 flex flex-col min-w-0">
      <ChatHero
        v-if="chat.messages.value.length === 0"
        @send="onHeroSend"
      />

      <template v-else>
        <div ref="scrollEl" class="flex-1 overflow-y-auto px-6 py-6" @scroll="onUserScroll">
          <div class="max-w-5xl mx-auto space-y-6">
            <ChatMessage
              v-for="m in chat.messages.value"
              :key="m.id"
              :message="m"
              @pick="onMessagePick"
              @panel-action="onPanelAction"
            />
            <div v-if="chat.loading.value" class="text-sm text-gray-400 pl-2">답변 생성 중…</div>
          </div>
        </div>
        <div class="px-6 pb-6 flex justify-center">
          <ChatInput
            v-model="text"
            :loading="chat.loading.value"
            :placeholder="chat.placeholder.value"
            @submit="onSubmit"
          />
        </div>
      </template>
    </div>

    <!-- 예약 우측 패널 -->
    <PanelReservationPanel
      v-if="showPanel"
      :panel="chat.panel.value"
      :palace-code="chat.palace.value || ''"
      @select="(res_idx) => chat.updatePanel({ res_idx, step: 'info' })"
      @go-form="(res_idx) => chat.updatePanel({ res_idx, step: 'form' })"
      @back-list="() => chat.updatePanel({ step: 'list' })"
    />
  </div>
</template>
