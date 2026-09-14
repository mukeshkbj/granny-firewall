export default function ThreatReport({ report, onClose }) {
  if (!report) return null
  const v = report.verdict || {}
  const u = report.understanding || {}
  return (
    <div className="panel report" style={{ position: 'absolute', inset: 12, zIndex: 20, background: 'var(--panel-2)', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <h3>Threat report · call {report.call_id}</h3>
        <button className="btn-sec" onClick={onClose} style={{ cursor: 'pointer' }}>close</button>
      </div>
      <div className="verdict">
        {v.scam_type ? v.scam_type.replaceAll('_', ' ').toUpperCase() : report.detector?.scam_type?.replaceAll('_', ' ')}
        {v.risk_score != null && <span style={{ color: 'var(--red)' }}> · {v.risk_score}/100</span>}
      </div>
      {v.summary && <p style={{ color: 'var(--dim)' }}>{v.summary}</p>}
      <dl>
        <dt>Claimed identity</dt><dd>{v.caller_claimed_identity || '—'}</dd>
        <dt>Money asked</dt><dd>{(v.money_amounts || []).join(', ') || '—'}</dd>
        <dt>Detector score</dt><dd>{report.detector?.score}/100 ({report.detector?.level})</dd>
        <dt>Markers</dt><dd>{report.markers?.length || 0}</dd>
        <dt>Trusted caller</dt><dd>{report.trusted ? 'yes — codeword verified' : 'no'}</dd>
        <dt>Passed through</dt><dd>{report.passed_to_family ? 'yes' : 'no'}</dd>
      </dl>
      {v.red_flags?.length > 0 && <>
        <h3>Red flags</h3>
        <ul>{v.red_flags.map((f, i) => <li key={i}>{f}</li>)}</ul></>}
      {v.recommended_actions?.length > 0 && <>
        <h3>Recommended actions</h3>
        <ul>{v.recommended_actions.map((f, i) => <li key={i}>{f}</li>)}</ul></>}
      {u.entities?.length > 0 && <>
        <h3>Entities (PII-redacted transcript)</h3>
        <div className="chips" style={{ justifyContent: 'flex-start' }}>
          {u.entities.map((e, i) => <span key={i} className="chip">{e.text} · {e.type}</span>)}
        </div></>}
      {u.highlights?.length > 0 && <>
        <h3>Key moments</h3>
        <ul>{u.highlights.map((h, i) => <li key={i}>{h.text}</li>)}</ul></>}
      {v.error && <p style={{ color: 'var(--amber)' }}>{v.error}</p>}
    </div>
  )
}
