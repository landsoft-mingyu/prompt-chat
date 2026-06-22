<!--
  ──────────────────────────────────────────────
  MenuTreeNode — 사이드바 메뉴 트리 재귀 노드
  - level=0: 대메뉴 (K-Startup 스타일 "큰 메뉴" 블록)
      · 큰 아이콘 + 굵은 레이블
      · 기본 접힘, 클릭 시 가이드 요청 + 자식 펼치기
  - level=1+: 그룹/리프 (얕은 트리, hover 배경)
  ──────────────────────────────────────────────
-->
<script setup lang="ts">
import type { BranchId, MenuNode } from '~/types/api'

const props = defineProps<{
  node: MenuNode
  level: number
  activeKey?: string | null
}>()

const emit = defineEmits<{
  (e: 'pickRoot', tl: BranchId): void
  (e: 'pickLeaf', node: MenuNode): void
}>()

// ── 기본 접힘 상태 — 사용자가 대메뉴 클릭할 때만 펼침
const open = ref(false)

const hasChildren = computed(() => (props.node.children?.length ?? 0) > 0)
const isActive = computed(() => props.activeKey === props.node.key)

// ── 대메뉴 아이콘 (level 0 전용)
const rootIcon: Record<string, string> = {
  curation: '🏛️',
  reservation: '🎟️',
  visit_guide: '📘',
}

// ── activeKey가 이 대메뉴 하위에 속하면 자동 펼침
watch(
  () => props.activeKey,
  (key) => {
    if (!key || props.level !== 0) return
    if (key.startsWith(props.node.key + '.')) open.value = true
  },
  { immediate: true },
)

function onClick() {
  if (props.level === 0 && props.node.top_level) {
    // 대메뉴 — 서버 가이드 요청 + 하위 펼침
    open.value = true
    emit('pickRoot', props.node.top_level as BranchId)
    return
  }
  if (hasChildren.value) {
    // 그룹 노드 — 토글
    open.value = !open.value
    return
  }
  // 리프 — 힌트 세팅 (서버 호출 없음)
  emit('pickLeaf', props.node)
}
</script>

<template>
  <!-- ── level 0: 대메뉴 (K-Startup 스타일 큰 메뉴 블록) ── -->
  <div v-if="level === 0" class="mb-2">
    <button
      class="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-royal-50 transition-colors border border-transparent hover:border-royal-100"
      :class="isActive ? 'bg-royal-50 border-royal-200' : ''"
      @click="onClick"
    >
      <span class="text-2xl leading-none">{{ rootIcon[node.key] || '📁' }}</span>
      <span class="flex-1 text-left text-base font-semibold text-gray-800">{{ node.label }}</span>
      <span v-if="hasChildren" class="text-gray-400 text-sm">
        <span v-if="open">▾</span><span v-else>▸</span>
      </span>
    </button>
    <div v-if="open && hasChildren" class="mt-1 ml-1 pl-2 border-l border-royal-100 space-y-0.5">
      <MenuTreeNode
        v-for="child in node.children"
        :key="child.key"
        :node="child"
        :level="1"
        :active-key="activeKey"
        @pick-root="(tl) => emit('pickRoot', tl)"
        @pick-leaf="(n) => emit('pickLeaf', n)"
      />
    </div>
  </div>

  <!-- ── level 1+: 그룹 / 리프 ── -->
  <div v-else>
    <button
      class="w-full flex items-center gap-1 px-2 py-1.5 rounded-md text-sm hover:bg-royal-50 transition-colors text-left"
      :class="[
        level === 1 ? 'text-gray-700' : 'text-gray-600',
        isActive && !hasChildren ? 'bg-royal-100 text-royal-700 font-medium' : '',
      ]"
      :style="{ paddingLeft: `${(level - 1) * 12 + 8}px` }"
      @click="onClick"
    >
      <span v-if="hasChildren" class="text-gray-400 text-xs w-3 inline-block">
        <span v-if="open">▾</span><span v-else>▸</span>
      </span>
      <span v-else class="w-3 inline-block text-royal-300">·</span>
      <span class="flex-1 truncate">{{ node.label }}</span>
    </button>
    <div v-if="open && hasChildren" class="space-y-0.5">
      <MenuTreeNode
        v-for="child in node.children"
        :key="child.key"
        :node="child"
        :level="level + 1"
        :active-key="activeKey"
        @pick-root="(tl) => emit('pickRoot', tl)"
        @pick-leaf="(n) => emit('pickLeaf', n)"
      />
    </div>
  </div>
</template>
