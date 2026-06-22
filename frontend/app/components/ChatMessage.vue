<script setup lang="ts">
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import type { Stage, UiMessage } from '~/types/api'

const props = defineProps<{ message: UiMessage }>()
const emit = defineEmits<{
  (e: 'pick', code: string, stage: Stage, label?: string, hint?: string): void
  (e: 'panel-action', action: 'info' | 'form', res_idx: string): void
}>()

const isAssistant = computed(() => props.message.role === 'assistant')
const isStreaming = computed(() => !!props.message.streaming)
const hasCandidates = computed(
  () => !!props.message.candidates && props.message.candidates.length > 0,
)
const hasImages = computed(() => !!props.message.images && props.message.images.length > 0)
const isReservationList = computed(
  () => props.message.structured?.mode === 'reservation_list',
)
const isStoryGrid = computed(
  () => props.message.structured?.mode === 'story_grid',
)
const isWide = computed(
  () => (props.message.content?.length ?? 0) > 800 || hasImages.value
    || isReservationList.value || isStoryGrid.value,
)

// 스토리 그리드: 선택된 항목 idx (메시지 id 단위로 독립)
const selectedStoryIdx = ref<string | null>(null)
const storyStreaming = ref(false)
const storyStreamedText = ref('')
let storyStreamTimer: ReturnType<typeof setInterval> | null = null

function stopStoryStream() {
  if (storyStreamTimer != null) {
    clearInterval(storyStreamTimer)
    storyStreamTimer = null
  }
  storyStreaming.value = false
}

function streamStoryContent(full: string) {
  stopStoryStream()
  if (!full) {
    storyStreamedText.value = ''
    return
  }
  const intervalMs = 16
  const totalMs = Math.min(3500, Math.max(600, full.length * 6))
  const charsPerTick = Math.max(1, Math.ceil(full.length / (totalMs / intervalMs)))
  storyStreaming.value = true
  storyStreamedText.value = ''
  let pos = 0
  storyStreamTimer = setInterval(() => {
    pos = Math.min(pos + charsPerTick, full.length)
    storyStreamedText.value = full.slice(0, pos)
    if (pos >= full.length) stopStoryStream()
  }, intervalMs)
}

function selectStory(idx: string) {
  const items = (props.message.structured?.items ?? []) as any[]
  const target = items.find((it) => String(it.idx) === idx)
  // 같은 항목 재클릭 → 닫기 + 스트림 중단
  if (selectedStoryIdx.value === idx) {
    selectedStoryIdx.value = null
    stopStoryStream()
    storyStreamedText.value = ''
    return
  }
  selectedStoryIdx.value = idx
  streamStoryContent(String(target?.content || ''))
}

const selectedStory = computed(() => {
  if (!selectedStoryIdx.value) return null
  const items = (props.message.structured?.items ?? []) as any[]
  return items.find((it) => String(it.idx) === selectedStoryIdx.value) ?? null
})

onUnmounted(() => stopStoryStream())

const candidateVariant = computed<'card' | 'pill' | 'prompt'>(() => {
  const s = props.message.stage
  if (s === 'content') return 'prompt'
  if (s === 'palace' || s === 'course_category' || s === 'course_spot') return 'card'
  return 'pill'
})

marked.setOptions({ breaks: true, gfm: true })

// ── ~~이중 틸드~~ 는 그대로 두고, 단독 ~는 \~ 로 이스케이프
// marked v5+ 는 ~text~ (single) 도 strikethrough 처리하므로,
// 한국어 범위 표기(1392~1897년, 09:00~18:00 등)가 취소선이 되는 것 방지
const escapeLoneTildes = (md: string): string =>
  md.replace(/(?<!~)~(?!~)/g, '\\~')

// ── 이미지는 상단 배너 영역에서 별도 렌더하므로 본문 마크다운에서는 제거
const stripImagesInMarkdown = (md: string): string =>
  md
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/<img\b[^>]*>/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

const renderedMarkdown = computed(() => {
  if (props.message.role !== 'assistant' || props.message.error) return ''
  const src = escapeLoneTildes(stripImagesInMarkdown(props.message.content || ''))
  const raw = marked.parse(src) as string
  const html = import.meta.client ? DOMPurify.sanitize(raw) : raw
  return isStreaming.value ? html + '<span class="typing-cursor"></span>' : html
})

