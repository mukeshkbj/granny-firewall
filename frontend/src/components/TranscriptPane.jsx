import { useEffect, useRef } from 'react'

export default function TranscriptPane({ lines, flaggedIdx, mode }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollTo(0, ref.current.scrollHeight) }, [lines])

  const callerLabel = mode === 'botfight' ? 'scammer agent' : 'caller'
  const callerIcon = mode === 'botfight' ? '🤖' : '📞'

  return (
    <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <h3>Live intercept</h3>
      <div className="transcript" ref={ref}>
        {lines.length === 0 && (
          <div className="empty-state">
            <div className="big">The line is quiet.</div>
            Pick a mode and start a call — every word the caller says is
            screened in real time.
          </div>
        )}
        {lines.map((l, i) => (
          <div key={i} className={`bubble ${l.speaker} ${flaggedIdx.has(i) ? 'flagged' : ''}`}>
            <div className="avatar">{l.speaker === 'caller' ? callerIcon : '🛡'}</div>
            <div>
              <div className="who">{l.speaker === 'caller' ? callerLabel : 'firewall'}</div>
              <div className="body">
                {l.final === false ? <span className="partial">{l.text}</span> : l.text}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
