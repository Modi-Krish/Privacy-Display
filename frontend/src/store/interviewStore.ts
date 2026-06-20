import { create } from 'zustand'
import { api, streamPost } from '@/api/client'

export interface ChunkView {
  text: string
  source: string
  section: string
  score: number
}

export interface InterviewTurn {
  question_id: string
  question_text: string
  category: string
  category_confidence: number
  retrieved_context: ChunkView[]
  generated_prompt: string
  answer: string
  confidence_score: number
  transcription_confidence: number | null
  is_personalized: boolean
  latency_ms: number
}

export type RecordingState = 'idle' | 'recording' | 'processing' | 'done' | 'error'

interface InterviewState {
  sessionId: string | null
  isSessionActive: boolean
  recordingState: RecordingState

  // Interaction mode
  realtimeMode: boolean

  // Current turn
  currentTurn: InterviewTurn | null
  error: string | null

  // Session history (shared between both modes)
  history: InterviewTurn[]

  // Actions
  startSession: () => Promise<void>
  endSession: () => Promise<void>
  submitAudio: (blob: Blob) => Promise<void>
  submitText: (question: string) => Promise<void>
  setRecordingState: (state: RecordingState) => void
  clearCurrentTurn: () => void
  clearError: () => void
  setRealtimeMode: (enabled: boolean) => void
  /** Called by RealtimeVoicePanel when a real-time turn completes */
  addRealtimeTurn: (question: string, answer: string, latencyMs: number) => void
}

const blobToBase64 = (blob: Blob): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = reader.result as string
      // Strip data URL prefix: "data:audio/webm;base64,..."
      resolve(result.split(',')[1])
    }
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })

export const useInterviewStore = create<InterviewState>((set, get) => ({
  sessionId: null,
  isSessionActive: false,
  recordingState: 'idle',
  realtimeMode: false,
  currentTurn: null,
  error: null,
  history: [],

  startSession: async () => {
    if (!navigator.onLine) {
      throw new Error('No internet connection. REAI requires an active connection to start a session.')
    }
    const { data } = await api.post('/api/interview/start')
    set({ sessionId: data.session_id, isSessionActive: true, history: [], currentTurn: null })
  },

  endSession: async () => {
    const { sessionId } = get()
    if (!sessionId) return
    await api.post('/api/interview/end', { session_id: sessionId }).catch(() => {})
    set({ sessionId: null, isSessionActive: false, recordingState: 'idle' })
  },

  submitAudio: async (blob) => {
    const { sessionId } = get()
    if (!sessionId) return
    set({ recordingState: 'processing', error: null, currentTurn: null })
    try {
      const audio_b64 = await blobToBase64(blob)
      let currentTurnAccumulator: InterviewTurn | null = null
      
      await streamPost(
        '/api/interview/question/stream',
        {
          session_id: sessionId,
          audio_b64,
        },
        {
          onInfo: (info) => {
            const initialTurn: InterviewTurn = {
              question_id: info.question_id,
              question_text: info.question_text || '🎙 Audio Question',
              category: 'Technical',
              category_confidence: 1.0,
              retrieved_context: info.retrieved_context,
              generated_prompt: info.generated_prompt,
              answer: '',
              confidence_score: 0.0,
              transcription_confidence: null,
              is_personalized: info.retrieved_context.length > 0,
              latency_ms: 0,
            }
            currentTurnAccumulator = initialTurn
            set({ currentTurn: initialTurn })
          },
          onToken: (token) => {
            if (currentTurnAccumulator) {
              currentTurnAccumulator.answer += token
              set({ currentTurn: { ...currentTurnAccumulator } })
            }
          },
          onDone: (done) => {
            if (currentTurnAccumulator) {
              currentTurnAccumulator.category = done.category
              currentTurnAccumulator.category_confidence = done.category_confidence
              currentTurnAccumulator.confidence_score = done.confidence_score
              currentTurnAccumulator.is_personalized = done.is_personalized
              currentTurnAccumulator.latency_ms = done.latency_ms
              
              const finalTurn = { ...currentTurnAccumulator }
              set((s) => ({
                currentTurn: finalTurn,
                history: [...s.history, finalTurn],
                recordingState: 'done',
              }))
            }
          },
          onError: (err) => {
            set({ error: err, recordingState: 'error' })
          },
        }
      )
    } catch (err: any) {
      set({
        error: err.message || 'Processing failed',
        recordingState: 'error',
      })
    }
  },

  submitText: async (question) => {
    const { sessionId } = get()
    if (!sessionId) return
    set({ recordingState: 'processing', error: null, currentTurn: null })
    try {
      let currentTurnAccumulator: InterviewTurn | null = null
      
      await streamPost(
        '/api/interview/question/stream',
        {
          session_id: sessionId,
          question,
        },
        {
          onInfo: (info) => {
            const initialTurn: InterviewTurn = {
              question_id: info.question_id,
              question_text: info.question_text || question,
              category: 'Technical',
              category_confidence: 1.0,
              retrieved_context: info.retrieved_context,
              generated_prompt: info.generated_prompt,
              answer: '',
              confidence_score: 0.0,
              transcription_confidence: null,
              is_personalized: info.retrieved_context.length > 0,
              latency_ms: 0,
            }
            currentTurnAccumulator = initialTurn
            set({ currentTurn: initialTurn })
          },
          onToken: (token) => {
            if (currentTurnAccumulator) {
              currentTurnAccumulator.answer += token
              set({ currentTurn: { ...currentTurnAccumulator } })
            }
          },
          onDone: (done) => {
            if (currentTurnAccumulator) {
              currentTurnAccumulator.category = done.category
              currentTurnAccumulator.category_confidence = done.category_confidence
              currentTurnAccumulator.confidence_score = done.confidence_score
              currentTurnAccumulator.is_personalized = done.is_personalized
              currentTurnAccumulator.latency_ms = done.latency_ms
              
              const finalTurn = { ...currentTurnAccumulator }
              set((s) => ({
                currentTurn: finalTurn,
                history: [...s.history, finalTurn],
                recordingState: 'done',
              }))
            }
          },
          onError: (err) => {
            set({ error: err, recordingState: 'error' })
          },
        }
      )
    } catch (err: any) {
      set({
        error: err.message || 'Processing failed',
        recordingState: 'error',
      })
    }
  },

  setRecordingState: (state) => set({ recordingState: state }),
  clearCurrentTurn: () => set({ currentTurn: null, recordingState: 'idle' }),
  clearError: () => set({ error: null }),
  setRealtimeMode: (enabled) => set({ realtimeMode: enabled }),
  addRealtimeTurn: (question, answer, latencyMs) => {
    const realtimeTurn: InterviewTurn = {
      question_id: `rt-${Date.now()}`,
      question_text: question,
      category: 'Technical',
      category_confidence: 1.0,
      retrieved_context: [],
      generated_prompt: '',
      answer,
      confidence_score: 0,
      transcription_confidence: null,
      is_personalized: false,
      latency_ms: latencyMs,
    }
    set((s) => ({
      history: [...s.history, realtimeTurn],
      currentTurn: realtimeTurn,
    }))
  },
}))
