import { useEffect, useRef } from 'react'

const SPEAKER_LABELS = { caller: 'caller', agent: 'firewall' }

export default function TranscriptPane({ lines, flaggedIdx, mode }) {
  const ref = useRef(null)
  useEffect(() => { ref.current?.scrollTo(0, ref.current.scrollHeight) }, [lines])

  const callerLabel = mode === 'botfight' ? 'scammer' : 'caller'

  return (
    <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      <h3>Live transcript</h3>
      <div className="transcript" ref={ref}>
        {lines.length === 0 && (
          <div style={{ color: 'var(--dim)', fontSize: 13 }}>
            Waiting for a call… pick a mode above and start.
          </div>
        )}
        {lines.map((l, i) => (
          <div key={i}
               className={`line ${l.speaker} ${flaggedIdx.has(i) ? 'flagged' : ''}`}>
            <div className="who">
              {l.speaker === 'caller' ? callerLabel : SPEAKER_LABELS[l.speaker] || l.speaker}
            </div>
            <div className="what">
              {l.final === false ? <span className="partial">{l.text}</span> : l.text}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
