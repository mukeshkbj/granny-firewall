const CAT_COLORS = {
  impersonation: '#ff5d5d', urgency_threat: '#fb923c', payment_vector: '#ef4444',
  credential_phishing: '#e879f9', isolation: '#ffb648',
  too_good_to_be_true: '#a3e635', grandparent_emergency: '#f472b6',
}

export default function MarkerFeed({ markers }) {
  return (
    <div className="markers">
      {markers.length === 0 && (
        <div style={{ color: 'var(--faint)', fontSize: 12, lineHeight: 1.6 }}>
          No scam signals yet. The wire is watching every word — rules, the
          agent's own flags, and an LLM classifier all feed this rail.
        </div>
      )}
      {[...markers].reverse().map((m, i) => (
        <div className="marker" key={i}
             style={{ borderLeftColor: CAT_COLORS[m.category] || 'var(--hostile)' }}>
          <div className="top">
            <span className="cat" style={{ color: CAT_COLORS[m.category] || 'var(--hostile)' }}>
              {m.label || m.category.replaceAll('_', ' ')}
            </span>
            <span className="meta">
              <span className="src">{m.source}</span>
              <span className="w">+{m.weight}</span>
            </span>
          </div>
          <div className="quote">“{m.quote}”</div>
        </div>
      ))}
    </div>
  )
}
