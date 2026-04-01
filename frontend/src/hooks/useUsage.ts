import { useQuery } from '@tanstack/react-query'
import { api, type UsageFilters } from '../lib/api'

export function useUsage(filters: UsageFilters = {}) {
  return useQuery({
    queryKey: ['usage', 'list', filters],
    queryFn: () => api.usage.list({ ...filters, limit: 1000 }),
    staleTime: 60_000,
    refetchInterval: 30_000,
  })
}
