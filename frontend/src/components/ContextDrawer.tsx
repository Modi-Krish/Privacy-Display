import { useState } from 'react'
import { ChunkView } from '@/store/interviewStore'
import { Database, FileText, Code2, ChevronRight } from 'lucide-react'
import styles from './ContextDrawer.module.css'

interface Props {
  chunks: ChunkView[]
  prompt: string
  categoryConfidence: number
}

const SOURCE_ICONS: Record<string, React.ComponentType<any>> = {
  resume:  FileText,
  project: Code2,
  skill:   Database,
}

export default function ContextDrawer({ chunks, prompt, categoryConfidence }: Props) {
  const [tab, setTab] = useState<'chunks' | 'prompt'>('chunks')

  return (
    <div className={`${styles.drawer} fade-in`}>
      {/* Tab bar */}
      <div className={styles.tabs}>
        <button
          id="ctx-tab-chunks"
          className={`${styles.tab} ${tab === 'chunks' ? styles.tabActive : ''}`}
          onClick={() => setTab('chunks')}
        >
          Retrieved Context ({chunks.length})
        </button>
        <button
          id="ctx-tab-prompt"
          className={`${styles.tab} ${tab === 'prompt' ? styles.tabActive : ''}`}
          onClick={() => setTab('prompt')}
        >
          Generated Prompt
        </button>
      </div>

      {tab === 'chunks' && (
        <div className={styles.chunkList}>
          {chunks.length === 0 ? (
            <div className={styles.empty}>No context retrieved — general answer generated.</div>
          ) : (
            chunks.map((chunk, i) => {
              const Icon = SOURCE_ICONS[chunk.source] || FileText
              const scorePct = Math.round(chunk.score * 100)
              return (
                <div key={i} className={styles.chunk}>
                  <div className={styles.chunkHeader}>
                    <div className="flex items-center gap-2">
                      <Icon size={12} style={{ color: 'var(--accent)' }} />
                      <span className={styles.chunkSource}>{chunk.source} / {chunk.section}</span>
                    </div>
                    <div className={styles.scoreBar}>
                      <div
                        className={styles.scoreFill}
                        style={{ width: `${scorePct}%` }}
                      />
                      <span className={styles.scoreLabel}>{scorePct}%</span>
                    </div>
                  </div>
                  <p className={styles.chunkText}>{chunk.text}</p>
                </div>
              )
            })
          )}
          <div className={styles.metaRow}>
            <span>Classification confidence: <strong>{Math.round(categoryConfidence * 100)}%</strong></span>
          </div>
        </div>
      )}

      {tab === 'prompt' && (
        <div className={styles.promptBox}>
          <pre className={styles.promptText}>{prompt}</pre>
        </div>
      )}
    </div>
  )
}
