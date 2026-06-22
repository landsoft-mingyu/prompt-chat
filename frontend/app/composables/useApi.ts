// ──────────────────────────────────────────────
// useApi — 백엔드 호출 래퍼 (Envelope 해제)
// - request     : JSON 요청/응답
// - requestForm : multipart/form-data (파일 업로드용)
// ──────────────────────────────────────────────
import type { Envelope } from '~/types/api'

export interface ApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  query?: Record<string, unknown>
}

export function useApi() {
  const config = useRuntimeConfig()
  const base = config.public.apiBase as string

  // ── JSON 요청 전용 ──────────────────────────────
  async function request<T>(path: string, opts: ApiOptions = {}): Promise<T> {
    const envelope = await $fetch<Envelope<T>>(`${base}${path}`, {
      method: opts.method ?? (opts.body ? 'POST' : 'GET'),
      body: opts.body as Record<string, unknown> | undefined,
      query: opts.query,
      headers: { 'Content-Type': 'application/json' },
    })

    if (!envelope.success || envelope.data === null) {
      const msg = envelope.error?.message ?? '요청 처리 중 오류가 발생했습니다.'
      throw new Error(msg)
    }
    return envelope.data
  }

  // ── multipart/form-data 요청 전용 (파일 업로드) ─────────
  // Content-Type 은 브라우저가 boundary 포함하여 자동 설정하도록 지정하지 않음
  async function requestForm<T>(path: string, formData: FormData): Promise<T> {
    const envelope = await $fetch<Envelope<T>>(`${base}${path}`, {
      method: 'POST',
      body: formData,
    })

    if (!envelope.success || envelope.data === null) {
      const msg = envelope.error?.message ?? '요청 처리 중 오류가 발생했습니다.'
      throw new Error(msg)
    }
    return envelope.data
  }

  async function fetchHealth(): Promise<{ status: string } & Record<string, unknown>> {
    const resp = await fetch('/health')
    if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`)
    return resp.json()
  }

  async function fetchRagHealth(): Promise<{ status: string; embedding_service: unknown }> {
    const resp = await fetch('/api/rag/health')
    if (!resp.ok) throw new Error(`RAG health check failed: ${resp.status}`)
    return resp.json()
  }

  return { request, requestForm, fetchHealth, fetchRagHealth }
}
