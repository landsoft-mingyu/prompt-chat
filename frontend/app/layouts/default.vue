<!--
  ──────────────────────────────────────────────
  default 레이아웃 — 3열 구조: [좌측 메뉴 사이드바] [중앙 챗봇] [우측 예약 패널(조건부)]
  ──────────────────────────────────────────────
-->
<script setup lang="ts">
const sidebarOpen = ref(true)
const chat = useRoyalChat()
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden kossis-gradient">
    <!-- ── 좌측 메뉴 사이드바 ── -->
    <Sidebar v-if="sidebarOpen" @collapse="sidebarOpen = false" />

    <!-- ── 중앙: 헤더 + 챗봇 본문 ── -->
    <div class="flex-1 flex flex-col relative min-w-0">
      <header class="h-12 flex items-center justify-between px-4 bg-transparent">
        <button
          v-if="!sidebarOpen"
          class="p-2 rounded-md hover:bg-white/60"
          title="사이드바 열기"
          @click="sidebarOpen = true"
        >
          <span class="block w-4 h-4 border-l-2 border-t-2 border-b-2 border-royal-300 rounded-sm"></span>
        </button>
        <span v-else></span>
        <div class="text-xs text-gray-400">
          <span v-if="chat.palace.value">궁: {{ chat.palace.value }}</span>
          <span v-if="chat.contentType.value" class="ml-2">콘텐츠: {{ chat.contentType.value }}</span>
        </div>
      </header>

      <!-- ── 예약 우측 패널은 pages/index.vue에서 렌더 ── -->
      <main class="flex-1 overflow-hidden">
        <slot />
      </main>
    </div>
  </div>
</template>
