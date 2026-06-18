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
