import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,   // sends HttpOnly cookies
  headers: { 'Content-Type': 'application/json' },
})

let isRefreshing = false
let failedQueue: Array<{resolve: (value?: unknown) => void, reject: (reason?: any) => void}> = []

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

api.interceptors.request.use(
  async (config) => {
    const apiKey = localStorage.getItem('gemini_api_key')
    const model = localStorage.getItem('gemini_model')
    const whisperSize = localStorage.getItem('whisper_size')

    if (apiKey) config.headers['X-Gemini-API-Key'] = apiKey
    if (model) config.headers['X-Gemini-Model'] = model
    if (whisperSize) config.headers['X-Whisper-Model-Size'] = whisperSize

    // Inject JWT Token
    if (window.electronAPI?.auth) {
      const tokens = await window.electronAPI.auth.getTokens()
      if (tokens?.access_token) {
        config.headers['Authorization'] = `Bearer ${tokens.access_token}`
      }
    }
    
    return config
  },
  (error) => Promise.reject(error)
)

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers['Authorization'] = 'Bearer ' + token
          return api(originalRequest)
        }).catch(err => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        if (!window.electronAPI?.auth) throw new Error('No electron API')
        const tokens = await window.electronAPI.auth.getTokens()
        if (!tokens?.refresh_token) throw new Error('No refresh token')
        
        const { data } = await axios.post(`${API_URL}/api/auth/desktop/refresh`, {
          refresh_token: tokens.refresh_token
        })
        
        await window.electronAPI.auth.setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          user_id: tokens.user_id
        })
        
        api.defaults.headers.common['Authorization'] = 'Bearer ' + data.access_token
        originalRequest.headers['Authorization'] = 'Bearer ' + data.access_token
        
        processQueue(null, data.access_token)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        if (window.electronAPI?.auth) {
          await window.electronAPI.auth.clearTokens()
          // Optional: redirect to login
          window.location.hash = '#/auth'
        }
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    return Promise.reject(error)
  }
)



export const getApiUrl = () => API_URL

export interface StreamCallbacks {
  onInfo?: (data: any) => void
  onToken?: (token: string) => void
  onDone?: (data: any) => void
  onError?: (err: string) => void
}

export async function streamPost(
  path: string,
  body: any,
  callbacks: StreamCallbacks
): Promise<void> {
  const apiKey = localStorage.getItem('gemini_api_key') || ''
  const model = localStorage.getItem('gemini_model') || ''
  const whisperSize = localStorage.getItem('whisper_size') || ''

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 15000)

  try {
    const response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Gemini-API-Key': apiKey,
        'X-Gemini-Model': model,
        'X-Whisper-Model-Size': whisperSize,
      },
      body: JSON.stringify(body),
      credentials: 'include',
      signal: controller.signal,
    })
    
    clearTimeout(timeoutId)

    if (!response.ok) {
      const errJson = await response.json().catch(() => ({}))
      throw new Error(errJson.detail || `HTTP error! Status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('Response body reader not available')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue

        if (trimmed.startsWith('data: ')) {
          const rawData = trimmed.slice(6)
          if (rawData === '[DONE]') {
            continue
          }

          try {
            const parsed = JSON.parse(rawData)
            if (parsed.event === 'info' && callbacks.onInfo) {
              callbacks.onInfo(parsed.data)
            } else if (parsed.event === 'token' && callbacks.onToken) {
              callbacks.onToken(parsed.data)
            } else if (parsed.event === 'done' && callbacks.onDone) {
              callbacks.onDone(parsed.data)
            } else if (parsed.event === 'error' && callbacks.onError) {
              callbacks.onError(parsed.detail || 'Stream error')
            }
          } catch (e) {
            console.error('Failed to parse stream line:', trimmed, e)
          }
        }
      }
    }
  } catch (err: any) {
    clearTimeout(timeoutId)
    const errorMsg = err.name === 'AbortError' 
      ? 'Request timed out (backend is unresponsive)' 
      : (err.message || 'Stream connection failed')
      
    if (callbacks.onError) {
      callbacks.onError(errorMsg)
    } else {
      throw new Error(errorMsg)
    }
  }
}
