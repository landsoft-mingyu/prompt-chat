<!--
  ──────────────────────────────────────────────
  ChatHero — 첫 진입 화면 (메시지 0개, 사이드바에서 아직 선택 안 함)
  - 좌측 메뉴에서 선택하거나 아래 입력창에 직접 질문하도록 안내
  - 기존 5버튼은 좌측 사이드바 트리로 이전되어 여기선 제거
  ──────────────────────────────────────────────
-->
<script setup lang="ts">
const emit = defineEmits<{
  (e: 'send', text: string): void
}>()

const text = ref('')

function submit() {
  const v = text.value.trim()
  if (!v) return
  emit('send', v)
  text.value = ''
}
</script>

<template>
  <div class="h-full w-full flex flex-col items-center justify-center px-6">
    <h1 class="text-4xl md:text-5xl font-semibold text-gray-800 mb-2 flex items-center gap-2">
      <span>궁능유적본부</span>
      <span class="text-royal-400">✦</span>
      <span>AI</span>
    </h1>
    <p class="text-sm text-gray-500 mb-8">조선왕조 궁능 · 관람 · 예약 안내</p>

    <!-- ── 안내 문구 ── -->
    <div class="mb-6 text-center space-y-1">
      <p class="text-gray-600 text-sm">좌측 <span class="text-royal-500 font-medium">큐레이션 / 통합예약 / 관람안내</span> 메뉴에서 원하시는 항목을 선택해주세요.</p>
      <p class="text-gray-400 text-xs">또는 아래 입력창에 직접 질문해주세요.</p>
    </div>

    <ChatInput v-model="text" @submit="submit" />
  </div>
</template>
