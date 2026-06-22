export interface Envelope<T> {
  success: boolean
  data: T | null
  error: { code: string; message: string; details?: Record<string, unknown> } | null
}

// ────────── Royal chatbot types (v3) ──────────
export type BranchId =
  | 'palace_intro'
  | 'reservation'
  | 'visit_guide'
  | 'visiting_hours_direct'
  | 'visiting_fee_direct'

export type NextAction =
  | 'ASK_TOP_LEVEL'
  | 'ASK_PALACE'
  | 'ASK_CONTENT'
  | 'ASK_VISIT_SUB'
  | 'ASK_COURSE_CATEGORY'
  | 'ASK_COURSE_SPOT'
  | 'ANSWER'
  | 'CLARIFY'

export type PanelStep = 'list' | 'info' | 'form' | 'submit'
export type ImageSource = 'html' | 'attachfile' | 'thumbnail' | 'curation'

export type Stage =
  | 'top_level'
  | 'palace'
  | 'content'
  | 'visit_sub'
  | 'course_category'
  | 'course_spot'

export interface Candidate {
  code: string
  label: string
  hint?: string | null
  /** 클릭 가능 여부 — 가이드 예시 칩처럼 참고만 하는 경우 false (기본 true) */
  clickable?: boolean
}

export interface SourceRef {
  mode: 'db' | 'rag'
  source_table?: string | null
  source_id?: string | null
  title?: string | null
  score?: number | null
  palace_code?: string | null
  content_type?: string | null
}

export interface ImageItem {
  url: string
  alt?: string
  source?: ImageSource
}

export interface FormFieldDef {
  name: string
  label: string
  type: 'text' | 'tel' | 'email' | 'number' | 'select' | 'textarea'
  required?: boolean
  min?: number
  max?: number
  options?: string[]
}

export interface FormSchema {
  res_idx?: string
  fields: FormFieldDef[]
  address_required?: boolean
  id_verifi_required?: boolean
  date_options?: string[]
  part_options?: Record<string, unknown>[]
  extra_fields?: FormFieldDef[]
  extra_fields_raw?: string
}

export interface PanelStateOut {
  step: PanelStep
  items: Record<string, unknown>[]
  form_schema?: FormSchema | null
  selected?: Record<string, unknown> | null
}

export interface PanelStateIn {
  step?: PanelStep | null
  res_idx?: string | null
  selected_date?: string | null
  selected_part?: string | null
  user_count?: number | null
  form_fields?: Record<string, unknown>
}

export interface ChatRequest {
  session_id: string
  message: string
  branch?: BranchId | null
  palace?: string | null
  content_type?: string | null
  course_idx?: string | null
  spot_idx?: string | null
  panel_state?: PanelStateIn | null
  history?: { role: 'user' | 'assistant'; content: string }[]
  hint_only?: boolean
}

// ──────────────────────────────────────────────
// 구조화 응답 — 현재: 해설안내(docent) sections
// 궁능별 실제 데이터에 존재하는 섹션만 포함 (빈 섹션 없음)
// ──────────────────────────────────────────────
export type GuideSectionType = 'schedule_table' | 'bullet_list' | 'info_cards' | 'warning_box'

export interface GuideScheduleTable {
  headers: string[]
  rows: (string | number)[][]
}
export interface GuideInfoCard {
  label: string
  value: string
}
export interface GuideWarningBox {
  text: string
}

export interface GuideSection {
  title: string
  type: GuideSectionType
  // type 별 data 형식이 달라 union. 렌더러에서 type으로 좁힘
  data: GuideScheduleTable | string[] | GuideInfoCard[] | GuideWarningBox
}

