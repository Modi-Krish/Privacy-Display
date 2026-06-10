import { useEffect, useRef, useState } from 'react'
import { Mic, MicOff, Square, Send, RotateCcw, ChevronDown, ChevronUp, Zap, BookOpen, Target } from 'lucide-react'
import { useInterviewStore } from '@/store/interviewStore'
import { useProfileStore }   from '@/store/profileStore'
import toast from 'react-hot-toast'
import styles from './InterviewPage.module.css'
import ConfidenceGauge from '@/components/ConfidenceGauge'
import ContextDrawer   from '@/components/ContextDrawer'
import AudioRecorder   from '@/components/AudioRecorder'

const CATEGORY_COLORS: Record<string, string> = {
  'Technical':      'badge-info',
  'Behavioral':     'badge-success',
  'Project-Based':  'badge-accent',
  'HR':             'badge-warning',
}

export default function InterviewPage() {
  const {
    sessionId, isSessionActive, recordingState,
    currentTurn, error, history,
    startSession, endSession, submitText, clearError,
  } = useInterviewStore()
  const { resume } = useProfileStore()
  const [textQuestion, setTextQuestion] = useState('')
  const [showContext, setShowContext]   = useState(false)
  const [elapsed, setElapsed]           = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const answerRef = useRef<HTMLDivElement>(null)

  // Session timer
  useEffect(() => {
    if (isSessionActive) {
      setElapsed(0)
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000)
    } else {
      if (timerRef.current) clearInterval(timerRef.current)
      setElapsed(0)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [isSessionActive])

  // Scroll answer into view on new turn
  useEffect(() => {
    if (currentTurn) answerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [currentTurn])

  useEffect(() => {
    if (error) { toast.error(error); clearError() }
  }, [error])

  const fmt = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!textQuestion.trim()) return
    await submitText(textQuestion.trim())
    setTextQuestion('')
  }

  const handleStart = async () => {
    try { await startSession(); toast.success('Session started') }
    catch { toast.error('Failed to start session') }
  }

  const handleEnd = async () => {
    await endSession()
    toast.success(`Session ended — ${history.length} question${history.length !== 1 ? 's' : ''} answered`)
  }

  /* ─ Pre-session state ─ */
  if (!isSessionActive) {
    return (
      <div className={styles.preSession}>
        <div className={styles.preCard}>
          <div className={styles.preIcon}><Zap size={32} strokeWidth={1.5} /></div>
          <h1>Start Interview Session</h1>
          <p>Speak or type your interview question. Gemini will generate a personalized answer using your profile context.</p>

          {!resume && (
            <div className={styles.noResumeWarning}>
              <BookOpen size={15} />
              <span>No resume uploaded — answers will be general. <a href="/profile">Upload now →</a></span>
            </div>
          )}

          <button id="btn-start-session" className="btn btn-primary btn-lg" onClick={handleStart}>
            <Zap size={18} />
            Start Session
          </button>
        </div>
      </div>
    )
  }

  /* ─ Active session ─ */
  return (
    <div className={styles.page}>
      {/* Header bar */}
      <div className={styles.header}>
        <div className="flex items-center gap-3">
          <span className="pulse-dot" />
          <span className={styles.sessionLabel}>Live Session</span>
          <span className={styles.timer}>{fmt(elapsed)}</span>
          <span className={styles.questionCount}>{history.length} answered</span>
        </div>
        <button id="btn-end-session" className="btn btn-danger btn-sm" onClick={handleEnd}>
          <Square size={14} />End Session
        </button>
      </div>

      {/* Body */}
      <div className={styles.body}>
        {/* Left — Input */}
        <div className={styles.leftCol}>
          <AudioRecorder />

          <div className={styles.dividerLabel}><span>or type question</span></div>

          <form onSubmit={handleTextSubmit} className={styles.textForm}>
            <textarea
              id="input-text-question"
              className="input"
              placeholder="Type the interview question here…"
              value={textQuestion}
              onChange={(e) => setTextQuestion(e.target.value)}
              rows={3}
              disabled={recordingState === 'processing'}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleTextSubmit(e) }
              }}
            />
            <button
              id="btn-submit-text"
              type="submit"
              className="btn btn-primary w-full"
              disabled={!textQuestion.trim() || recordingState === 'processing'}
            >
              {recordingState === 'processing'
                ? <><span className="spinner" /> Processing…</>
                : <><Send size={16} />  Get Answer</>}
            </button>
          </form>

          {/* History mini-list */}
          {history.length > 1 && (
            <div className={styles.historyList}>
              <p className={styles.sectionLabel}>Previous Questions</p>
              {history.slice(0, -1).reverse().slice(0, 3).map((turn) => (
                <div key={turn.question_id} className={styles.historyItem}>
                  <span className={`badge ${CATEGORY_COLORS[turn.category] || 'badge-info'}`}>{turn.category}</span>
                  <span className={styles.historyText}>{turn.question_text}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right — Answer */}
        <div className={styles.rightCol} ref={answerRef}>
          {recordingState === 'processing' && (
            <div className={styles.processingCard}>
              <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
              <p>Analyzing question and generating personalized answer…</p>
            </div>
          )}

          {currentTurn && recordingState !== 'processing' && (
            <div className={`${styles.answerCard} fade-in`}>
              {/* Question */}
              <div className={styles.questionSection}>
                <div className="flex items-center gap-2" style={{ marginBottom: 8 }}>
                  <span className={`badge ${CATEGORY_COLORS[currentTurn.category] || 'badge-info'}`}>
                    {currentTurn.category}
                  </span>
                  {currentTurn.transcription_confidence !== null && (
                    <span className="badge badge-success" title="Transcription confidence">
                      🎙 {Math.round(currentTurn.transcription_confidence * 100)}%
                    </span>
                  )}
                  {!currentTurn.is_personalized && (
                    <span className="badge badge-warning">General Answer</span>
                  )}
                </div>
                <p className={styles.questionText}>{currentTurn.question_text}</p>
              </div>

              <div className="divider" />

              {/* Answer */}
              <div className={styles.answerSection}>
                <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
                  <p className={styles.sectionLabel}>
                    <Target size={13} /> Suggested Answer
                  </p>
                  <div className="flex items-center gap-2">
                    <span className={styles.latency}>{currentTurn.latency_ms}ms</span>
                    <ConfidenceGauge value={currentTurn.confidence_score} />
                  </div>
                </div>
                <div className={styles.answerText}>{currentTurn.answer}</div>
              </div>

              <div className="divider" />

              {/* Context drawer */}
              <button
                id="btn-toggle-context"
                className={styles.contextToggle}
                onClick={() => setShowContext(!showContext)}
              >
                <BookOpen size={14} />
                Context & Prompt Viewer ({currentTurn.retrieved_context.length} chunks)
                {showContext ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              {showContext && (
                <ContextDrawer
                  chunks={currentTurn.retrieved_context}
                  prompt={currentTurn.generated_prompt}
                  categoryConfidence={currentTurn.category_confidence}
                />
              )}
            </div>
          )}

          {!currentTurn && recordingState === 'idle' && (
            <div className={styles.emptyState}>
              <Mic size={40} strokeWidth={1} style={{ color: 'var(--text-muted)' }} />
              <p>Record or type your first question to begin</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
