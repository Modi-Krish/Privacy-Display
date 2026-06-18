import { useEffect, useRef, useCallback } from 'react'
import { useRealtimeVoice, VoicePhase } from '@/hooks/useRealtimeVoice'
import styles from './RealtimeVoicePanel.module.css'

// ── Waveform Visualizer ────────────────────────────────────────────────────

function WaveformBars({ amplitude, phase }: { amplitude: number; phase: VoicePhase }) {
  const BAR_COUNT = 20
  const isActive = phase === 'listening' || phase === 'detecting'

  return (
    <div className={styles.waveform} aria-hidden="true">
      {Array.from({ length: BAR_COUNT }, (_, i) => {
        // Each bar gets a different phase offset so they look organic
        const offset = Math.sin((i / BAR_COUNT) * Math.PI * 2)
        const noiseAmp = isActive
          ? amplitude * (0.5 + 0.5 * Math.abs(Math.sin(i * 1.3)))
          : 0.06
        const height = Math.max(0.06, noiseAmp + offset * 0.15 * amplitude)
        return (
          <div
            key={i}
            className={`${styles.waveBar} ${isActive ? styles.waveBarsActive : ''}`}
            style={{
              '--bar-height': `${Math.min(1, height) * 100}%`,
              '--bar-delay': `${(i % 5) * 0.08}s`,
            } as React.CSSProperties}
          />
        )
      })}
    </div>
  )
}

// ── Phase label ────────────────────────────────────────────────────────────

const PHASE_META: Record<VoicePhase, { label: string; icon: string; cls: string }> = {
  idle:       { label: 'Ready',      icon: 'mic',           cls: '' },
  listening:  { label: 'Listening',  icon: 'graphic_eq',    cls: 'listening' },
  detecting:  { label: 'Detecting',  icon: 'psychology',    cls: 'detecting' },
  generating: { label: 'Generating', icon: 'auto_awesome',  cls: 'generating' },
  done:       { label: 'Done',       icon: 'check_circle',  cls: 'done' },
}

// ── Token-streaming answer display ─────────────────────────────────────────

function StreamingAnswer({ text, phase }: { text: string; phase: VoicePhase }) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [text])

  if (!text && phase !== 'generating') return null

  return (
    <div className={styles.answerBubble}>
      <div className={styles.answerLabel}>
        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>auto_awesome</span>
        AI Response
      </div>
      <p className={styles.answerText}>
        {text}
        {phase === 'generating' && <span className={styles.cursor}>▋</span>}
      </p>
      <div ref={endRef} />
    </div>
  )
}

// ── Main Panel ─────────────────────────────────────────────────────────────

interface RealtimeVoicePanelProps {
  /** Called when a complete turn finishes, so the parent can add it to history */
  onTurnComplete?: (question: string, answer: string, latencyMs: number) => void
}

