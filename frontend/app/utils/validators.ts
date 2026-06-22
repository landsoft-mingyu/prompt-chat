// ──────────────────────────────────────────────
// 입력 검증 유틸 — 이메일 / 휴대폰 / 이름 / 파일
// ──────────────────────────────────────────────

export const EMAIL_RE = /^[_0-9a-zA-Z-]+(\.[_0-9a-zA-Z-]+)*@[0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*$/
export const KR_PHONE_RE = /^01(?:0|1|[6-9])[-]?\d{3,4}[-]?\d{4}$/
export const NAME_RE = /^[가-힣a-zA-Z\s]{1,20}$/

export function isValidEmail(v: string): boolean {
  return EMAIL_RE.test(v.trim())
}

export function normalizePhone(v: string): string {
  return v.replace(/\s/g, '')
}

export function isValidPhone(v: string): boolean {
  const n = normalizePhone(v)
  const digitsOnly = n.replace(/-/g, '')
  if (/^01(?:0|1|[6-9])\d{7,8}$/.test(digitsOnly)) return true
  return KR_PHONE_RE.test(n)
}

export function isValidName(v: string): boolean {
  const t = v.trim()
  if (t.length < 1 || t.length > 20) return false
  return NAME_RE.test(t)
}

export const MAX_FILE_BYTES = 10 * 1024 * 1024

export function isValidFileSize(file: File | null): boolean {
  if (!file) return true
  return file.size <= MAX_FILE_BYTES
}
