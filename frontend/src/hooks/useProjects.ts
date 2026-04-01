import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: api.projects.list,
    staleTime: 5 * 60_000,
  })
}
