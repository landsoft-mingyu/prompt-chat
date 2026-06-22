// ──────────────────────────────────────────────
// useMenuTree — 좌측 사이드바 메뉴 트리 로더
// - GET /api/v1/menu/tree (1회 캐시, 5분 TTL)
// - 실패 시 빈 트리 반환 (사이드바가 비어 보일 뿐, 다른 경로 차단 없음)
// ──────────────────────────────────────────────
import type { MenuTree } from '~/types/api'

const CACHE_TTL_MS = 5 * 60 * 1000

export function useMenuTree() {
  const { request } = useApi()

  // ── 전역 싱글턴 — 탭 내 모든 컴포넌트가 동일한 트리 공유
  const tree = useState<MenuTree | null>('royal.menuTree', () => null)
  const loadedAt = useState<number>('royal.menuTreeAt', () => 0)
  const loading = useState<boolean>('royal.menuTreeLoading', () => false)
  const error = useState<string | null>('royal.menuTreeError', () => null)

  async function load(force = false): Promise<MenuTree> {
    const now = Date.now()
    if (!force && tree.value && (now - loadedAt.value) < CACHE_TTL_MS) {
      return tree.value
    }
    loading.value = true
    error.value = null
    try {
      const data = await request<MenuTree>('/api/v1/menu/tree', { method: 'GET' })
      tree.value = data
      loadedAt.value = now
      return data
    } catch (e) {
      error.value = e instanceof Error ? e.message : '메뉴 트리 로드 실패'
      if (!tree.value) tree.value = { roots: [] }
      return tree.value
    } finally {
      loading.value = false
    }
  }

  return { tree, loading, error, load }
}