// ──────────────────────────────────────────────
// 구조화 응답 HTML — DB 원문 그대로 sanitize 후 v-html
// 운영사이트 CSS 클래스 (time_gray/time_red/time_blue/bd_table/t_inn_wrap 등) 보존
// mode='html' 또는 mode='curated'의 "원문 전체 보기" 에서 공통 사용
// ──────────────────────────────────────────────
const renderedStructuredHtml = computed(() => {
  const s = props.message.structured
  if (!s || !s.html) return ''
  if (import.meta.client) {
    return DOMPurify.sanitize(s.html, {
      ADD_TAGS: ['em'],
      ADD_ATTR: ['class', 'rowspan', 'colspan', 'scope', 'style'],
    })
  }
  return s.html
})

// ──────────────────────────────────────────────
// 큐레이션 요약 마크다운 — LLM이 뽑은 핵심 정보
// ──────────────────────────────────────────────
const renderedCuratedSummary = computed(() => {
  const s = props.message.structured
  if (!s || s.mode !== 'curated' || !s.summary_md) return ''
  const html = marked.parse(escapeLoneTildes(s.summary_md)) as string
  if (import.meta.client) return DOMPurify.sanitize(html)
  return html
})

function resolveUrl(u: string): string {
  if (!u) return ''
  if (u.startsWith('http://') || u.startsWith('https://')) return u
  if (u.startsWith('/')) return u
  return `/${u}`
}
</script>

