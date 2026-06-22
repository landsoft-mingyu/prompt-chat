<!--
  ──────────────────────────────────────────────
  Sidebar v3
  - 상단: 로고
  - 탭: [메뉴] [아카이브]
  - 메뉴 탭: 새 대화시작 + 대메뉴 (큐레이션/통합예약/관람안내)
  - 아카이브 탭: [최근기록] [예약목록] 서브탭
  ──────────────────────────────────────────────
-->
<script setup lang="ts">
import type { BranchId } from '~/types/api'
import type { RecentEntry } from '~/composables/useRecentLog'
import type { ReservationEntry } from '~/composables/useReservationLog'

const emit = defineEmits<{ (e: 'collapse'): void }>()

const chat = useRoyalChat()
const recent = useRecentLog()
const resLog = useReservationLog()

onMounted(() => {
  recent.refresh()
  resLog.refresh()
})

// ── 탭 상태
const tab = ref<'menu' | 'archive'>('menu')
const archiveSub = ref<'recent' | 'reservation'>('recent')

// ── 대메뉴 3개
interface RootMenu {
  key: string
  label: string
  icon: string
  topLevel: BranchId
}
const ICON_CURATION = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 4l9 6.5"/><path d="M5 10.5V19h14v-8.5"/><path d="M9 19v-5h6v5"/></svg>`
const ICON_RESERVATION = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4z"/><path d="M13 6v12" stroke-dasharray="2 2"/></svg>`
const ICON_VISIT_GUIDE = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h10a4 4 0 0 1 4 4v12"/><path d="M5 4v16h14"/><path d="M8 9h7M8 13h7M8 17h4"/></svg>`

const rootMenus: RootMenu[] = [
  { key: 'curation',    label: '큐레이션', icon: ICON_CURATION,    topLevel: 'palace_intro' },
  { key: 'reservation', label: '통합예약', icon: ICON_RESERVATION, topLevel: 'reservation' },
  { key: 'visit_guide', label: '관람안내', icon: ICON_VISIT_GUIDE, topLevel: 'visit_guide' },
]

const menuLabelByTl: Record<string, string> = {
  palace_intro: '큐레이션',
  reservation:  '통합예약',
  visit_guide:  '관람안내',
}

const palaceLabelByCode: Record<string, string> = {
  gbg: '경복궁', cdg: '창덕궁', cgg: '창경궁', dsg: '덕수궁',
  jms: '종묘', rtm: '조선왕릉',
}

const activeRootKey = computed<string | null>(() => {
  const tl = chat.topLevel.value
  if (!tl) return null
  const found = rootMenus.find((m) => m.topLevel === tl)
  return found?.key ?? null
})

function onPickRoot(m: RootMenu) {
  chat.pickSidebarRoot(m.topLevel)
}

function onNewChat() {
  chat.resetFlow()
  chat.clearMessages()
}

function onPickRecent(entry: RecentEntry) {
  chat.restoreSession(entry)
}

function onDeleteRecent(id: string, e: Event) {
  e.stopPropagation()
  recent.remove(id)
}

function onDeleteReservation(id: string, e: Event) {
  e.stopPropagation()
  resLog.remove(id)
}

const expandedRes = ref<string | null>(null)
function toggleReservation(id: string) {
  expandedRes.value = expandedRes.value === id ? null : id
}

