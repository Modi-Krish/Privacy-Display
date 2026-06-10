import { create } from 'zustand'
import { api } from '@/api/client'

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

  // Current turn
  currentTurn: InterviewTurn | null
  error: string | null

  // Session history
  history: InterviewTurn[]

  // Actions
  startSession: () => Promise<void>
  endSession: () => Promise<void>
  submitAudio: (blob: Blob) => Promise<void>
  submitText: (question: string) => Promise<void>
  setRecordingState: (state: RecordingState) => void
  clearCurrentTurn: () => void
  clearError: () => void
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
  currentTurn: null,
  error: null,
  history: [],

  startSession: async () => {
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
    set({ recordingState: 'processing', error: null })
    try {
      const audio_b64 = await blobToBase64(blob)
      const { data } = await api.post('/api/interview/question', {
        session_id: sessionId,
        audio_b64,
      })
      const turn: InterviewTurn = data
      set((s) => ({
        currentTurn: turn,
        history: [...s.history, turn],
        recordingState: 'done',
      }))
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || 'Processing failed',
        recordingState: 'error',
      })
    }
  },

  submitText: async (question) => {
    const { sessionId } = get()
    if (!sessionId) return
    set({ recordingState: 'processing', error: null })
    try {
      const { data } = await api.post('/api/interview/question', {
        session_id: sessionId,
        question,
      })
      const turn: InterviewTurn = data
      set((s) => ({
        currentTurn: turn,
        history: [...s.history, turn],
        recordingState: 'done',
      }))
    } catch (err: any) {
      set({
        error: err.response?.data?.detail || 'Processing failed',
        recordingState: 'error',
      })
    }
  },

  setRecordingState: (state) => set({ recordingState: state }),
  clearCurrentTurn: () => set({ currentTurn: null, recordingState: 'idle' }),
  clearError: () => set({ error: null }),
}))