export interface GuideData {
  palace_name: string
  guide_type?: string
  // 렌더링 모드
  //  - 'html'             : DB 원문 그대로 (v-html)
  //  - 'sections'         : 타입별 커스텀 섹션
  //  - 'curated'          : LLM 큐레이션 요약(summary_md) + 원문 아코디언(html)
  //  - 'reservation_list' : 예약 가능 상품 인라인 카드 + 관람정보/예약하기 버튼
  //  - 'reservation_info' : 관람정보 AI 답변 하단에 예약하기 버튼
  //  - 'story_grid'             : 이야기 제목 버튼 그리드 + 클릭 시 본문 인라인 확장
  //  - 'reservation_submitted'  : 예약 접수 완료 — 프론트가 예약목록에 자동 추가
  mode?: 'html' | 'sections' | 'curated' | 'reservation_list' | 'reservation_info' | 'story_grid' | 'reservation_submitted'
  html?: string
  sections?: GuideSection[]
  summary_md?: string
  // mode='reservation_list' / 'story_grid' 공용 — 원본 데이터 배열
  items?: Record<string, unknown>[]
  // mode='reservation_info' / 'reservation_submitted' — 예약 식별자
  res_idx?: string
  // mode='reservation_submitted' 전용 — 예약목록 자동 기록용
  title?: string
  palace_code?: string | null
  fields?: Record<string, unknown>
  selected_date?: string | null
}

export interface ChatData {
  reply: string
  next_action: NextAction
  candidates: Candidate[]
  sources: SourceRef[]
  panel?: PanelStateOut | null
  images: ImageItem[]
  palace?: string | null
  content_type?: string | null
  branch?: BranchId | null
  course_idx?: string | null
  spot_idx?: string | null
  /** 대메뉴/리프 진입 시 입력창 placeholder 힌트 (STEP 3에서 백엔드가 채움) */
  placeholder?: string | null
  /** 예약 폼 LLM 파싱 결과 — panel.form_schema 필드 value 머지용 (STEP 7) */
  form_updates?: Record<string, unknown> | null
  /** 구조화 응답 (범용) — 해설안내 등 타입별 커스텀 렌더링 */
  structured?: GuideData | null
}

// ────────── UI state ──────────
export type ChatRole = 'user' | 'assistant'

export interface RagSource {
  title: string
  content: string
  score?: number | null
}

export interface UiMessage {
  id: string
  role: ChatRole
  content: string
  createdAt: number
  error?: boolean
  next_action?: NextAction
  candidates?: Candidate[]
  sources?: SourceRef[]
  rag_sources?: RagSource[]
  images?: ImageItem[]
  stage?: Stage
  // 구조화 응답 — ChatMessage 렌더러가 마크다운 대신/위에 커스텀 블록으로 렌더
  structured?: GuideData | null
  // SSE 스트리밍 중 여부 — 커서 표시 및 타이프라이터 중복 방지
  streaming?: boolean
}

// ────────── Menu tree (좌측 사이드바) ──────────
export interface MenuNode {
  key: string
  label: string
  top_level?: BranchId | null
  palace_code?: string | null
  content_type?: string | null
  children?: MenuNode[]
}

export interface MenuTree {
  roots: MenuNode[]
}

// ────────── RAG Search types ──────────
export interface RagSearchRequest {
  query: string
  top_k?: number
  source_types?: string[]
  site_code?: string
}

export interface RagSearchResult {
  id: string | number
  title: string
  content: string
  source_type: string
  source_table: string
  site_code: string
  score: number
  url?: string
  metadata?: Record<string, unknown>
}

export interface RagSearchResponse {
  results: RagSearchResult[]
  total_count: number
  query: string
}

// ────────── POST /api/v1/chat ──────────
export interface ChatApiRequest {
  session_id: string
  message: string
  site_code?: string
}

export interface OrchestratorResponse {
  session_id: string
  message: string
  intent: string
  mode: 'chat' | 'reservation' | 'rag'
  action_card?: Record<string, unknown> | null
  slots_needed?: string[] | null
  slots_filled?: Record<string, unknown> | null
  requires_confirmation?: boolean
  sources?: RagSource[] | null
}
