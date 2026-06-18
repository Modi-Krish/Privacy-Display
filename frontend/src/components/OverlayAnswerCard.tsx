import { useState, useEffect, useRef } from 'react'
import { useInterviewStore } from '@/store/interviewStore'
import styles from './OverlayAnswerCard.module.css'

interface OverlayAnswerCardProps {
  isClickThrough?: boolean
}

export default function OverlayAnswerCard({ isClickThrough = false }: OverlayAnswerCardProps) {
  const {
    isSessionActive, currentTurn, recordingState,
    sessionId, submitText, startSession,
  } = useInterviewStore()

  const [textInput, setTextInput] = useState('')
  const answerEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when answer updates
  useEffect(() => {
    answerEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentTurn?.answer])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!textInput.trim() || recordingState === 'processing') return

    try {
      // Auto-start session if needed
      if (!sessionId) {
        await startSession()
      }
      await submitText(textInput.trim())
      setTextInput('')
    } catch (err: any) {
      console.error('Failed to submit question:', err)
      // The store will handle error state if submitText fails, but if startSession throws we need to handle it.
      useInterviewStore.setState({ 
        error: err.message || 'Failed to start session', 
        recordingState: 'error' 
      })
    }
  }

  const isProcessing = recordingState === 'processing'
  const hasAnswer = currentTurn && currentTurn.answer

  return (
    <div className={styles.card}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={`${styles.statusDot} ${!isSessionActive ? styles.statusDotIdle : ''}`} />
          <span className={styles.headerTitle}>
            {isSessionActive ? 'Live Session' : 'ReAI Overlay'}
          </span>
        </div>
        {isClickThrough && (
          <div className={styles.clickThroughBadge}>
            <span className="material-symbols-outlined" style={{ fontSize: 12 }}>touch_app</span>
            CLICK-THROUGH
          </div>
        )}
      </div>

      {/* Badges */}
      {currentTurn && (
        <div className={styles.badges}>
          <span className={`${styles.badge} ${styles.badgeCategory}`}>
            {currentTurn.category}
          </span>
          {currentTurn.latency_ms > 0 && (
            <span className={`${styles.badge} ${styles.badgeLatency}`}>
              {currentTurn.latency_ms}ms
            </span>
          )}
          {currentTurn.confidence_score > 0 && (
            <span className={`${styles.badge} ${styles.badgeConfidence}`}>
              {Math.round(currentTurn.confidence_score * 100)}%
            </span>
          )}
          {currentTurn.question_id?.startsWith('rt-') && (
            <span className={`${styles.badge} ${styles.badgeRealtime}`}>
              <span className="material-symbols-outlined" style={{ fontSize: 11 }}>graphic_eq</span>
              RT
            </span>
          )}
        </div>
      )}

      {/* Answer Area */}
      {isProcessing && !hasAnswer ? (
        <div className={styles.processingWrap}>
          <div className={styles.processingDots}>
            <div className={styles.processingDot} />
            <div className={styles.processingDot} />
            <div className={styles.processingDot} />
          </div>
          <span className={styles.processingText}>Analyzing question…</span>
        </div>
      ) : hasAnswer ? (
        <div className={styles.answerArea}>
          <div className={styles.questionLabel}>Question</div>
          <div className={styles.questionText}>{currentTurn.question_text}</div>
          <div className={styles.answerText}>
            {currentTurn.answer}
          </div>
          <div ref={answerEndRef} />
        </div>
      ) : (
        <div className={styles.emptyState}>
          <span className={`material-symbols-outlined ${styles.emptyIcon}`}>
            {recordingState === 'error' ? 'error' : 'auto_awesome'}
          </span>
          <span className={styles.emptyTitle}>
            {recordingState === 'error' ? 'Error Occurred' : 'Awaiting Input'}
          </span>
          <span className={styles.emptyDesc}>
            {recordingState === 'error' 
              ? useInterviewStore.getState().error || 'Failed to process request.' 
              : 'Type a question below or speak in the main window. Answers will stream here in real-time.'}
          </span>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className={styles.inputArea}>
        <input
          className={styles.textInput}
          placeholder="Type a question…"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          disabled={isProcessing}
          spellCheck={false}
        />
        <button
          type="submit"
          className={styles.sendBtn}
          disabled={!textInput.trim() || isProcessing}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>send</span>
        </button>
      </form>
    </div>
  )
}
