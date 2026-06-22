// ──────────────────────────────────────────────
// useReservationLog — 예약 접수 기록 (사이드바 > 아카이브 > 예약목록)
//   - 채팅에서 예약 접수 완료(reservation_submitted) 시 자동 기록
//   - localStorage 기반, 최대 50건, 최신순
//   - 시연 모드(DB 등록 없음)이지만 사용자 입장에선 "내 예약 내역"처럼 보임
// ──────────────────────────────────────────────

export interface ReservationEntry {
  id: string
  title: string                    // 프로그램명
  palaceCode: string | null
  res_idx: string
  fields: Record<string, unknown>  // name, mobile, email, user_count
  selectedDate: string | null
  createdAt: number
}

const STORAGE_KEY = 'royal.reservations'
const MAX_ENTRIES = 50

function readAll(): ReservationEntry[] {
  if (!import.meta.client) return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as ReservationEntry[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeAll(list: ReservationEntry[]) {
  if (!import.meta.client) return
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(list)) } catch { /* quota */ }
}

function uid(): string {
  return `r-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
}

export function useReservationLog() {
  const entries = useState<ReservationEntry[]>('royal.reservations.entries', () => [])

  function refresh() {
    entries.value = readAll().sort((a, b) => b.createdAt - a.createdAt).slice(0, MAX_ENTRIES)
  }

  function add(input: Omit<ReservationEntry, 'id' | 'createdAt'>): ReservationEntry {
    const entry: ReservationEntry = {
      id: uid(),
      createdAt: Date.now(),
      ...input,
    }
    const all = [entry, ...readAll()].slice(0, MAX_ENTRIES)
    writeAll(all)
    entries.value = all
    return entry
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

  return { entries, refresh, add, remove, clear }
}