<template>
  <div class="w-full" :data-role="message.role">
    <div class="w-full flex" :class="message.role === 'user' ? 'justify-end' : 'justify-start'">
      <div
        :class="[
          message.role === 'user'
            ? 'rounded-2xl px-4 py-3 bg-royal-100 text-gray-800 whitespace-pre-wrap shadow-sm'
            : message.error
            ? 'rounded-2xl px-4 py-3 bg-red-50 border border-red-200 text-red-600 whitespace-pre-wrap shadow-sm'
            : 'px-3 py-2 text-sm leading-relaxed text-gray-800',
          isWide ? 'max-w-3xl w-full' : 'max-w-2xl',
        ]"
      >
        <!-- 이미지 1장: 상단 히어로 배너 (답변 텍스트 위에 항상 위치) -->
        <div v-if="isAssistant && message.images?.length === 1" class="mb-4">
          <a
            :href="resolveUrl(message.images[0].url)"
            target="_blank"
            rel="noopener"
            class="block rounded-xl overflow-hidden border border-royal-100 shadow-sm"
          >
            <img
              :src="resolveUrl(message.images[0].url)"
              :alt="message.images[0].alt || ''"
              loading="lazy"
              class="w-full object-cover max-h-80"
              @error="($event.target as HTMLImageElement).style.display='none'"
            >
          </a>
        </div>
        <!-- 이미지 2장+: 그리드 -->
        <div v-else-if="isAssistant && (message.images?.length ?? 0) > 1" class="mb-3 grid grid-cols-2 md:grid-cols-3 gap-2">
          <a
            v-for="(img, i) in message.images"
            :key="i"
            :href="resolveUrl(img.url)"
            target="_blank"
            rel="noopener"
            class="block rounded-lg overflow-hidden border border-royal-50 hover:border-royal-200"
          >
            <img
              :src="resolveUrl(img.url)"
              :alt="img.alt || ''"
              loading="lazy"
              class="w-full h-32 object-cover"
              @error="($event.target as HTMLImageElement).style.display='none'"
            >
          </a>
        </div>

        <!-- ──────────────────────────────────────────────
             구조화 응답 (해설안내 등) — 마크다운보다 먼저 렌더
             ────────────────────────────────────────────── -->
        <div v-if="isAssistant && !message.error && message.structured" class="guide-container">
          <!-- 헤더: 궁능명(있을 때만) + 콘텐츠 종류 -->
          <h2 class="guide-heading">
            <span v-if="message.structured.palace_name">{{ message.structured.palace_name }}</span>
            <span class="guide-heading-sub">{{ message.structured.guide_type }}</span>
          </h2>

          <!-- ── [A] HTML 모드 — DB 원문 그대로 렌더 (운영사이트와 동일 구조) ── -->
          <div
            v-if="message.structured.mode === 'html'"
            class="guide-html"
            v-html="renderedStructuredHtml || '<div class=\'guide-empty\'>해설 안내 정보가 없습니다.</div>'"
          />

          <!-- ── [D] reservation_list — 예약 가능 상품 인라인 카드 ── -->
          <div
            v-else-if="message.structured.mode === 'reservation_list'"
            class="reservation-list"
          >
            <PanelReservationCard
              v-for="(it, i) in (message.structured.items ?? [])"
              :key="((it as any).res_idx as string) || i"
              :item="(it as any)"
              @select="(res_idx: string) => emit('panel-action', 'info', res_idx)"
              @go-form="(res_idx: string) => emit('panel-action', 'form', res_idx)"
            />
          </div>

          <!-- ── [E] reservation_info — AI 관람정보 답변 + 예약하기 버튼 ── -->
          <template v-else-if="message.structured.mode === 'reservation_info'">
            <div class="royal-md" v-html="renderedMarkdown" />
            <div class="mt-4">
              <button
                class="w-full py-2.5 rounded-xl bg-royal-500 text-white font-medium hover:bg-royal-600 transition-colors"
                @click="emit('panel-action', 'form', message.structured.res_idx || '')"
              >
                예약하기
              </button>
            </div>
          </template>

          <!-- ── [G] reservation_submitted — 예약 접수 완료 확인 카드 ── -->
          <template v-else-if="message.structured.mode === 'reservation_submitted'">
            <div class="reservation-submitted">
              <div class="reservation-submitted-check">✓</div>
              <div class="royal-md" v-html="renderedMarkdown" />
            </div>
          </template>

          <!-- ── [F] story_grid — 이야기 제목 그리드 + 클릭 시 본문 확장 ── -->
          <template v-else-if="message.structured.mode === 'story_grid'">
            <div class="story-grid">
              <button
                v-for="(it, i) in (message.structured.items ?? [])"
                :key="((it as any).idx as string) || i"
                type="button"
                class="story-tile"
                :class="{ 'story-tile--active': selectedStoryIdx === ((it as any).idx as string) }"
                @click="selectStory((it as any).idx as string)"
              >
                {{ (it as any).title }}
              </button>
            </div>
            <div v-if="selectedStory" class="story-detail">
              <h3 class="story-detail-title">{{ (selectedStory as any).title }}</h3>
              <div
                v-if="(selectedStory as any).images?.length"
                class="story-detail-images"
              >
                <a
                  v-for="(img, i) in (selectedStory as any).images"
                  :key="i"
                  :href="resolveUrl((img as any).url)"
                  target="_blank"
                  rel="noopener"
                  class="story-detail-image-wrap"
                >
                  <img
                    :src="resolveUrl((img as any).url)"
                    :alt="(img as any).alt || ''"
                    loading="lazy"
                    @error="($event.target as HTMLImageElement).style.display='none'"
                  >
                </a>
              </div>
              <p class="story-detail-body">
                {{ storyStreamedText }}<span v-if="storyStreaming" class="typing-cursor" />
              </p>
            </div>
          </template>

          <!-- ── [C] 큐레이션 모드 — LLM 요약 + 원문 아코디언 ── -->
          <template v-else-if="message.structured.mode === 'curated'">
            <div
              v-if="renderedCuratedSummary"
              class="royal-md guide-curated"
              v-html="renderedCuratedSummary"
            />
            <div v-else class="guide-empty">핵심 정보를 추출하지 못했습니다.</div>

            <details v-if="message.structured.html" class="guide-details">
              <summary>{{ message.structured.guide_type || '원문' }} 전체 보기</summary>
              <div class="guide-html" v-html="renderedStructuredHtml" />
            </details>
          </template>

          <!-- ── [B] sections 모드 — 타입별 커스텀 렌더 (기존 구조화 방식) ── -->
          <!-- 해설 정보가 아예 없는 경우 -->
          <div v-else-if="!message.structured.sections || message.structured.sections.length === 0"
               class="guide-empty">
            해설 안내 정보가 없습니다.
          </div>

          <!-- sections 순회 (궁능마다 개수·종류 달라도 자동 대응) -->
          <template v-else>
            <section v-for="(sec, idx) in message.structured.sections" :key="idx"
                     class="guide-section">
              <h3 v-if="sec.title" class="guide-section-title">{{ sec.title }}</h3>

              <!-- 1) 시간표 테이블 — 데스크톱: 표 / 모바일: 카드 리스트 -->
              <template v-if="sec.type === 'schedule_table'">
                <!-- 데스크톱 표 -->
                <div class="guide-table-wrap">
                  <table class="guide-table">
                    <thead>
                      <tr>
                        <th v-for="(h, hi) in (sec.data as any).headers || []" :key="hi">{{ h }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, ri) in (sec.data as any).rows || []" :key="ri">
                        <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <!-- 모바일 카드 리스트 (표가 좁을 때 자동 전환) -->
                <ul class="guide-table-cards">
                  <li v-for="(row, ri) in (sec.data as any).rows || []" :key="ri"
                      class="guide-table-card">
                    <div v-for="(cell, ci) in row" :key="ci" class="guide-table-card-row">
                      <span class="guide-table-card-label">{{ (sec.data as any).headers?.[ci] || '' }}</span>
                      <span class="guide-table-card-value">{{ cell }}</span>
                    </div>
                  </li>
                </ul>
                <!-- 비고 (schedule_table.note) -->
                <p v-if="(sec.data as any).note" class="guide-table-note">※ {{ (sec.data as any).note }}</p>
              </template>

              <!-- 2) 불릿 리스트 (관람 방법 등) -->
              <ul v-else-if="sec.type === 'bullet_list'" class="guide-bullets">
                <li v-for="(item, ii) in (sec.data as string[])" :key="ii">
                  <span class="guide-bullet-mark">✓</span>
                  <span>{{ item }}</span>
                </li>
              </ul>

              <!-- 3) 정보 카드 (집결장소/소요시간/문의처 등) -->
              <div v-else-if="sec.type === 'info_cards'" class="guide-cards">
                <div v-for="(card, ci) in (sec.data as any[])" :key="ci" class="guide-card">
                  <div class="guide-card-label">{{ card.label }}</div>
                  <div class="guide-card-value">{{ card.value }}</div>
                </div>
              </div>

              <!-- 4) 주의사항 박스 -->
              <div v-else-if="sec.type === 'warning_box'" class="guide-warning">
                <span class="guide-warning-icon">⚠</span>
                <span>{{ (sec.data as any).text }}</span>
              </div>

              <!-- 5) 연락처 리스트 (문의처 등) -->
              <ul v-else-if="sec.type === 'contact_list'" class="guide-contacts">
                <li v-for="(c, ci) in (sec.data as any[])" :key="ci" class="guide-contact">
                  <div class="guide-contact-name">{{ c.name }}</div>
                  <div class="guide-contact-meta">
                    <span v-if="c.phone" class="guide-contact-phone">☏ {{ c.phone }}</span>
                    <a
                      v-if="c.url"
                      :href="c.url"
                      target="_blank"
                      rel="noopener"
                      class="guide-contact-link"
                    >{{ c.url }}</a>
                  </div>
                </li>
              </ul>
            </section>
          </template>
        </div>

        <!-- 일반 마크다운 답변 (구조화 응답이 없거나 보조 reply 용) -->
        <div
          v-else-if="isAssistant && !message.error"
          class="royal-md"
          v-html="renderedMarkdown"
        />
        <div v-else-if="!isAssistant || message.error">{{ message.content }}</div>

        <div v-if="isAssistant && hasCandidates && message.stage" class="mt-3">
          <CandidateGroup
            :candidates="message.candidates!"
            :variant="candidateVariant"
            @pick="(code, label, hint) => emit('pick', code, message.stage!, label, hint)"
          />
        </div>

        <!-- RAG 소스 청크 토글 -->
        <details
          v-if="isAssistant && message.rag_sources && message.rag_sources.length > 0"
          class="rag-sources-details"
        >
          <summary>관련 문서 {{ message.rag_sources.length }}건 보기</summary>
          <div class="rag-sources-list">
            <div
              v-for="(src, i) in message.rag_sources"
              :key="i"
              class="rag-source-item"
            >
              <div class="rag-source-title">{{ src.title || '(제목 없음)' }}</div>
              <div class="rag-source-content">{{ src.content }}</div>
              <div v-if="src.score != null" class="rag-source-score">점수 {{ src.score.toFixed(3) }}</div>
            </div>
          </div>
        </details>

      </div>
    </div>
  </div>
