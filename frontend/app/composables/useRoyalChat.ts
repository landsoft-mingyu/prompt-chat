// ──────────────────────────────────────────────
// useRoyalChat v4 — 좌측 메뉴 트리 사이드바 기반 챗봇 상태
// - 채팅 히스토리 완전 제거 (세션 단일, localStorage 미사용)
// - 대메뉴 클릭 → 대화창 리셋 + 가이드 요청 (pickSidebarRoot)
// - 리프 클릭 → palace/content_type 힌트 + placeholder 갱신만 (서버 호출 없음)
// - LLM 역할: 쿼리 리라이터 + 큐레이션 요약 + 예약 폼 파싱 3가지
// ──────────────────────────────────────────────
import { useSessionId } from '~/composables/useSessionId'
import type {
  BranchId,
  ChatApiRequest,
  GuideData,
  OrchestratorResponse,
  PanelStateIn,
  PanelStateOut,
  UiMessage,
} from '~/types/api'

function uid(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}

// ── 대메뉴별 기본 placeholder (백엔드 응답이 비었을 때 fallback)
const DEFAULT_PLACEHOLDER: Record<string, string> = {
  palace_intro: '원하시는 콘텐츠에 대해 질문해 주세요. (예: 경복궁 소개 역사에 대해서 알려줘)',
  reservation: '원하시는 예약 업무를 질문해 주세요.',
  visit_guide: '궁금하신 관람 정보를 질문해 주세요.',
}

const FALLBACK_PLACEHOLDER = '질문을 입력해주세요.'