export default function RealtimeVoicePanel({ onTurnComplete }: RealtimeVoicePanelProps) {
  const {
    connectionState,
    phase,
    liveTranscript,
    currentAnswer,
    isListening,
    isGenerating,
    firstTokenLatency,
    totalLatency,
    amplitude,
    error,
    connect,
    disconnect,
    startListening,
    stopListening,
    resetAnswer,
  } = useRealtimeVoice()

  const prevPhaseRef = useRef<VoicePhase>('idle')
  const prevAnswerRef = useRef('')
  const prevQuestionRef = useRef('')

  // Fire onTurnComplete when a turn finishes
  useEffect(() => {
    if (prevPhaseRef.current === 'generating' && phase === 'done') {
      if (onTurnComplete && currentAnswer && liveTranscript) {
        onTurnComplete(liveTranscript, currentAnswer, totalLatency ?? 0)
      }
    }
    prevPhaseRef.current = phase
  }, [phase, currentAnswer, liveTranscript, totalLatency, onTurnComplete])

  const handleToggle = useCallback(async () => {
    if (isListening) {
      stopListening()
    } else {
      if (connectionState === 'disconnected' || connectionState === 'error') {
        await connect()
      }
      await startListening()
    }
  }, [isListening, connectionState, connect, startListening, stopListening])

  const phaseMeta = PHASE_META[phase]
  const isConnected = connectionState === 'connected'
  const isConnecting = connectionState === 'connecting'

  return (
    <div className={`${styles.panel} ${isListening ? styles.panelActive : ''}`}>
      {/* Header row */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={`material-symbols-outlined ${styles.headerIcon}`}>
            {phaseMeta.icon}
          </span>
          <span className={styles.headerTitle}>Real-Time Voice</span>
        </div>

        <div className={styles.badges}>
          {/* Connection status */}
          <span className={`${styles.badge} ${styles[`badge_${connectionState}`]}`}>
            <span className={styles.statusDot} />
            {connectionState === 'connected' ? 'Connected'
              : connectionState === 'connecting' ? 'Connecting…'
              : connectionState === 'error' ? 'Error'
              : 'Offline'}
          </span>

          {/* Phase badge */}
          {phase !== 'idle' && (
            <span className={`${styles.badge} ${styles[`badge_phase_${phaseMeta.cls}`]}`}>
              {phaseMeta.label}
            </span>
          )}

          {/* Latency badge */}
          {firstTokenLatency !== null && (
            <span className={`${styles.badge} ${styles.badge_latency}`}>
              ⚡ {firstTokenLatency}ms first token
            </span>
          )}
        </div>
      </div>

      {/* Waveform */}
      <WaveformBars amplitude={amplitude} phase={phase} />

      {/* Transcript area */}
      <div className={styles.transcriptArea}>
        <div className={styles.transcriptLabel}>
          <span className="material-symbols-outlined" style={{ fontSize: 14 }}>mic</span>
          You
        </div>
        {liveTranscript ? (
          <p className={styles.transcriptText}>
            {liveTranscript}
            {(phase === 'listening' || phase === 'detecting') && (
              <span className={styles.cursor}>▋</span>
            )}
          </p>
        ) : (
          <p className={styles.transcriptPlaceholder}>
            {isListening
              ? 'Listening… start speaking your question'
              : 'Press the mic button to begin speaking'}
          </p>
        )}
      </div>

      {/* Streaming answer */}
      <StreamingAnswer text={currentAnswer} phase={phase} />

      {/* Error message */}
      {error && (
        <div className={styles.errorBanner}>
          <span className="material-symbols-outlined" style={{ fontSize: 16 }}>warning</span>
          {error}
        </div>
      )}

      {/* Controls */}
      <div className={styles.controls}>
        {/* Main mic toggle */}
        <button
          id="btn-realtime-mic-toggle"
          className={`${styles.micBtn} ${isListening ? styles.micBtnActive : ''}`}
          onClick={handleToggle}
          disabled={isConnecting}
          title={isListening ? 'Stop listening' : 'Start listening'}
        >
          <span className="material-symbols-outlined" style={{ fontSize: 28 }}>
            {isListening ? 'stop' : 'mic'}
          </span>
          <span className={styles.micBtnLabel}>
            {isConnecting ? 'Connecting…'
              : isListening ? 'Stop'
              : 'Start Listening'}
          </span>
        </button>

        {/* Reset button — visible after an answer */}
        {(currentAnswer || liveTranscript) && !isListening && (
          <button
            id="btn-realtime-reset"
            className={styles.resetBtn}
            onClick={resetAnswer}
            title="Clear and start fresh"
          >
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>refresh</span>
            New Question
          </button>
        )}

        {/* Total latency */}
        {totalLatency !== null && phase === 'done' && (
          <span className={styles.totalLatency}>
            Total: {totalLatency}ms
          </span>
        )}
      </div>

      {/* Speed hint */}
      {phase === 'idle' && !isListening && (
        <p className={styles.hint}>
          💡 Gemini starts answering as soon as your question is detected — no need to stop talking
        </p>
      )}
    </div>
  )
}
