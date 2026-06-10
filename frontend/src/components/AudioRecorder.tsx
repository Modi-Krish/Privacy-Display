import { useState, useRef } from 'react'
import { Mic, Square, AlertTriangle, Monitor } from 'lucide-react'
import { useInterviewStore } from '@/store/interviewStore'
import toast from 'react-hot-toast'
import styles from './AudioRecorder.module.css'

const MIME_TYPES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/mp4',
]

function getSupportedMime(): string | null {
  for (const m of MIME_TYPES) {
    if (MediaRecorder.isTypeSupported(m)) return m
  }
  return null
}

type AudioSource = 'mic' | 'screen'

export default function AudioRecorder() {
  const { recordingState, setRecordingState, submitAudio, isSessionActive } = useInterviewStore()
  const [micError, setMicError]     = useState<string | null>(null)
  const [audioSource, setAudioSource] = useState<AudioSource>('mic')
  const mediaRef   = useRef<MediaRecorder | null>(null)
  const chunksRef  = useRef<Blob[]>([])
  const streamRef  = useRef<MediaStream | null>(null)
  const videoTrackRef = useRef<MediaStreamTrack | null>(null)

  const isRecording  = recordingState === 'recording'
  const isProcessing = recordingState === 'processing'

  const getStream = async (): Promise<MediaStream> => {
    if (audioSource === 'mic') {
      return navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    }

    // Screen share — capture system audio from the shared tab/screen
    const displayStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,          // required by spec, we keep it alive for lifecycle tracking
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        sampleRate: 44100,
      },
    })

    // Check if audio track was granted (user must tick "Share audio")
    const audioTracks = displayStream.getAudioTracks()
    if (audioTracks.length === 0) {
      // Stop video tracks since we don't need them
      displayStream.getVideoTracks().forEach((t) => t.stop())
      throw new Error('NO_AUDIO')
    }

    // Hold reference to video track for stop events
    const videoTrack = displayStream.getVideoTracks()[0]
    if (videoTrack) {
      videoTrackRef.current = videoTrack
    }

    // Return audio-only stream (discard video from recording stream)
    return new MediaStream(audioTracks)
  }

  const startRecording = async () => {
    setMicError(null)
    try {
      const stream = await getStream()
      streamRef.current = stream
      const mimeType = getSupportedMime()
      if (!mimeType) throw new Error('No supported audio format')

      const mr = new MediaRecorder(stream, { mimeType })
      mediaRef.current  = mr
      chunksRef.current = []

      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: mimeType })
        stream.getTracks().forEach((t) => t.stop())
        if (videoTrackRef.current) {
          videoTrackRef.current.stop()
          videoTrackRef.current = null
        }
        await submitAudio(blob)
      }

      // If the user stops the screen share from the browser UI, stop recording too
      if (videoTrackRef.current) {
        videoTrackRef.current.addEventListener('ended', () => {
          if (mediaRef.current?.state === 'recording') stopRecording()
        })
      }
      stream.getAudioTracks()[0]?.addEventListener('ended', () => {
        if (mediaRef.current?.state === 'recording') stopRecording()
      })

      mr.start(250)
      setRecordingState('recording')
    } catch (err: any) {
      let msg: string
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        msg = audioSource === 'mic'
          ? 'Microphone permission denied. Please allow access in your browser.'
          : 'Screen share was cancelled or permission denied.'
      } else if (err.message === 'NO_AUDIO') {
        msg = 'No audio captured. Make sure to check "Share tab audio" or "Share system audio" in the browser dialog.'
      } else {
        msg = `Could not start recording: ${err.message}`
      }
      setMicError(msg)
      toast.error(msg)
    }
  }

  const stopRecording = () => {
    mediaRef.current?.stop()
    setRecordingState('processing')
  }

  return (
    <div className={styles.wrap}>

      {/* Source toggle — only shown when not recording */}
      {!isRecording && !isProcessing && (
        <div className={styles.sourceToggle}>
          <button
            id="btn-source-mic"
            className={`${styles.sourceBtn} ${audioSource === 'mic' ? styles.sourceActive : ''}`}
            onClick={() => { setAudioSource('mic'); setMicError(null) }}
            title="Record from microphone"
          >
            <Mic size={14} strokeWidth={1.8} />
            <span>Mic</span>
          </button>
          <button
            id="btn-source-screen"
            className={`${styles.sourceBtn} ${audioSource === 'screen' ? styles.sourceActive : ''}`}
            onClick={() => { setAudioSource('screen'); setMicError(null) }}
            title="Capture audio from screen share (captures interviewer's voice from Zoom/Meet/Teams)"
          >
            <Monitor size={14} strokeWidth={1.8} />
            <span>Screen Audio</span>
          </button>
        </div>
      )}

      {/* Record button */}
      <button
        id={isRecording ? 'btn-stop-recording' : 'btn-start-recording'}
        className={`${styles.recordBtn} ${isRecording ? styles.recording : ''}`}
        onClick={isRecording ? stopRecording : startRecording}
        disabled={isProcessing || !isSessionActive}
        title={isRecording ? 'Stop recording' : audioSource === 'mic' ? 'Record from microphone' : 'Capture screen audio'}
      >
        <div className={styles.recordInner}>
          {isProcessing
            ? <span className="spinner" style={{ width: 24, height: 24, borderWidth: 3 }} />
            : isRecording
              ? <Square size={22} fill="currentColor" />
              : audioSource === 'screen'
                ? <Monitor size={22} strokeWidth={1.5} />
                : <Mic size={22} strokeWidth={1.5} />}
        </div>
        {isRecording && <div className={styles.ripple} />}
      </button>

      <p className={styles.label}>
        {isProcessing
          ? 'Processing…'
          : isRecording
            ? `Recording (${audioSource === 'screen' ? 'screen audio' : 'mic'}) — click to stop`
            : audioSource === 'screen'
              ? 'Click to share screen & capture audio'
              : 'Click to record question'}
      </p>

      {audioSource === 'screen' && !isRecording && !isProcessing && (
        <p className={styles.screenHint}>
          💡 A browser dialog will open. Select your meeting tab and check <strong>"Share tab audio"</strong>
        </p>
      )}

      {micError && (
        <div className={styles.micError}>
          <AlertTriangle size={13} />
          <span>{micError}</span>
        </div>
      )}
    </div>
  )
}