</template>

<style>
.royal-md h1 {
  font-size: 1.1rem;
  font-weight: 700;
  color: #601421;
  margin: 0 0 0.75rem;
  line-height: 1.5;
}
.royal-md h2 {
  font-size: 1rem;
  font-weight: 600;
  color: #601421;
  margin: 0.75rem 0 0.5rem;
  border-bottom: 1px solid #E6DED0;
  padding-bottom: 0.25rem;
}
.royal-md h3 {
  font-size: 0.95rem;
  font-weight: 600;
  color: #374151;
  margin: 0.75rem 0 0.35rem;
}
.royal-md h4 {
  font-size: 0.9rem;
  font-weight: 600;
  color: #4b5563;
  margin: 0.6rem 0 0.3rem;
}
.royal-md p {
  margin: 0.3rem 0;
  line-height: 1.65;
}
.royal-md ul {
  list-style: disc;
  padding-left: 1.25rem;
  margin: 0.3rem 0;
}
.royal-md ol {
  list-style: decimal;
  padding-left: 1.5rem;
  margin: 0.3rem 0;
}
.royal-md li {
  margin: 0.15rem 0;
}
.royal-md strong {
  color: #1f2937;
  font-weight: 600;
}
.royal-md em {
  color: #6b7280;
  font-style: italic;
}
.royal-md a {
  color: #7A1F2B;
  text-decoration: underline;
}
.royal-md code {
  background: #FAF6EE;
  padding: 0 0.25rem;
  border-radius: 4px;
  font-family: ui-monospace, monospace;
  font-size: 0.85em;
}
.royal-md table {
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 0.85rem;
}
.royal-md th, .royal-md td {
  border: 1px solid #E6DED0;
  padding: 0.25rem 0.5rem;
}
.royal-md th {
  background: #FAF6EE;
  font-weight: 600;
}
.royal-md blockquote {
  border-left: 3px solid #E6DED0;
  padding-left: 0.75rem;
  color: #6b7280;
  margin: 0.5rem 0;
}
.royal-md img {
  max-width: 100%;
  border-radius: 8px;
  margin: 0.25rem 0;
}

