const BASE = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

// ── Types ──────────────────────────────────────────────────────────────────────

export interface Model {
  id: number
  name: string
  provider: string
  cost_per_input_token: number
  cost_per_output_token: number
}

export interface Project {
  id: number
  name: string
  team: string
  description?: string
}

export interface UsageRecord {
  id: number
  model_id: number
  project_id: number
  timestamp: string
  input_tokens: number
  output_tokens: number
  latency_ms?: number
  success: boolean
  cost: number
}

export interface UsageSummary {
  total_calls: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_cost: number
  avg_latency_ms: number | null
  success_rate: number
}

export interface UsageFilters {
  model?: string
  project?: string
  team?: string
  from?: string
  to?: string
  skip?: number
  limit?: number
}

// ── Endpoints ─────────────────────────────────────────────────────────────────

function buildQuery(params: Record<string, string | number | undefined>): string {
  const q = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&')
  return q ? `?${q}` : ''
}

export const api = {
  models: {
    list: () => request<Model[]>('/api/v1/models'),
    create: (body: Omit<Model, 'id'>) =>
      request<Model>('/api/v1/models', { method: 'POST', body: JSON.stringify(body) }),
  },

  projects: {
    list: () => request<Project[]>('/api/v1/projects'),
    create: (body: Omit<Project, 'id'>) =>
      request<Project>('/api/v1/projects', { method: 'POST', body: JSON.stringify(body) }),
  },

  usage: {
    list: (filters: UsageFilters = {}) =>
      request<UsageRecord[]>(`/api/v1/usage${buildQuery(filters as Record<string, string | number | undefined>)}`),
    summary: (filters: UsageFilters = {}) =>
      request<UsageSummary>(`/api/v1/usage/summary${buildQuery(filters as Record<string, string | number | undefined>)}`),
    create: (body: Omit<UsageRecord, 'id'>) =>
      request<UsageRecord>('/api/v1/usage', { method: 'POST', body: JSON.stringify(body) }),
  },
}
