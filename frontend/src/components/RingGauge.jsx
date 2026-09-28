const LEVEL_COLORS = { low: '#2ef2a0', elevated: '#ffb648', high: '#fb923c', critical: '#ff5d5d' }

export default function RingGauge({ risk, persona, trusted }) {
  const score = risk?.score ?? 0
  const level = risk?.level ?? 'low'
  const color = LEVEL_COLORS[level] || '#7d8b9e'

  const r = 96, cx = 120, cy = 120, sw = 14
  const circ = 2 * Math.PI * r
  const frac = Math.min(100, score) / 100

  return (
    <div className="dial-wrap">
      <svg width="240" height="240" viewBox="0 0 240 240">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#161f29" strokeWidth={sw} />
        {/* ticks */}
        {Array.from({ length: 20 }, (_, i) => {
          const a = (i / 20) * Math.PI * 2
          const inr = r - sw / 2 - 5
          return <line key={i}
            x1={cx + inr * Math.cos(a)} y1={cy + inr * Math.sin(a)}
            x2={cx + (inr - 4) * Math.cos(a)} y2={cy + (inr - 4) * Math.sin(a)}
            stroke="#2a3a4c" strokeWidth="1.5" />
        })}
        {score > 0.5 && (
          <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={sw}
                  strokeLinecap="round"
                  strokeDasharray={`${circ * frac} ${circ}`}
                  transform={`rotate(-90 ${cx} ${cy})`}
                  style={{ transition: 'stroke-dasharray 500ms cubic-bezier(0.23,1,0.32,1), stroke 300ms' }} />)}
        <text x={cx} y={cy - 4} textAnchor="middle" className="dial-score"
              fill={color} style={{ fontSize: 52, fontWeight: 800 }}>
          {Math.round(score)}
        </text>
        <text x={cx} y={cy + 22} textAnchor="middle" className="dial-level" fill={color}>
          {level}
        </text>
        <text x={cx} y={cy + 44} textAnchor="middle" fill="#4a5868" style={{ fontSize: 10 }}>
          SCAM RISK / 100
        </text>
      </svg>
      <div className="dial-type">{risk?.action}</div>
      <div className="badges" style={{ marginTop: 8, justifyContent: 'center' }}>
        {trusted && <span className="badge trusted">codeword ✓ trusted</span>}
        {persona === 'waster' && <span className="badge persona">honeypot engaged</span>}
        {risk?.scam_type && risk.scam_type !== 'legitimate_or_unknown' &&
          <span className="badge cat">{risk.scam_type.replaceAll('_', ' ')}</span>}
      </div>
    </div>
  )
}