export function useRoyalChat() {
  // ── 세션/라우팅 상태 ──
  const sessionId = useState<string>('royal.sessionId', () => uid())
  const { getOrCreate: getSessionId, reset: resetSessionId } = useSessionId()
  // 클라이언트에서 localStorage 세션 복원 (탭 새로고침 시 세션 유지)
  if (import.meta.client) {
    sessionId.value = getSessionId()
  }
  const topLevel = useState<BranchId | null>('royal.topLevel', () => null)
  const palace = useState<string | null>('royal.palace', () => null)
  const contentType = useState<string | null>('royal.contentType', () => null)
  const courseIdx = useState<string | null>('royal.courseIdx', () => null)
  const spotIdx = useState<string | null>('royal.spotIdx', () => null)
  const loading = useState<boolean>('royal.loading', () => false)
  const panel = useState<PanelStateOut | null>('royal.panel', () => null)

  // ── 대화 메시지 (세션 1개, 영속성 없음) ──
  const messages = useState<UiMessage[]>('royal.messages', () => [])

  // ── ChatInput placeholder (대메뉴/리프 클릭 시 갱신) ──
  const placeholder = useState<string>('royal.placeholder', () => FALLBACK_PLACEHOLDER)

  // ── 예약 폼 필드값 (우측 패널 + LLM 파싱 결과 공유) ──
  const formFields = useState<Record<string, unknown>>('royal.formFields', () => ({}))

  // ──────────────────────────────────────────────
  // 상태 리셋
  // ──────────────────────────────────────────────
  function resetFlow() {
    topLevel.value = null
    palace.value = null
    contentType.value = null
    courseIdx.value = null
    spotIdx.value = null
    panel.value = null
    placeholder.value = FALLBACK_PLACEHOLDER
    formFields.value = {}
    // 새 세션 발급 — 최근기록이 세션 단위로 1개만 남도록
    sessionId.value = import.meta.client ? resetSessionId() : uid()
  }

  function clearMessages() {
    messages.value = []
  }

  // ──────────────────────────────────────────────
  // 사이드바 네비게이션
  // ──────────────────────────────────────────────

  /** 대메뉴(큐레이션/통합예약/관람안내) 클릭 — 대화창 리셋 + 가이드 요청 */
  function pickSidebarRoot(tl: BranchId) {
    resetFlow()
    clearMessages()
    topLevel.value = tl
    placeholder.value = DEFAULT_PLACEHOLDER[tl] ?? FALLBACK_PLACEHOLDER
    // hint_only 요청으로 가이드/칩 응답 받기 (STEP 3에서 백엔드 대응)
    send('', { topLevelHint: tl })
  }

  /** 리프 노드 클릭 — palace/content_type 힌트만 세팅, 서버 호출 없음 */
  function pickSidebarLeaf(hint: {
    top_level?: BranchId | null
    palace_code?: string | null
    content_type?: string | null
    label?: string
  }) {
    if (hint.top_level) topLevel.value = hint.top_level
    if (hint.palace_code !== undefined) palace.value = hint.palace_code ?? null
    if (hint.content_type !== undefined) contentType.value = hint.content_type ?? null
    // placeholder 갱신 (사용자가 직접 프롬프트를 작성할 때 도움)
    if (hint.label) {
      placeholder.value = `${hint.label}에 대해 질문해 주세요.`
    }
  }

  // ──────────────────────────────────────────────
  // 기존 UI 인터랙션 (후보 버튼 클릭 등)
  // ──────────────────────────────────────────────

  function pickTopLevel(code: BranchId) {
    topLevel.value = code
    palace.value = null
    contentType.value = null
    courseIdx.value = null
    spotIdx.value = null
    send('', { topLevelHint: code })
  }

  function pickPalace(code: string) {
    palace.value = code
    courseIdx.value = null
    spotIdx.value = null
    send('', { topLevelHint: topLevel.value ?? 'palace_intro', palaceHint: code })
  }

  function pickContent(code: string) {
    contentType.value = code
    courseIdx.value = null
    spotIdx.value = null
    send('', {
      topLevelHint: topLevel.value,
      palaceHint: palace.value,
      contentHint: code,
    })
  }

  function pickCourseCategory(vc_idx: string) {
    courseIdx.value = vc_idx
    spotIdx.value = null
    send('', {
      topLevelHint: topLevel.value ?? 'palace_intro',
      palaceHint: palace.value,
      contentHint: contentType.value ?? 'view_course',
      courseIdxHint: vc_idx,
    })
  }

  function pickCourseSpot(vi_idx: string) {
    spotIdx.value = vi_idx
    send('', {
      topLevelHint: topLevel.value ?? 'palace_intro',
      palaceHint: palace.value,
      contentHint: contentType.value ?? 'view_course',
      courseIdxHint: courseIdx.value,
      spotIdxHint: vi_idx,
    })
  }

  /** 예시 프롬프트 / 추천 칩 클릭 — 사용자 메시지로 기록하고 전송 */
  function pickPrompt(text: string, contentCode?: string) {
    if (contentCode) contentType.value = contentCode
    send(text)
  }

  // ──────────────────────────────────────────────
  // 채팅 전송
  // ──────────────────────────────────────────────
  interface SendOpts {
    topLevelHint?: BranchId | null
    palaceHint?: string | null
    contentHint?: string | null
    courseIdxHint?: string | null
    spotIdxHint?: string | null
    panelState?: PanelStateIn | null
  }

  function addMessage(msg: UiMessage) {
    messages.value = [...messages.value, msg]
  }

  // ── 메시지 배열의 특정 id 항목을 patch로 갱신 (반응성 유지)
  function patchMessage(id: string, patch: Partial<UiMessage>) {
    const idx = messages.value.findIndex((m) => m.id === id)
    if (idx < 0) return
    const next = [...messages.value]
    next[idx] = { ...next[idx], ...patch } as UiMessage
    messages.value = next
  }

  function applyActionCard(
    actionCard: OrchestratorResponse['action_card'] | undefined | null,
  ): GuideData | null {
    if (!actionCard || typeof actionCard !== 'object') return null

    const type = String(actionCard.type ?? '')
    const items = Array.isArray(actionCard.items)
      ? actionCard.items as Record<string, unknown>[]
      : []

    if (type === 'program_list') {
      panel.value = {
        step: 'list',
        items,
        selected: null,
        form_schema: null,
      }
      topLevel.value = 'reservation'
      contentType.value = contentType.value ?? 'res_event'
      return {
        palace_name: '예약 프로그램',
        guide_type: '예약 가능 목록',
        mode: 'reservation_list',
        items,
      }
    }

    if (type === 'parts_list') {
      return null
    }

    return null
  }

  // ── 가짜 타이프라이터 — 스트리밍 LLM 호출이 아닌 응답(하드코딩/DB/renderer)에 적용
  async function fakeTypewriter(assistantId: string, fullText: string) {
    if (!fullText) return
    const intervalMs = 16
    const totalMs = Math.min(2500, Math.max(400, fullText.length * 6))
    const charsPerTick = Math.max(1, Math.ceil(fullText.length / (totalMs / intervalMs)))
    let pos = 0
    while (pos < fullText.length) {
      pos = Math.min(pos + charsPerTick, fullText.length)
      patchMessage(assistantId, { content: fullText.slice(0, pos) })
      await new Promise((r) => setTimeout(r, intervalMs))
    }
  }

  // 현재 대화 상태를 최근기록에 스냅샷 저장 (chat session 단위)
  function snapshotRecent(extraMessages?: UiMessage[]) {
    const recent = useRecentLog()
    recent.saveSnapshot({
      sessionId: sessionId.value,
      messages: extraMessages ?? messages.value,
      topLevel: topLevel.value,
      palace: palace.value,
      contentType: contentType.value,
      courseIdx: courseIdx.value,
      spotIdx: spotIdx.value,
    })
  }

  // 최근기록 엔트리 → 대화 복원
  function restoreSession(entry: import('./useRecentLog').RecentEntry) {
    sessionId.value = entry.sessionId
    topLevel.value = entry.topLevel
    palace.value = entry.palace
    contentType.value = entry.contentType
    courseIdx.value = entry.courseIdx
    spotIdx.value = entry.spotIdx
    panel.value = null
    formFields.value = {}
    placeholder.value = FALLBACK_PLACEHOLDER
    messages.value = entry.messages.map((m) => ({ ...m, streaming: false }))
  }

  async function send(userText: string, opts: SendOpts = {}) {
    const trimmed = userText.trim()

    // 네비게이션 힌트 상태 업데이트
    if (opts.topLevelHint != null) topLevel.value = opts.topLevelHint
    if (opts.palaceHint !== undefined) palace.value = opts.palaceHint ?? null
    if (opts.contentHint !== undefined) contentType.value = opts.contentHint ?? null
    if (opts.courseIdxHint !== undefined) courseIdx.value = opts.courseIdxHint ?? null
    if (opts.spotIdxHint !== undefined) spotIdx.value = opts.spotIdxHint ?? null

    if (trimmed) {
      addMessage({
        id: uid(),
        role: 'user',
        content: trimmed,
        createdAt: Date.now(),
      })
    }

    // hint_only (사이드바 네비게이션) — API 호출 없이 상태만 갱신
    if (!trimmed) return

    const assistantId = uid()
    addMessage({
      id: assistantId,
      role: 'assistant',
      content: '',
      createdAt: Date.now(),
      streaming: false,
    })

    loading.value = true

    try {
      const body: ChatApiRequest = {
        session_id: sessionId.value,
        message: trimmed,
        site_code: 'ROYAL',
      }
      const resp = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)

      const data: OrchestratorResponse = await resp.json()
      const replyText = data.message || '응답을 받지 못했습니다.'
      const structured = applyActionCard(data.action_card)

      await fakeTypewriter(assistantId, replyText)
      patchMessage(assistantId, {
        content: replyText,
        streaming: false,
        rag_sources: data.sources ?? undefined,
        structured,
      })
    } catch (e) {
      patchMessage(assistantId, {
        content: '오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
        error: true,
        streaming: false,
      })
    } finally {
      loading.value = false
      snapshotRecent()
    }
  }

  async function updatePanel(ps: PanelStateIn) {
    const current = panel.value
    if (!current) return

    if (ps.step === 'list') {
      panel.value = { ...current, step: 'list', selected: null }
      return
    }

    if ((ps.step === 'info' || ps.step === 'form') && ps.res_idx) {
      const selected = current.items.find((item) => {
        const raw = item as Record<string, unknown>
        return String(raw.res_idx ?? raw.resIdx ?? '') === ps.res_idx
      }) ?? null
      panel.value = {
        ...current,
        step: ps.step,
        items: selected ? [selected] : current.items,
        selected,
        form_schema: ps.step === 'form' ? null : current.form_schema,
      }

      if (ps.step === 'form') {
        try {
          const resp = await fetch(`/api/v1/reservations/${encodeURIComponent(ps.res_idx)}/form`)
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
          const formSchema = await resp.json()
          panel.value = {
            ...(panel.value ?? current),
            step: 'form',
            items: selected ? [selected] : current.items,
            selected,
            form_schema: formSchema,
          }
        } catch (e) {
          panel.value = {
            ...(panel.value ?? current),
            step: 'form',
            items: selected ? [selected] : current.items,
            selected,
            form_schema: null,
          }
        }
      }
    }
  }

  return {
    sessionId,
    topLevel,
    branch: topLevel, // 레거시 alias
    palace,
    contentType,
    courseIdx,
    spotIdx,
    loading,
    panel,
    messages,
    placeholder,
    formFields,
    // 리셋
    resetFlow,
    clearMessages,
    // 사이드바
    pickSidebarRoot,
    pickSidebarLeaf,
    // 기존 후보 클릭
    pickTopLevel,
    pickBranch: pickTopLevel, // 레거시 alias
    pickPalace,
    pickContent,
    pickCourseCategory,
    pickCourseSpot,
    pickPrompt,
    send,
    updatePanel,
    // 최근기록 복원
    restoreSession,
  }
}
