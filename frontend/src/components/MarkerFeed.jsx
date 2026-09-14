const CAT_COLORS = {
  impersonation: '#f87171', urgency_threat: '#fb923c', payment_vector: '#ef4444',
  credential_phishing: '#e879f9', isolation: '#fbbf24',
  too_good_to_be_true: '#a3e635', grandparent_emergency: '#f472b6',
}

export default function MarkerFeed({ markers }) {
  return (
    <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <h3>Detected markers ({markers.length})</h3>
      <div className="markers">
        {markers.length === 0 && (
          <div style={{ color: 'var(--dim)', fontSize: 12 }}>
            No scam signals yet. The detector watches every word the caller says.
          </div>
        )}
        {[...markers].reverse().map((m, i) => (
          <div className="marker" key={i}>
            <div className="top">
              <span className="cat" style={{ color: CAT_COLORS[m.category] || 'var(--red)' }}>
                {m.label || m.category.replaceAll('_', ' ')}
              </span>
              <span>
                <span className="src">{m.source}</span>{' '}
                <span className="w">+{m.weight}</span>
              </span>
            </div>
            <div className="quote">“{m.quote}”</div>
          </div>
        ))}
      </div>
    </div>
  )
}
