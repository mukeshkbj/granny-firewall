const LEVEL_COLORS = { low: '#34d399', elevated: '#fbbf24', high: '#fb923c', critical: '#f87171' }

export default function RiskGauge({ risk, persona, trusted }) {
  const score = risk?.score ?? 0
  const level = risk?.level ?? 'low'
  const color = LEVEL_COLORS[level] || '#8b98ab'
  // semicircle: -90deg..90deg needle sweep
  const angle = -90 + (Math.min(100, score) / 100) * 180
  const r = 70, cx = 90, cy = 85

  const arc = (a0, a1) => {
    const p = (a) => [cx + r * Math.cos((a * Math.PI) / 180), cy + r * Math.sin((a * Math.PI) / 180)]
    const [x0, y0] = p(a0), [x1, y1] = p(a1)
    return `M ${x0} ${y0} A ${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1}`
  }
  const needleA = (angle - 90) * (Math.PI / 180)
  const nx = cx + (r - 16) * Math.cos(needleA), ny = cy + (r - 16) * Math.sin(needleA)

  return (
    <div className="panel">
      <h3>Scam risk {trusted && <span className="badge trusted">trusted caller</span>}
        {persona === 'waster' && <span className="badge persona">waster mode</span>}</h3>
      <div className="gauge-wrap">
        <svg width="180" height="95" viewBox="0 0 180 95">
          <path d={arc(-180, 0)} fill="none" stroke="#1f2b3a" strokeWidth="12" strokeLinecap="round" />
          <path d={arc(-180, -180 + Math.min(100, score) * 1.8)} fill="none"
                stroke={color} strokeWidth="12" strokeLinecap="round" />
          <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={color} strokeWidth="3" />
          <circle cx={cx} cy={cy} r="5" fill={color} />
        </svg>
        <div className="gauge-num" style={{ color }}>{Math.round(score)}</div>
        <div className="gauge-label" style={{ color }}>{level}</div>
        <div className="gauge-action">{risk?.action}</div>
        <div className="chips">
          {(risk?.categories_hit || []).map((c) => (
            <span key={c} className="chip hit">{c.replaceAll('_', ' ')}</span>
          ))}
        </div>
        {risk?.scam_type && risk.scam_type !== 'legitimate_or_unknown' && (
          <div className="chip hit" style={{ marginTop: 6 }}>
            likely: {risk.scam_type.replaceAll('_', ' ')}
          </div>
        )}
      </div>
    </div>
  )
}
