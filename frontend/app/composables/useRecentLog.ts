// ──────────────────────────────────────────────
// useRecentLog — 최근기록 (사이드바 하단)
//   - chat session(=chat.sessionId) 단위로 대화 스냅샷 저장
//   - "새 대화시작" / 사이드바 대메뉴 클릭 시 sessionId 갱신 → 새 엔트리
//   - 클릭하면 해당 대화를 그대로 복원 (messages + palace/topLevel 등)
//   - localStorage 최대 20개, 오래된 건 자동 제거
// ──────────────────────────────────────────────
import type { BranchId, UiMessage } from '~/types/api'

export interface RecentEntry {
  id: string
  sessionId: string            // chat session id — 스냅샷 키
  prompt: string               // 리스트에 보일 제목 (첫 사용자 질문)
  topLevel: BranchId | null
  palace: string | null
  contentType: string | null
  courseIdx: string | null
  spotIdx: string | null
  messages: UiMessage[]        // 전체 대화 로그 (복원용)
  createdAt: number
  updatedAt: number
}

const STORAGE_KEY = 'royal.recent'
const MAX_ENTRIES = 20
// 메시지 하나당 content 캡 (localStorage quota 보호)
const MAX_CONTENT_LEN = 8000

function readAll(): RecentEntry[] {
  if (!import.meta.client) return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as RecentEntry[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeAll(list: RecentEntry[]) {
  if (!import.meta.client) return
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(list)) } catch { /* quota */ }
}

function uid(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
}

// 스트리밍 플래그 제거 + 긴 content 자름 — 직렬화 안전성 확보
function sanitizeMessages(messages: UiMessage[]): UiMessage[] {
  return messages.map((m) => {
    const content = (m.content || '')
    return {
      ...m,
      streaming: false,
      content: content.length > MAX_CONTENT_LEN ? content.slice(0, MAX_CONTENT_LEN) + '…' : content,
    }
  })
}

export function useRecentLog() {
  const entries = useState<RecentEntry[]>('royal.recent.entries', () => [])

  function refresh() {
    entries.value = readAll().sort((a, b) => b.updatedAt - a.updatedAt).slice(0, MAX_ENTRIES)
  }

  interface SnapshotInput {
    sessionId: string
    messages: UiMessage[]
    topLevel: BranchId | null
    palace: string | null
    contentType: string | null
    courseIdx: string | null
    spotIdx: string | null
  }

  // 현재 채팅 세션의 대화 스냅샷을 저장/갱신. 메시지가 없거나 사용자 질문이 아직 없으면 skip.
  function saveSnapshot(data: SnapshotInput) {
    if (!data.sessionId) return
    const firstUser = data.messages.find((m) => m.role === 'user' && (m.content || '').trim())
    if (!firstUser) return
    const now = Date.now()
    const all = readAll()
    const existingIdx = all.findIndex((e) => e.sessionId === data.sessionId)
    const snapshot: RecentEntry = {
      id: existingIdx >= 0 ? all[existingIdx].id : uid(),
      sessionId: data.sessionId,
      prompt: firstUser.content.trim(),
      topLevel: data.topLevel,
      palace: data.palace,
      contentType: data.contentType,
      courseIdx: data.courseIdx,
      spotIdx: data.spotIdx,
      messages: sanitizeMessages(data.messages),
      createdAt: existingIdx >= 0 ? all[existingIdx].createdAt : now,
      updatedAt: now,
    }
    const merged = existingIdx >= 0
      ? [...all.slice(0, existingIdx), snapshot, ...all.slice(existingIdx + 1)]
      : [snapshot, ...all]
    const pruned = merged
      .sort((a, b) => b.updatedAt - a.updatedAt)
      .slice(0, MAX_ENTRIES)
    writeAll(pruned)
    entries.value = pruned
  }

  function remove(id: string) {
    const merged = readAll().filter((e) => e.id !== id)
    writeAll(merged)
    entries.value = merged
  }

  function clear() {
    writeAll([])
    entries.value = []
  }

  return { entries, refresh, saveSnapshot, remove, clear }
}
