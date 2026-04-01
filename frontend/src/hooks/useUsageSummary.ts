import { useQuery } from '@tanstack/react-query'
import { api, type UsageFilters } from '../lib/api'

export function useUsageSummary(filters: UsageFilters = {}) {
  return useQuery({
    queryKey: ['usage', 'summary', filters],
    queryFn: () => api.usage.summary(filters),
    staleTime: 60_000,
    refetchInterval: 30_000,
  })
}
