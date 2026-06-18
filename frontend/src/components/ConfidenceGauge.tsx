import styles from './ConfidenceGauge.module.css'

interface Props { value: number }  // 0.0 – 1.0

export default function ConfidenceGauge({ value }: Props) {
  const pct    = Math.round(value * 100)
  const color  = pct >= 75 ? '#2d7a3a' : pct >= 50 ? '#b35900' : '#ff4d4d'
  const label  = pct >= 75 ? 'High' : pct >= 50 ? 'Medium' : 'Low'

  return (
    <div className={styles.gauge} title={`Confidence: ${pct}%`}>
      <svg width="44" height="44" viewBox="0 0 44 44">
        {/* Track */}
        <circle cx="22" cy="22" r="18" fill="none" stroke="#e5e0d8" strokeWidth="4" />
        {/* Fill */}
        <circle
          cx="22" cy="22" r="18"
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={`${113.1 * value} 113.1`}
          transform="rotate(-90 22 22)"
          style={{ transition: 'stroke-dasharray 0.6s cubic-bezier(0.4,0,0.2,1)' }}
        />
        <text
          x="22" y="26"
          textAnchor="middle"
          fill={color}
          fontSize="10"
          fontWeight="700"
          fontFamily="'Kalam', cursive"
        >{pct}%</text>
      </svg>
      <span className={styles.label} style={{ color }}>{label}</span>
    </div>
  )
}
