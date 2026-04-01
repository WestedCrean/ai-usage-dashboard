import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/layout/Layout'
import { DashboardPage } from './pages/DashboardPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  const [filterOpen, setFilterOpen] = useState(false)

  return (
    <QueryClientProvider client={queryClient}>
      <Layout onFilterToggle={() => setFilterOpen(v => !v)}>
        <DashboardPage
          filterOpen={filterOpen}
          onFilterClose={() => setFilterOpen(false)}
        />
      </Layout>
    </QueryClientProvider>
  )
}