/* ──────────────────────────────────────────────
   구조화 응답 (해설안내) — 섹션별 렌더링 스타일
   ────────────────────────────────────────────── */
.guide-container {
  font-size: 0.875rem;
  color: #1f2937;
}
.guide-heading {
  font-size: 1.05rem;
  font-weight: 700;
  color: #601421;
  margin: 0 0 0.75rem;
  padding-bottom: 0.35rem;
  border-bottom: 1px solid #E6DED0;
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}
.guide-heading-sub {
  font-size: 0.85rem;
  font-weight: 500;
  color: #6b7280;
}
.guide-empty {
  padding: 1rem;
  background: #f9fafb;
  border: 1px dashed #e5e7eb;
  border-radius: 8px;
  color: #6b7280;
  text-align: center;
}
.guide-section {
  margin: 0.75rem 0 1rem;
}
.guide-section-title {
  font-size: 0.92rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 0.45rem;
}

/* ── 1) 시간표 테이블 (데스크톱) ── */
.guide-table-wrap {
  overflow-x: auto;
  border: 1px solid #E6DED0;
  border-radius: 8px;
}
.guide-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.guide-table thead th {
  background: #FAF6EE;
  color: #601421;
  font-weight: 600;
  padding: 0.5rem 0.6rem;
  text-align: left;
  border-bottom: 1px solid #E6DED0;
  white-space: nowrap;
}
.guide-table tbody td {
  padding: 0.45rem 0.6rem;
  border-bottom: 1px solid #F5EBD8;
  vertical-align: top;
}
.guide-table tbody tr:nth-child(even) td {
  background: #FDFAF2;
}
.guide-table tbody tr:hover td {
  background: #FAF6EE;
}
.guide-table tbody tr:last-child td {
  border-bottom: none;
}

/* 모바일 카드 리스트 (표 숨기고 카드 표출) */
.guide-table-cards { display: none; }
@media (max-width: 640px) {
  .guide-table-wrap { display: none; }
  .guide-table-cards {
    display: block;
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .guide-table-card {
    background: #fff;
    border: 1px solid #E6DED0;
    border-radius: 8px;
    padding: 0.55rem 0.75rem;
    margin-bottom: 0.5rem;
  }
  .guide-table-card-row {
    display: flex;
    gap: 0.5rem;
    font-size: 0.82rem;
    padding: 0.15rem 0;
  }
  .guide-table-card-label {
    color: #601421;
    font-weight: 600;
    min-width: 4.5rem;
    flex-shrink: 0;
  }
  .guide-table-card-value {
    color: #1f2937;
    flex: 1;
  }
}

/* ── 2) 불릿 리스트 ── */
.guide-bullets {
  list-style: none;
  padding: 0;
  margin: 0;
}
.guide-bullets li {
  display: flex;
  gap: 0.5rem;
  padding: 0.25rem 0;
  line-height: 1.55;
}
.guide-bullet-mark {
  color: #7A1F2B;
  font-weight: 700;
  flex-shrink: 0;
  width: 1rem;
}

/* ── 3) 정보 카드 그리드 ── */
.guide-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.5rem;
}
.guide-card {
  background: #fff;
  border: 1px solid #E6DED0;
  border-radius: 10px;
  padding: 0.6rem 0.75rem;
  box-shadow: 0 1px 2px rgba(159, 18, 57, 0.04);
}
.guide-card-label {
  font-size: 0.72rem;
  color: #601421;
  font-weight: 600;
  margin-bottom: 0.15rem;
}
.guide-card-value {
  font-size: 0.85rem;
  color: #1f2937;
  line-height: 1.45;
  word-break: break-all;
}
@media (max-width: 640px) {
  .guide-cards { grid-template-columns: 1fr; }
}

