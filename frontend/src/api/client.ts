import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,   // sends HttpOnly cookies
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: inject local user settings headers ───────────────────
api.interceptors.request.use(
  (config) => {
    const apiKey = localStorage.getItem('gemini_api_key')
    const model = localStorage.getItem('gemini_model')
    const whisperSize = localStorage.getItem('whisper_size')

    if (apiKey) {
      config.headers['X-Gemini-API-Key'] = apiKey
    }
    if (model) {
      config.headers['X-Gemini-Model'] = model
    }
    if (whisperSize) {
      config.headers['X-Whisper-Model-Size'] = whisperSize
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Response interceptor: silent JWT refresh on 401 ──────────────────────────
let isRefreshing = false
let refreshQueue: Array<(ok: boolean) => void> = []

// URLs that should NEVER trigger a token refresh attempt
const AUTH_BYPASS = ['/auth/refresh', '/auth/login', '/auth/register', '/auth/me']

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const url: string = originalRequest?.url || ''

    const shouldBypass = AUTH_BYPASS.some((path) => url.includes(path))

    if (error.response?.status === 401 && !originalRequest._retry && !shouldBypass) {
      originalRequest._retry = true

      if (isRefreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve, reject) => {
          refreshQueue.push((ok) => {
            if (ok) resolve(api(originalRequest))
            else reject(error)
          })
        })
      }

      isRefreshing = true

      try {
        await api.post('/api/auth/refresh')
        refreshQueue.forEach((cb) => cb(true))
        refreshQueue = []
        isRefreshing = false
        return api(originalRequest)
      } catch {
        // Refresh failed — clear queue and let the store handle redirect
        refreshQueue.forEach((cb) => cb(false))
        refreshQueue = []
        isRefreshing = false
        // Dynamically import store to avoid circular deps — clears user without page reload
        import('@/store/authStore').then(({ useAuthStore }) => {
          useAuthStore.getState().logout()
        })
      }
    }

    return Promise.reject(error)
  }
)
