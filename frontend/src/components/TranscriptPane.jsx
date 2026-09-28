import { useEffect, useRef } from 'react'

export default function TranscriptPane({ lines, flaggedIdx, mode }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollTo(0, ref.current.scrollHeight) }, [lines])

  const callerLabel = mode === 'botfight' ? 'scammer agent'
    : mode === 'replay' ? 'scammer' : 'caller'
  const callerIcon = mode === 'botfight' ? '🤖' : '📞'
  const labelFor = (s) =>
    s === 'caller' ? [callerLabel, callerIcon]
    : s === 'victim' ? ['grandma', '👵']
    : ['firewall', '🛡']

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
            <div className="avatar">{labelFor(l.speaker)[1]}</div>
            <div>
              <div className="who">{labelFor(l.speaker)[0]}</div>
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
