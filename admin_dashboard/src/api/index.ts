// The app's single API client, wired to the session store.
// The store is looked up inside each callback, never at import time (the store imports this file).
import { useSessionStore } from '../stores/session'
import { createApiClient } from './client'

export const apiBaseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export const api = createApiClient({
  baseUrl: apiBaseUrl,
  getAccessToken: () => useSessionStore().accessToken,
  refresh: () => useSessionStore().refresh(),
  onAuthLost: () => useSessionStore().expire(),
})
