/**
 * useRealtimeVoice — React hook for the real-time voice pipeline.
 *
 * Manages:
 * - AudioContext + AudioWorklet (16kHz, mono PCM capture)
 * - WebSocket connection to /api/ws/realtime
 * - State: transcript, answer tokens, connection status
 * - Auto-reconnect with exponential backoff
 * - Waveform amplitude data for visualizer
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { getApiUrl } from '@/api/client'
import { useInterviewStore } from '@/store/interviewStore'

// ── Types ────────────────────────────────────────────────────────────────────

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'
export type VoicePhase =
  | 'idle'
  | 'listening'
  | 'detecting'    // question keyword found — waiting for silence/confirmation
  | 'generating'   // Gemini is streaming
  | 'done'

export interface RealtimeVoiceState {
  connectionState: ConnectionState
  phase: VoicePhase
  liveTranscript: string
  currentAnswer: string
  isListening: boolean
  isGenerating: boolean
  firstTokenLatency: number | null
  totalLatency: number | null
  amplitude: number              // 0-1, for waveform visualizer
  error: string | null
}

export interface RealtimeVoiceActions {
  connect: () => Promise<void>
  disconnect: () => void
  startListening: () => Promise<void>
  stopListening: () => void
  sendTextQuestion: (text: string) => void
  resetAnswer: () => void
}

// ── Constants ─────────────────────────────────────────────────────────────────
const SAMPLE_RATE = 16_000
const MAX_RECONNECT_ATTEMPTS = 5
const RECONNECT_BASE_DELAY_MS = 1000

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useRealtimeVoice(): RealtimeVoiceState & RealtimeVoiceActions {
  // State
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const [phase, setPhase] = useState<VoicePhase>('idle')
  const [liveTranscript, setLiveTranscript] = useState('')
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [firstTokenLatency, setFirstTokenLatency] = useState<number | null>(null)
  const [totalLatency, setTotalLatency] = useState<number | null>(null)
  const [amplitude, setAmplitude] = useState(0)
  const [error, setError] = useState<string | null>(null)

  // Refs (stable across renders)
  const wsRef = useRef<WebSocket | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animFrameRef = useRef<number>(0)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isListeningRef = useRef(false)
  const answerAccRef = useRef('')   // accumulates tokens for the current answer

  // ── WebSocket connection ─────────────────────────────────────────────────

  const buildWsUrl = useCallback(async () => {
    const apiUrl = getApiUrl()
    const wsBase = apiUrl.replace(/^http/, 'ws')
    const apiKey = localStorage.getItem('gemini_api_key') || ''
    const model = localStorage.getItem('gemini_model') || ''
    const sessionId = useInterviewStore.getState().sessionId || ''
    let tokenParam = ''
    if (window.electronAPI?.auth) {
      try {
        const tokens = await window.electronAPI.auth.getTokens()
        if (tokens?.access_token) {
          tokenParam = `&token=${encodeURIComponent(tokens.access_token)}`
        }
      } catch (e) {
        console.warn('Failed to retrieve auth tokens for WebSocket url:', e)
      }
    }
    return `${wsBase}/api/ws/realtime?api_key=${encodeURIComponent(apiKey)}&model=${encodeURIComponent(model)}&session_id=${encodeURIComponent(sessionId)}${tokenParam}`
  }, [])

  const handleWsMessage = useCallback((event: MessageEvent) => {
    let msg: Record<string, unknown>
    try {
      msg = JSON.parse(event.data as string)
    } catch {
      return
    }

    const type = msg.type as string

    switch (type) {
      case 'ready':
        setConnectionState('connected')
        setError(null)
        reconnectAttemptsRef.current = 0
        break

      case 'transcript_partial':
        setLiveTranscript(msg.text as string)
        setPhase('detecting')
        break

      case 'transcript_final':
        setLiveTranscript(msg.text as string)
        break

      case 'answer_start':
        answerAccRef.current = ''
        setCurrentAnswer('')
        setFirstTokenLatency(null)
        setTotalLatency(null)
        setPhase('generating')
        break

      case 'answer_restart':
        // New transcript triggered a restart — clear current answer
        answerAccRef.current = ''
        setCurrentAnswer('')
        setFirstTokenLatency(null)
        setPhase('generating')
        break

      case 'answer_first_token':
        setFirstTokenLatency(msg.latency_ms as number)
        break

      case 'answer_token': {
        const token = msg.token as string
        answerAccRef.current += token
        setCurrentAnswer(answerAccRef.current)
        break
      }

      case 'answer_done':
        setTotalLatency(msg.latency_ms as number)
        setPhase('done')
        break

      case 'error':
        setError(msg.detail as string)
        setPhase('idle')
        break

      case 'pong':
        break
    }
  }, [])

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return

    setConnectionState('connecting')
    setError(null)

    try {
      const wsUrl = await buildWsUrl()
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        // 'ready' message from server will set state to 'connected'
      }

      ws.onmessage = handleWsMessage

      ws.onerror = () => {
        setConnectionState('error')
        setError('Connection error')
      }

      ws.onclose = (ev) => {
        setConnectionState('disconnected')
        if (isListeningRef.current) {
          // Unexpected close — attempt reconnect
          const attempts = reconnectAttemptsRef.current
          if (attempts < MAX_RECONNECT_ATTEMPTS) {
            const delay = RECONNECT_BASE_DELAY_MS * Math.pow(2, attempts)
            reconnectAttemptsRef.current++
            reconnectTimerRef.current = setTimeout(() => connect(), delay)
          } else {
            setError('Connection lost. Please reconnect.')
          }
        }
      }
    } catch (e) {
      setConnectionState('error')
      setError('Failed to open WebSocket')
    }
  }, [buildWsUrl, handleWsMessage])

  const disconnect = useCallback(() => {
    isListeningRef.current = false
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
    }
    wsRef.current?.close()
    wsRef.current = null
    setConnectionState('disconnected')
    setPhase('idle')
  }, [])

  // ── Audio capture ────────────────────────────────────────────────────────

  const startListening = useCallback(async () => {
    if (isListeningRef.current) return

    // Ensure WS is open
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      await connect()
      // Wait for connection to establish
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('Connection timeout')), 5000)
        const check = setInterval(() => {
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            clearInterval(check)
            clearTimeout(timeout)
            resolve()
          }
        }, 100)
      })
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: SAMPLE_RATE,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      })
      streamRef.current = stream

      // Create AudioContext at target sample rate
      const audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE })
      audioCtxRef.current = audioCtx

      // Load AudioWorklet module — use URL relative to the page
      const workletUrl = new URL('../worklets/audio-processor.js', import.meta.url)
      await audioCtx.audioWorklet.addModule(workletUrl.href)

      const source = audioCtx.createMediaStreamSource(stream)

      // Analyser for amplitude visualisation
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 256
      analyserRef.current = analyser

      // AudioWorkletNode
      const workletNode = new AudioWorkletNode(audioCtx, 'audio-processor')
      workletNodeRef.current = workletNode

      // Receive PCM batches from worklet thread
      workletNode.port.onmessage = (e: MessageEvent) => {
        if (e.data?.type !== 'pcm') return
        const ws = wsRef.current
        if (!ws || ws.readyState !== WebSocket.OPEN) return

        // Convert ArrayBuffer → base64
        const pcmBuffer = e.data.buffer as ArrayBuffer
        const bytes = new Uint8Array(pcmBuffer)
        let binary = ''
        for (let i = 0; i < bytes.length; i++) {
          binary += String.fromCharCode(bytes[i])
        }
        const b64 = btoa(binary)
        ws.send(JSON.stringify({ type: 'audio_chunk', data: b64, sampleRate: SAMPLE_RATE }))
      }

      source.connect(analyser)
      source.connect(workletNode)
      workletNode.connect(audioCtx.destination) // required for worklet to process

      isListeningRef.current = true
      setPhase('listening')

      // Start amplitude animation loop
      const drawAmplitude = () => {
        if (!isListeningRef.current) return
        const dataArr = new Uint8Array(analyser.frequencyBinCount)
        analyser.getByteFrequencyData(dataArr)
        const avg = dataArr.reduce((a, b) => a + b, 0) / dataArr.length
        setAmplitude(avg / 255)
        animFrameRef.current = requestAnimationFrame(drawAmplitude)
      }
      animFrameRef.current = requestAnimationFrame(drawAmplitude)

    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Microphone access failed'
      setError(msg)
      setPhase('idle')
    }
  }, [connect])

  const stopListening = useCallback(() => {
    isListeningRef.current = false
    cancelAnimationFrame(animFrameRef.current)
    setAmplitude(0)
    setPhase(currentAnswer !== '' ? 'done' : 'idle')

    // Signal end of stream to backend
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end_stream' }))
    }

    // Stop audio tracks
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null

    workletNodeRef.current?.port.postMessage('stop')
    workletNodeRef.current?.disconnect()
    workletNodeRef.current = null

    audioCtxRef.current?.close()
    audioCtxRef.current = null
  }, [currentAnswer])

  const sendTextQuestion = useCallback((text: string) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'text_question', text }))
  }, [])

  const resetAnswer = useCallback(() => {
    answerAccRef.current = ''
    setCurrentAnswer('')
    setLiveTranscript('')
    setFirstTokenLatency(null)
    setTotalLatency(null)
    setPhase(isListeningRef.current ? 'listening' : 'idle')
  }, [])

  // ── Cleanup on unmount ───────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      isListeningRef.current = false
      cancelAnimationFrame(animFrameRef.current)
      streamRef.current?.getTracks().forEach((t) => t.stop())
      audioCtxRef.current?.close()
      wsRef.current?.close()
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
    }
  }, [])

  return {
    connectionState,
    phase,
    liveTranscript,
    currentAnswer,
    isListening: isListeningRef.current && phase !== 'idle',
    isGenerating: phase === 'generating',
    firstTokenLatency,
    totalLatency,
    amplitude,
    error,
    connect,
    disconnect,
    startListening,
    stopListening,
    sendTextQuestion,
    resetAnswer,
  }
}