/* ── 예약 가능 상품 인라인 카드 리스트 ── */
.reservation-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-top: 0.25rem;
}

/* ── 예약 접수 완료 확인 카드 ── */
.reservation-submitted {
  background: linear-gradient(180deg, #F5EBD8 0%, #FDFAF2 100%);
  border: 1px solid #D9C9A8;
  border-radius: 12px;
  padding: 1.1rem 1.25rem;
  display: flex;
  gap: 0.85rem;
  align-items: flex-start;
}
.reservation-submitted-check {
  flex: 0 0 auto;
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  background: #7A1F2B;
  color: #fff;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  line-height: 1;
}

/* ── 이야기 그리드 ── */
.story-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin: 0.25rem 0 1rem;
}
@media (min-width: 640px) {
  .story-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (min-width: 768px) {
  .story-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (min-width: 1024px) {
  .story-grid { grid-template-columns: repeat(5, minmax(0, 1fr)); }
}
.story-tile {
  background: #FAF6EE;
  border: 1px solid #E6DED0;
  border-radius: 10px;
  padding: 0.65rem 0.5rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: #1f2937;
  text-align: center;
  line-height: 1.3;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  min-height: 3.1rem;
}
.story-tile:hover {
  background: #F5EBD8;
  border-color: #D9C9A8;
}
.story-tile--active {
  background: #7A1F2B;
  border-color: #7A1F2B;
  color: #fff;
}
.story-detail {
  background: #fff;
  border: 1px solid #E6DED0;
  border-radius: 12px;
  padding: 1rem 1.15rem;
  margin-top: 0.25rem;
}
.story-detail-title {
  font-size: 1rem;
  font-weight: 700;
  color: #601421;
  margin: 0 0 0.5rem;
  border-bottom: 1px solid #E6DED0;
  padding-bottom: 0.4rem;
}
.story-detail-images {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.5rem;
  margin: 0.6rem 0;
}
.story-detail-image-wrap {
  display: block;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #F5EBD8;
}
.story-detail-image-wrap img {
  width: 100%;
  height: 140px;
  object-fit: cover;
  display: block;
}
.story-detail-body {
  font-size: 0.9rem;
  line-height: 1.7;
  color: #374151;
  white-space: pre-wrap;
  margin: 0.4rem 0 0;
}

/* ── schedule_table 비고 ── */
.guide-table-note {
  margin: 0.35rem 0 0;
  color: #6b7280;
  font-size: 0.78rem;
  line-height: 1.5;
}

/* ── 5) 연락처 리스트 ── */
.guide-contacts {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.5rem;
}
.guide-contact {
  background: #fff;
  border: 1px solid #E6DED0;
  border-radius: 10px;
  padding: 0.55rem 0.75rem;
}
.guide-contact-name {
  font-weight: 600;
  color: #601421;
  font-size: 0.88rem;
  margin-bottom: 0.2rem;
}
.guide-contact-meta {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  font-size: 0.8rem;
  color: #1f2937;
}
.guide-contact-phone {
  color: #4b5563;
}
.guide-contact-link {
  color: #7A1F2B;
  text-decoration: underline;
  word-break: break-all;
}

/* ── 4) 주의사항 박스 ── */
.guide-warning {
  display: flex;
  gap: 0.5rem;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-left: 3px solid #f59e0b;
  border-radius: 8px;
  padding: 0.6rem 0.75rem;
  color: #92400e;
  line-height: 1.55;
}
.guide-warning-icon {
  color: #f59e0b;
  font-weight: 700;
  flex-shrink: 0;
}

/* ──────────────────────────────────────────────
   HTML 모드 — 운영사이트(royal.khs.go.kr) CSS 클래스 매핑
   원문 table/rowspan/span.class 구조를 그대로 재현
   ────────────────────────────────────────────── */
.guide-html {
  font-size: 0.82rem;
  color: #1f2937;
}

/* 섹션 링크 네비 (상단 정규해설/특별관람/칠궁 등) */
.guide-html .info_box_wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0 0 0.75rem;
  padding: 0;
}
.guide-html .page_privacy_item {
  flex: 1 1 auto;
  background: #FAF6EE;
  border: 1px solid #E6DED0;
  border-radius: 10px;
  transition: background 0.15s;
}
.guide-html .page_privacy_item:hover { background: #F5EBD8; }
.guide-html .page_privacy_item a {
  display: block;
  padding: 0.45rem 0.75rem;
  color: #601421;
  font-weight: 600;
  text-align: center;
  text-decoration: none;
}
.guide-html .page_privacy_item .txt_wrap { color: inherit; }

/* 섹션 컨테이너 */
.guide-html .sub_con_section {
  margin: 0.75rem 0 1rem;
}
.guide-html .txt_section_tit {
  font-size: 0.95rem;
  font-weight: 700;
  color: #601421;
  padding-bottom: 0.3rem;
  margin: 0 0 0.5rem;
  border-bottom: 1px solid #E6DED0;
}

/* ──────────────────────────────────────────────
   정기휴일 카드 리스트 — holiday_list / holiday_item
   요일별 카드 2열 그리드 + 안내문 박스
   ────────────────────────────────────────────── */
.guide-html .holiday_list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.6rem;
  list-style: none;
  padding: 0;
  margin: 0.5rem 0;
}
.guide-html .holiday_item {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  background: #FAF6EE;
  border: 1px solid #E6DED0;
  border-radius: 10px;
  padding: 0.7rem 0.85rem;
}
/* 요일 아이콘 이미지는 외부 리소스라 깨질 수 있어 숨김 처리 */
.guide-html .holiday_item .img_wrap {
  display: none;
}
.guide-html .holiday_item .tit_wrap {
  font-weight: 700;
  color: #601421;
  font-size: 0.88rem;
  min-width: 3.2rem;
}
.guide-html .holiday_item .txt_wrap {
  color: #2B2927;
  font-size: 0.82rem;
  line-height: 1.5;
}
/* 안내 문구 박스 (※ 로 시작) */
.guide-html .info_txt {
  background: #FDFAF2;
  border-left: 3px solid #B89E50;
  border-radius: 0 8px 8px 0;
  padding: 0.55rem 0.85rem;
  margin: 0.55rem 0;
}
.guide-html .info_txt p {
  margin: 0.2rem 0;
  color: #4A3A28;
  font-size: 0.8rem;
  line-height: 1.55;
}

/* 표 (bd_table, mark_table 공용) */
.guide-html .table_wrap {
  overflow-x: auto;
  border: 1px solid #E6DED0;
  border-radius: 8px;
  margin: 0.25rem 0 0.75rem;
}
.guide-html table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}
.guide-html table caption {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}
.guide-html thead th {
  background: #FAF6EE;
  color: #601421;
  font-weight: 600;
  padding: 0.5rem 0.55rem;
  text-align: center;
  border-bottom: 1px solid #E6DED0;
  white-space: nowrap;
}
.guide-html tbody th {
  background: #FDFAF2;
  color: #601421;
  font-weight: 600;
  padding: 0.5rem 0.55rem;
  border-right: 1px solid #E6DED0;
  border-bottom: 1px solid #F5EBD8;
  text-align: center;
  vertical-align: middle;
}
.guide-html tbody td {
  padding: 0.45rem 0.55rem;
  border-bottom: 1px solid #F5EBD8;
  border-right: 1px solid #F5EBD8;
  vertical-align: middle;
  text-align: center;
}
.guide-html tbody td:last-child,
.guide-html tbody th:last-child { border-right: none; }
.guide-html tbody tr:last-child td,
.guide-html tbody tr:last-child th { border-bottom: none; }
.guide-html td.bdl { border-left: 1px solid #F5EBD8; }

/* pill 컨테이너 (한 셀 안에 여러 시간) */
.guide-html .t_inn_wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  justify-content: center;
  align-items: center;
}
.guide-html .t_inn_wrap.tal { justify-content: flex-start; }

