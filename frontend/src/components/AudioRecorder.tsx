import { useState, useRef } from 'react'
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
  const [activeSource, setActiveSource] = useState<AudioSource | null>(null)
  const mediaRef   = useRef<MediaRecorder | null>(null)
  const chunksRef  = useRef<Blob[]>([])
  const streamRef  = useRef<MediaStream | null>(null)
  const videoTrackRef = useRef<MediaStreamTrack | null>(null)

  const isRecording  = recordingState === 'recording'
  const isProcessing = recordingState === 'processing'

  const getStream = async (source: AudioSource): Promise<MediaStream> => {
    if (source === 'mic') {
      return navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    }

    const displayStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        sampleRate: 44100,
      },
    })

    const audioTracks = displayStream.getAudioTracks()
    if (audioTracks.length === 0) {
      displayStream.getVideoTracks().forEach((t) => t.stop())
      throw new Error('NO_AUDIO')
    }

    const videoTrack = displayStream.getVideoTracks()[0]
    if (videoTrack) {
      videoTrackRef.current = videoTrack
    }

    return new MediaStream(audioTracks)
  }

  const startRecording = async (source: AudioSource) => {
    setMicError(null)
    setActiveSource(source)
    try {
      const stream = await getStream(source)
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
        setActiveSource(null)
      }

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
      setActiveSource(null)
      let msg: string
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        msg = source === 'mic'
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

  const handleToggle = (source: AudioSource) => {
    if (!isSessionActive || isProcessing) return
    if (isRecording) {
      if (activeSource === source) {
        stopRecording()
      } else {
        toast.error('Another recording is already in progress.')
      }
    } else {
      startRecording(source)
    }
  }

  return (
    <div className={styles.container}>
      {/* Mic Audio Toggle Row */}
      <div 
        className={styles.toggleRow} 
        onClick={() => handleToggle('mic')}
        style={{ cursor: (!isSessionActive || isProcessing) ? 'not-allowed' : 'pointer', opacity: (!isSessionActive || isProcessing) ? 0.6 : 1 }}
      >
        <div className={styles.toggleLeft}>
          <button className={`${styles.iconBtn} ${isRecording && activeSource === 'mic' ? styles.iconBtnActive : ''}`}>
            {isRecording && activeSource === 'mic' ? (
              <span className="material-symbols-outlined text-[24px]">square</span>
            ) : (
              <span className="material-symbols-outlined text-[24px]">mic</span>
            )}
          </button>
          <span className={styles.toggleLabel}>Mic Audio {isRecording && activeSource === 'mic' ? '(Recording...)' : ''}</span>
        </div>
        <div className={`${styles.switch} ${isRecording && activeSource === 'mic' ? styles.switchOn : styles.switchOff}`}>
          <div className={`${styles.switchThumb} ${isRecording && activeSource === 'mic' ? styles.thumbOn : styles.thumbOff}`}></div>
        </div>
      </div>

      {/* Screen Audio Toggle Row */}
      <div 
        className={styles.toggleRow} 
        onClick={() => handleToggle('screen')}
        style={{ cursor: (!isSessionActive || isProcessing) ? 'not-allowed' : 'pointer', opacity: (!isSessionActive || isProcessing) ? 0.6 : 1 }}
      >
        <div className={styles.toggleLeft}>
          <button className={`${styles.iconBtn} ${isRecording && activeSource === 'screen' ? styles.iconBtnActive : ''}`}>
            {isRecording && activeSource === 'screen' ? (
              <span className="material-symbols-outlined text-[24px]">square</span>
            ) : (
              <span className="material-symbols-outlined text-[24px]">volume_up</span>
            )}
          </button>
          <span className={styles.toggleLabel}>Screen Audio {isRecording && activeSource === 'screen' ? '(Recording...)' : ''}</span>
        </div>
        <div className={`${styles.switch} ${isRecording && activeSource === 'screen' ? styles.switchOn : styles.switchOff}`}>
          <div className={`${styles.switchThumb} ${isRecording && activeSource === 'screen' ? styles.thumbOn : styles.thumbOff}`}></div>
        </div>
      </div>

      {micError && (
        <div className={styles.micError}>
          <span className="material-symbols-outlined text-[16px]">warning</span>
          <span>{micError}</span>
        </div>
      )}
    </div>
  )
}