// ── 시간 포맷
function formatTime(ts: number): string {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function formatDate(ts: number): string {
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

// 예약 상세 라벨 매핑 (backend 필드명 → 한글)
const FIELD_LABELS: Record<string, string> = {
  name: '대표자 이름',
  mobile: '휴대전화',
  email: '이메일',
  user_count: '인원',
}
function labelOf(k: string): string { return FIELD_LABELS[k] || k }
</script>

<template>
  <aside class="w-64 h-full flex flex-col bg-white border-r border-gray-200">
    <!-- ── 상단 로고 ── -->
    <div class="h-16 flex items-center justify-between px-4 border-b border-gray-100">
      <div class="flex items-center gap-1.5 font-bold text-lg text-gray-800">
        <span>궁능</span>
        <span class="text-royal-400">✦</span>
        <span>AI</span>
      </div>
      <button
        class="p-1.5 rounded-md hover:bg-gray-100 text-gray-400"
        title="사이드바 닫기"
        @click="emit('collapse')"
      >
        <span class="block w-4 h-4 border-r-2 border-t-2 border-b-2 border-gray-300 rounded-sm"></span>
      </button>
    </div>

    <!-- ── 상위 탭: 메뉴 / 아카이브 ── -->
    <div class="flex border-b border-gray-200">
      <button
        class="flex-1 py-3 text-sm font-medium transition-colors"
        :class="tab === 'menu'
          ? 'text-royal-600 border-b-2 border-royal-500 bg-royal-50/40'
          : 'text-gray-500 hover:text-gray-700'"
        @click="tab = 'menu'"
      >메뉴</button>
      <button
        class="flex-1 py-3 text-sm font-medium transition-colors"
        :class="tab === 'archive'
          ? 'text-royal-600 border-b-2 border-royal-500 bg-royal-50/40'
          : 'text-gray-500 hover:text-gray-700'"
        @click="tab = 'archive'"
      >아카이브</button>
    </div>

    <!-- ── 메뉴 탭 ── -->
    <div v-if="tab === 'menu'" class="flex-1 overflow-y-auto flex flex-col">
      <button
        class="flex items-center gap-2 px-4 py-3 text-left text-sm text-gray-700 hover:bg-royal-50/60 border-b border-gray-100"
        @click="onNewChat"
      >
        <span class="text-royal-500 text-lg leading-none">+</span>
        <span>새 대화시작</span>
      </button>

      <nav class="py-2">
        <button
          v-for="m in rootMenus"
          :key="m.key"
          class="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors"
          :class="activeRootKey === m.key
            ? 'bg-royal-50 text-royal-600 font-semibold border-l-4 border-royal-500 pl-3'
            : 'text-gray-700 hover:bg-gray-50 border-l-4 border-transparent pl-3'"
          @click="onPickRoot(m)"
        >
          <span class="menu-icon inline-flex shrink-0" v-html="m.icon" />
          <span class="text-sm">{{ m.label }}</span>
        </button>
      </nav>
    </div>

    <!-- ── 아카이브 탭 ── -->
    <div v-else class="flex-1 overflow-y-auto flex flex-col">
      <!-- 서브탭: 최근기록 / 예약목록 -->
      <div class="flex gap-1 px-3 py-2 border-b border-gray-100">
        <button
          class="flex-1 py-1.5 rounded-md text-xs font-medium transition-colors"
          :class="archiveSub === 'recent'
            ? 'bg-royal-500 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
          @click="archiveSub = 'recent'"
        >🕐 최근기록</button>
        <button
          class="flex-1 py-1.5 rounded-md text-xs font-medium transition-colors"
          :class="archiveSub === 'reservation'
            ? 'bg-royal-500 text-white'
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'"
          @click="archiveSub = 'reservation'"
        >📋 예약목록</button>
      </div>

      <!-- [최근기록] -->
      <div v-if="archiveSub === 'recent'" class="px-3 py-3">
        <div v-if="recent.entries.value.length === 0" class="text-xs text-gray-400 px-1 py-4 text-center">
          아직 기록이 없습니다.
        </div>
        <div v-else class="space-y-1.5">
          <button
            v-for="r in recent.entries.value"
            :key="r.id"
            class="group w-full text-left px-2 py-1.5 rounded-md hover:bg-royal-50/60"
            @click="onPickRecent(r)"
          >
            <div class="text-sm text-gray-800 truncate flex items-center justify-between gap-2">
              <span class="truncate">{{ r.prompt }}</span>
              <span
                class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-royal-500 text-xs"
                title="삭제"
                @click="(e) => onDeleteRecent(r.id, e)"
              >✕</span>
            </div>
            <div class="flex items-center gap-1.5 text-xs text-gray-400 mt-0.5">
              <span v-if="r.topLevel" class="inline-block bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded text-[10px]">
                🏛 {{ menuLabelByTl[r.topLevel] || r.topLevel }}
              </span>
              <span>🕐 {{ formatTime(r.createdAt) }}</span>
            </div>
          </button>
        </div>
      </div>

      <!-- [예약목록] -->
      <div v-else class="px-3 py-3">
        <div v-if="resLog.entries.value.length === 0" class="text-xs text-gray-400 px-1 py-4 text-center">
          아직 예약 내역이 없습니다.
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="r in resLog.entries.value"
            :key="r.id"
            class="border border-gray-200 rounded-lg overflow-hidden"
          >
            <button
              class="group w-full text-left px-2.5 py-2 hover:bg-royal-50/60 flex items-start justify-between gap-2"
              @click="toggleReservation(r.id)"
            >
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-800 truncate">{{ r.title }}</div>
                <div class="flex items-center gap-1.5 text-xs text-gray-500 mt-0.5">
                  <span v-if="r.palaceCode" class="inline-block bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded text-[10px]">
                    🏛 {{ palaceLabelByCode[r.palaceCode] || r.palaceCode }}
                  </span>
                  <span v-if="r.selectedDate">📅 {{ r.selectedDate }}</span>
                  <span v-else>🕐 {{ formatDate(r.createdAt) }}</span>
                </div>
              </div>
              <span
                class="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-royal-500 text-xs mt-0.5"
                title="삭제"
                @click="(e) => onDeleteReservation(r.id, e)"
              >✕</span>
            </button>
            <div v-if="expandedRes === r.id" class="px-2.5 py-2 border-t border-gray-100 bg-gray-50 text-xs space-y-0.5">
              <div v-for="(v, k) in r.fields" :key="k" class="flex gap-1.5">
                <span class="text-gray-500 min-w-[4.5rem]">{{ labelOf(String(k)) }}</span>
                <span class="text-gray-800 break-all">{{ v }}</span>
              </div>
              <div class="text-gray-400 pt-1 text-[10px]">접수일시 · {{ new Date(r.createdAt).toLocaleString('ko-KR') }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── 하단 공식 사이트 링크 ── -->
    <div class="border-t border-gray-100 py-3 px-2 text-sm text-gray-600">
      <a
        href="https://royal.khs.go.kr/ROYAL/main/index.do"
        target="_blank"
        rel="noopener"
        class="block px-3 py-1.5 rounded-md hover:bg-royal-50"
      >
        <span class="text-royal-400 mr-2">↗</span>공식 사이트
      </a>
    </div>
  </aside>
</template>

<style>
.menu-icon svg { display: block; }
</style>