/* 접근성 텍스트 (스크린리더 전용) — 시각 숨김 */
.guide-html .sr_only,
.guide-html em.sr_only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* ── pill 색상 3종 (운영사이트 클래스 그대로 매핑) ── */
/* 관리소 해설사 — 노란 테두리 + 흰 배경 */
.guide-html .time_gray {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.55rem;
  background: #fff;
  color: #b45309;
  border: 1px solid #fcd34d;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 500;
  white-space: nowrap;
}
/* 우리궁궐지킴이 — 분홍 배경 */
.guide-html .time_red {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.55rem;
  background: #fce7f3;
  color: #be185d;
  border: 1px solid #fbcfe8;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 500;
  white-space: nowrap;
}
/* 궁궐길라잡이 — 보라 배경 */
.guide-html .time_blue {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.55rem;
  background: #ede9fe;
  color: #6d28d9;
  border: 1px solid #ddd6fe;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 500;
  white-space: nowrap;
}

/* 회색(부가 설명) 텍스트 */
.guide-html .c_gray70 {
  display: block;
  margin-top: 0.4rem;
  color: #6b7280;
  font-size: 0.75rem;
  line-height: 1.45;
}

/* ──────────────────────────────────────────────
   큐레이션 모드 — LLM 요약 + 원문 아코디언
   ────────────────────────────────────────────── */
