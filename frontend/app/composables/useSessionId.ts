const SESSION_KEY = 'prompt_chat_session_id'

function generateId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}

export function useSessionId() {
  function getOrCreate(): string {
    if (!import.meta.client) return ''
    let id = localStorage.getItem(SESSION_KEY)
    if (!id) {
      id = generateId()
      localStorage.setItem(SESSION_KEY, id)
    }
    return id
  }

  function reset(): string {
    if (!import.meta.client) return ''
    const id = generateId()
    localStorage.setItem(SESSION_KEY, id)
    return id
  }

  return { getOrCreate, reset }
}
