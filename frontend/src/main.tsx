import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { normalizeApiError } from './lib/apiError'
import { staleTime } from './lib/queryKeys'
import { RealtimeProvider } from './providers/RealtimeProvider'
import './index.css'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: staleTime.reportDetail,
      retry: (failureCount, error) =>
        failureCount < 2 && normalizeApiError(error).retryable,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <RealtimeProvider>
          <App />
        </RealtimeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