.guide-curated {
  font-size: 0.88rem;
  line-height: 1.65;
  color: #1f2937;
}
.guide-details {
  margin-top: 0.75rem;
  border-top: 1px dashed #E6DED0;
  padding-top: 0.4rem;
}
.guide-details > summary {
  cursor: pointer;
  color: #601421;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 0.35rem 0.25rem;
  list-style: none;
  user-select: none;
}
.guide-details > summary::-webkit-details-marker { display: none; }
.guide-details > summary::before {
  content: '▸ ';
  display: inline-block;
  margin-right: 0.25rem;
  transition: transform 0.15s;
}
.guide-details[open] > summary::before {
  transform: rotate(90deg);
}
.guide-details[open] > summary {
  border-bottom: 1px solid #F5EBD8;
  margin-bottom: 0.5rem;
}

/* 일반 텍스트 박스들 (바깥 목록·설명) */
.guide-html p { margin: 0.35rem 0; line-height: 1.55; }
.guide-html ul, .guide-html ol { padding-left: 1.25rem; margin: 0.35rem 0; }
.guide-html li { margin: 0.15rem 0; line-height: 1.55; }
.guide-html a { color: #7A1F2B; text-decoration: underline; }
.guide-html strong { color: #1f2937; font-weight: 600; }
.guide-html img { max-width: 100%; height: auto; border-radius: 8px; margin: 0.35rem 0; }

/* ── RAG 소스 청크 토글 ── */
.rag-sources-details {
  margin-top: 0.6rem;
  border-top: 1px dashed #E6DED0;
  padding-top: 0.35rem;
}
.rag-sources-details > summary {
  cursor: pointer;
  color: #601421;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.25rem 0.1rem;
  list-style: none;
  user-select: none;
  opacity: 0.8;
}
.rag-sources-details > summary::-webkit-details-marker { display: none; }
.rag-sources-details > summary::before {
  content: '▸ ';
  margin-right: 0.2rem;
  display: inline-block;
  transition: transform 0.15s;
}
.rag-sources-details[open] > summary::before { transform: rotate(90deg); }
.rag-sources-list {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.rag-source-item {
  background: #FDFAF2;
  border: 1px solid #E6DED0;
  border-radius: 8px;
  padding: 0.55rem 0.75rem;
}
.rag-source-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: #601421;
  margin-bottom: 0.25rem;
}
.rag-source-content {
  font-size: 0.76rem;
  color: #374151;
  line-height: 1.55;
  white-space: pre-wrap;
  max-height: 6rem;
  overflow-y: auto;
}
.rag-source-score {
  margin-top: 0.2rem;
  font-size: 0.7rem;
  color: #9ca3af;
  text-align: right;
}

/* ── 타이프라이터 커서 */
.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background: #601421;
  margin-left: 2px;
  vertical-align: middle;
  border-radius: 1px;
  animation: typing-blink 0.75s step-end infinite;
}
@keyframes typing-blink {
  50% { opacity: 0; }
}
</style>
