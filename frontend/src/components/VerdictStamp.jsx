/** Big rotated verdict stamp that slams onto the call stage when a call ends. */
export default function VerdictStamp({ risk, trusted, passed, mode, onClose }) {
  if (!risk) return null
  const score = risk.score ?? 0
  let cls, title, sub
  if (passed || trusted) {
    cls = 'passed'; title = 'CALL PASSED'; sub = 'verified caller · sent through'
  } else if (score >= 60) {
    cls = 'blocked'; title = mode === 'botfight' ? 'SCAMMER CONTAINED' : 'SCAM BLOCKED'
    sub = `risk ${Math.round(score)}/100 · report generated`
  } else if (score >= 30) {
    cls = 'sus'; title = 'SUSPICIOUS'; sub = `risk ${Math.round(score)}/100 · logged`
  } else {
    cls = 'passed'; title = 'LINE CLEAR'; sub = 'no scam signals detected'
  }
  return (
    <div className="stamp-wrap" onClick={onClose}>
      <div className={`stamp ${cls}`}>{title}<small>{sub} · click to dismiss</small></div>
    </div>
  )
}
