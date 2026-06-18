import { useEffect, useRef, useState, useCallback } from 'react'
import { useInterviewStore } from '@/store/interviewStore'
import { useProfileStore }   from '@/store/profileStore'
import toast from 'react-hot-toast'
import styles from './InterviewPage.module.css'
import ConfidenceGauge from '@/components/ConfidenceGauge'
import ContextDrawer   from '@/components/ContextDrawer'
import AudioRecorder   from '@/components/AudioRecorder'
import RealtimeVoicePanel from '@/components/RealtimeVoicePanel'

export default function InterviewPage() {
  const {
    sessionId, isSessionActive, recordingState,
    currentTurn, error, history,
    startSession, endSession, submitText, clearError,
    realtimeMode, setRealtimeMode, addRealtimeTurn,
  } = useInterviewStore()
  const { resume } = useProfileStore()
  const [textQuestion, setTextQuestion] = useState('')
  const [showContext, setShowContext]   = useState(false)
  const [elapsed, setElapsed]           = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const answerRef = useRef<HTMLDivElement>(null)

  const CATEGORY_COLORS: Record<string, string> = {
    'Technical':      styles.badgeInfo,
    'Behavioral':     styles.badgeSuccess,
    'Project-Based':  styles.badgeAccent,
    'HR':             styles.badgeWarning,
  }

  function AnalyzingLoader() {
    const [dots, setDots] = useState('.')
    useEffect(() => {
      const iv = setInterval(() => {
        setDots((d) => (d.length >= 3 ? '.' : d + '.'))
      }, 500)
      return () => clearInterval(iv)
    }, [])
    return <span>Analyzing{dots}</span>
  }

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

  useEffect(() => {
    if (currentTurn) answerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [currentTurn])

  useEffect(() => {
    if (error) { toast.error(error); clearError() }
  }, [error])

  const fmt = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  const handleTextSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!textQuestion.trim() || recordingState === 'processing') return
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

  const handleRealtimeTurnComplete = useCallback(
    (question: string, answer: string, latencyMs: number) => {
      addRealtimeTurn(question, answer, latencyMs)
    },
    [addRealtimeTurn]
  )

  /* ─ Pre-session state ─ */
  if (!isSessionActive) {
    return (
      <div className={styles.page}>
        <div className={styles.bgDecoration}></div>
        <div className={styles.preSession}>
          <div className={styles.preCard}>
            <div className={styles.preIcon}>
              <span className="material-symbols-outlined text-[40px]">bolt</span>
            </div>
            <h1 className={styles.preTitle}>Start Interview Session</h1>
            <p className={styles.preDesc}>Speak or type your interview question. Gemini will generate a personalized answer using your profile context.</p>

            {!resume && (
              <div className={styles.noResumeWarning}>
                <span className="material-symbols-outlined text-[16px]">menu_book</span>
                <span>No resume uploaded — answers will be general. <a href="/profile">Upload now →</a></span>
              </div>
            )}

            <button id="btn-start-session" className={styles.startBtn} onClick={handleStart}>
              <span className="material-symbols-outlined text-[20px]">bolt</span>
              Start Session
            </button>
          </div>
        </div>
      </div>
    )
  }

  /* ─ Active session ─ */
  return (
    <div className={styles.page}>
      <div className={styles.bgDecoration}></div>
      
      {/* TopAppBar */}
      <header className={styles.topAppBar}>
        <div className="flex items-center gap-4">
          <div className={styles.sessionPill}>
            <div className={styles.pulseDot}></div>
            <span className={styles.sessionPillText}>Live Session {fmt(elapsed)}</span>
          </div>

          {/* ── Mode Toggle ── */}
          <div className={styles.modeToggle} role="group" aria-label="Interaction mode">
            <button
              id="btn-mode-standard"
              className={`${styles.modeBtn} ${!realtimeMode ? styles.modeBtnActive : ''}`}
              onClick={() => setRealtimeMode(false)}
              title="Stop-and-submit mode"
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>stop_circle</span>
              Standard
            </button>
            <button
              id="btn-mode-realtime"
              className={`${styles.modeBtn} ${realtimeMode ? styles.modeBtnActive : ''}`}
              onClick={() => setRealtimeMode(true)}
              title="Real-time streaming mode"
            >
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>graphic_eq</span>
              Real-Time
            </button>
          </div>
        </div>
        
        <div className={styles.headerActions}>
          <div className={styles.iconGrp}>
            <button className={styles.iconBtn}>
              <span className="material-symbols-outlined">notifications</span>
            </button>
            <button className={styles.iconBtn}>
              <span className="material-symbols-outlined">help</span>
            </button>
          </div>
          
          <button className={styles.endBtn} onClick={handleEnd}>
            <span className="material-symbols-outlined text-[18px]">stop_circle</span>
            End Session
          </button>
          
          <button className={styles.avatar}>
            <span className="material-symbols-outlined">person</span>
          </button>
        </div>
      </header>

      {/* Workspace Canvas */}
      <div className={styles.workspace}>
        {/* Left Panel: Input Area */}
        <section className={styles.leftPanel}>

          {realtimeMode ? (
            /* ── Real-Time Mode ── */
            <RealtimeVoicePanel onTurnComplete={handleRealtimeTurnComplete} />
          ) : (
            /* ── Standard Mode ── */
            <div className={styles.inputCard}>
              <h2 className={styles.inputTitle}>Question Prompt</h2>
              <textarea
                className={styles.textarea}
                placeholder="Type your question or use the mic..."
                value={textQuestion}
                onChange={(e) => setTextQuestion(e.target.value)}
                disabled={recordingState === 'processing'}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleTextSubmit() }
                }}
              ></textarea>
              
              <div className={styles.controlsWrap}>
                <AudioRecorder />
                
                <button
                  className={styles.getAnswerBtn}
                  onClick={() => handleTextSubmit()}
                  disabled={!textQuestion.trim() || recordingState === 'processing'}
                >
                  {recordingState === 'processing' ? (
                    <>Processing...</>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[20px]">auto_awesome</span>
                      Get Answer
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* History Mini List — shared between both modes */}
          {history.length > 1 && (
            <div className={styles.historyMiniList}>
              <p className={styles.sectionLabel}>Previous Questions</p>
              {history.slice(0, -1).reverse().slice(0, 3).map((turn) => (
                <div key={turn.question_id} className={styles.historyItem}>
                  <span className={`${styles.badge} ${CATEGORY_COLORS[turn.category] || styles.badgeInfo}`}>{turn.category}</span>
                  <span className={styles.historyText}>{turn.question_text}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Right Panel: Output Workspace */}
        <section className={styles.rightPanel}>
          <div className={styles.referenceImage}></div>

          {/* Empty State */}
          {!currentTurn && recordingState === 'idle' && !realtimeMode && (
            <div className={styles.emptyState}>
              <div className={styles.pulsingMicWrap}>
                <div className={styles.pulseRing}></div>
                <div className={styles.micIconInner}>
                  <span className="material-symbols-outlined text-[40px]">mic</span>
                </div>
              </div>
              <h3 className={styles.emptyTitle}>Awaiting Input</h3>
              <p className={styles.emptyDesc}>
                Record or type your first question to begin. The AI will process the context and provide real-time assistance.
              </p>
            </div>
          )}

          {/* Real-time mode empty state */}
          {!currentTurn && realtimeMode && (
            <div className={styles.emptyState}>
              <div className={styles.pulsingMicWrap}>
                <div className={styles.pulseRing}></div>
                <div className={`${styles.micIconInner} ${styles.micIconRealtime}`}>
                  <span className="material-symbols-outlined text-[40px]">graphic_eq</span>
                </div>
              </div>
              <h3 className={styles.emptyTitle}>Real-Time Mode</h3>
              <p className={styles.emptyDesc}>
                Press the mic button on the left and start speaking. Your answer will appear here as you talk — before you even finish your question.
              </p>
            </div>
          )}

          {/* Processing / Output */}
          <div className={styles.outputContent} ref={answerRef}>
            {recordingState === 'processing' && !currentTurn?.answer && (
              <div className={styles.processingCard}>
                <div className={styles.pulseDot} style={{ width: '20px', height: '20px', backgroundColor: 'var(--primary)' }}></div>
                <p><AnalyzingLoader /></p>
              </div>
            )}

            {currentTurn && (recordingState !== 'processing' || currentTurn.answer) && (
              <div className={styles.answerCard}>
                {/* Question */}
                <div>
                  <div className={styles.badges}>
                    {recordingState === 'processing' && (
                      <span className={`${styles.badge} ${styles.badgeWarning}`}>Thinking...</span>
                    )}
                    <span className={`${styles.badge} ${CATEGORY_COLORS[currentTurn.category] || styles.badgeInfo}`}>
                      {currentTurn.category}
                    </span>
                    {currentTurn.transcription_confidence !== null && (
                      <span className={`${styles.badge} ${styles.badgeSuccess}`}>
                        <span className="material-symbols-outlined text-[14px]">mic</span>
                        {Math.round(currentTurn.transcription_confidence * 100)}%
                      </span>
                    )}
                    {!currentTurn.is_personalized && (
                      <span className={`${styles.badge} ${styles.badgeWarning}`}>General Answer</span>
                    )}
                    {/* Real-time badge for turns from realtime mode */}
                    {currentTurn.question_id.startsWith('rt-') && (
                      <span className={`${styles.badge} ${styles.badgeAccent}`}>
                        <span className="material-symbols-outlined text-[12px]">graphic_eq</span>
                        Real-Time
                      </span>
                    )}
                  </div>
                  <p className={styles.questionText}>{currentTurn.question_text}</p>
                </div>

                <div className={styles.divider}></div>

                {/* Answer */}
                <div>
                  <div className={styles.answerSectionHeader}>
                    <p className={styles.sectionLabel}>
                      <span className="material-symbols-outlined text-[14px]">target</span>
                      Suggested Answer
                    </p>
                    <div className="flex items-center gap-2">
                      {recordingState === 'processing' ? (
                        <span className={styles.latency}>Generating...</span>
                      ) : (
                        <>
                          <span className={styles.latency}>{currentTurn.latency_ms}ms</span>
                          {currentTurn.confidence_score > 0 && (
                            <ConfidenceGauge value={currentTurn.confidence_score} />
                          )}
                        </>
                      )}
                    </div>
                  </div>
                  <div className={styles.answerText}>
                    {currentTurn.answer}
                  </div>
                </div>

                {/* Context Drawer — only for standard mode turns (real-time turns have no prompt) */}
                {currentTurn.generated_prompt && (
                  <>
                    <div className={styles.divider}></div>
                    <button
                      className={styles.contextToggle}
                      onClick={() => setShowContext(!showContext)}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="material-symbols-outlined text-[16px]">menu_book</span>
                        Context & Prompt Viewer ({currentTurn.retrieved_context.length} chunks)
                      </span>
                      <span className="material-symbols-outlined text-[18px]">
                        {showContext ? 'expand_less' : 'expand_more'}
                      </span>
                    </button>

                    {showContext && (
                      <ContextDrawer
                        chunks={currentTurn.retrieved_context}
                        prompt={currentTurn.generated_prompt}
                        categoryConfidence={currentTurn.category_confidence}
                      />
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
