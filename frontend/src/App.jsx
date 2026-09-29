import { useEffect, useRef, useState } from 'react'
import useDashboardSocket from './useDashboardSocket.js'
import { startCapture } from './audio/capture.js'
import { createPlayer } from './audio/playback.js'
import TranscriptPane from './components/TranscriptPane.jsx'
import MarkerFeed from './components/MarkerFeed.jsx'
import RingGauge from './components/RingGauge.jsx'
import ScopeWave from './components/ScopeWave.jsx'
import VerdictStamp from './components/VerdictStamp.jsx'
import ThreatReport from './components/ThreatReport.jsx'

export default function App() {
  const [mode, setMode] = useState('live')
  const [active, setActive] = useState(false)
  const [lines, setLines] = useState([])
  const [flagged, setFlagged] = useState(new Set())
  const [markers, setMarkers] = useState([])
  const [risk, setRisk] = useState(null)
  const [persona, setPersona] = useState('screener')
  const [trusted, setTrusted] = useState(false)
  const [passed, setPassed] = useState(false)
  const [report, setReport] = useState(null)
  const [stamp, setStamp] = useState(false)
  const [alert, setAlert] = useState(null)
  const [callId, setCallId] = useState(null)
  const [samples, setSamples] = useState([])
  const [file, setFile] = useState(null)
  const [speed, setSpeed] = useState(1)
  const [elapsed, setElapsed] = useState(0)

  const callWs = useRef(null)
  const stopCapture = useRef(null)
  const player = useRef(createPlayer())
  const callStart = useRef(0)
  const riskRef = useRef(null)

  const onEvent = (ev) => {
    switch (ev.type) {
      case 'state':
        if (ev.risk) { setRisk(ev.risk); riskRef.current = ev.risk }
        if (ev.persona) setPersona(ev.persona)
        if (ev.mode) setMode(ev.mode)
        break
      case 'call_started':
        setLines([]); setMarkers([]); setFlagged(new Set())
        setRisk(null); riskRef.current = null
        setReport(null); setAlert(null); setStamp(false)
        setPersona('screener'); setTrusted(false); setPassed(false)
        setCallId(ev.call_id); setActive(true)
        callStart.current = Date.now()
        if (ev.mode) setMode(ev.mode)
        break
      case 'transcript':
        setLines((ls) => {
          const last = ls[ls.length - 1]
          if (ev.final === false && last && !last.final && last.speaker === ev.speaker)
            return [...ls.slice(0, -1), { ...ev, idx: last.idx }]
          return [...ls, { ...ev, idx: ls.length }]
        })
        break
      case 'marker':
        setMarkers((m) => [...m, ev])
        setLines((ls) => {
          const i = ls.map((l) => l.speaker).lastIndexOf('caller')
          if (i >= 0) setFlagged((f) => new Set(f).add(i))
          return ls
        })
        break
      case 'risk':
        setRisk(ev); riskRef.current = ev; setTrusted(!!ev.trusted)
        break
      case 'tool_call':
        if (ev.name === 'set_persona') setPersona(ev.arguments?.persona || 'screener')
        if (ev.name === 'verify_codeword' && /verified/i.test(ev.result || '')) setTrusted(true)
        if (ev.name === 'pass_to_family') setPassed(true)
        if (ev.name === 'whisper_alert') setAlert(ev.arguments?.summary || 'Family alerted')
        break
      case 'call_audio':
        player.current.playB64(ev.audio, ev.speaker)
        break
      case 'interrupted':
        player.current.flush()
        break
      case 'report':
        setReport(ev.report); setActive(false)
        break
      case 'call_ended': case 'analysis_done': case 'session_closed':
        setActive(false)
        if (riskRef.current || markers.length) setStamp(true)
        break
      case 'error':
        setAlert(`Error: ${ev.detail}`)
        break
    }
  }
  useDashboardSocket(onEvent)

  useEffect(() => {
    if (!active) return
    const t = setInterval(() => setElapsed((Date.now() - callStart.current) / 1000), 500)
    return () => clearInterval(t)
  }, [active])

  // ---- live mode -------------------------------------------------------
  const startLive = async () => {
    setReport(null); setStamp(false)
    const ws = new WebSocket(`ws://${location.host}/ws/call`)
    callWs.current = ws
    ws.binaryType = 'arraybuffer'
    ws.onmessage = (e) => { if (e.data instanceof ArrayBuffer) player.current.play(e.data, 'agent') }
    ws.onclose = () => setActive(false)
    await new Promise((r) => { ws.onopen = r })
    stopCapture.current = await startCapture(ws)
  }
  const stopLive = () => {
    try { callWs.current?.send(JSON.stringify({ type: 'stop' })) } catch {}
    stopCapture.current?.()
    callWs.current?.close()
  }

  // ---- analyze / botfight ----------------------------------------------
  const runAnalysis = async () => {
    if (!file) return
    const fd = new FormData(); fd.append('file', file)
    await fetch(`/api/analyze?speed=${speed}`, { method: 'POST', body: fd })
  }
  const startBotfight = () => fetch('/api/botfight?cap_s=180', { method: 'POST' })
  const stopAll = () => fetch('/api/call/stop', { method: 'POST' })
  const makeReport = () => fetch('/api/report', { method: 'POST' })
    .then((r) => r.json()).then((r) => r.report ? setReport(r.report) : setReport(r))

  const level = risk?.level || 'low'
  const statusCls = active ? (level === 'high' || level === 'critical' ? 'threat' : 'live') : ''
  const statusTxt = !active ? 'line secured'
    : level === 'high' || level === 'critical' ? 'threat active' : 'screening call'

  const mm = String(Math.floor(elapsed / 60)).padStart(2, '0')
  const ss = String(Math.floor(elapsed % 60)).padStart(2, '0')

  return (
    <div className="app">
      <header>
        <div className="logo">GRANNY<span className="x">//</span>FIREWALL</div>
        <div className="tagline">the bouncer at grandma's phone line</div>
        <span className={`status-pill ${statusCls}`}>
          <span className="dot" />{statusTxt}{callId && active ? ` · ${callId}` : ''}
        </span>
        <nav className="modes">
          {[['live', 'live screen'], ['replay', 'replay'], ['analyze', 'analyze'], ['botfight', 'botfight']].map(([m, label]) => (
            <button key={m} className={mode === m ? 'active' : ''}
                    onClick={() => { setMode(m); if (m === 'analyze') fetch('/api/samples').then(r => r.json()).then(setSamples) }}>
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        <div className="col" style={{ position: 'relative' }}>
          <div className={`panel stage ${level === 'high' || level === 'critical' ? 'threat' : ''}`}>
            <RingGauge risk={risk} persona={persona} trusted={trusted} />
            <div className="scope-wrap">
              <div className="scope-row">
                <span className="who-dot" style={{ background: 'var(--hostile)' }} />
                <span className="name">{mode === 'botfight' || mode === 'replay' ? 'scammer' : 'caller'}</span>
                <span style={{ color: 'var(--faint)', flex: 1 }}>▲ hostile audio</span>
                <span className="who-dot" style={{ background: 'var(--guard)' }} />
                <span className="name" style={{ width: 'auto' }}>{mode === 'replay' ? 'grandma ▼' : 'firewall ▼'}</span>
              </div>
              <ScopeWave active={active} />
              <div className="controls">
                {mode === 'live' && (<>
                  {!active
                    ? <button className="btn-start" onClick={startLive}>▶ Answer the phone</button>
                    : <button className="btn-stop" onClick={stopLive}>■ Hang up</button>}
                  {!active && callId &&
                    <button onClick={makeReport}>Threat report</button>}
                </>)}
                {mode === 'replay' && (<>
                  {!active
                    ? <button className="btn-start" onClick={() => fetch(`/api/replay?speed=${speed}`, { method: 'POST' })}>▶ Replay the scam call</button>
                    : <button className="btn-stop" onClick={stopAll}>■ Stop</button>}
                  <select value={speed} onChange={(e) => setSpeed(+e.target.value)}>
                    <option value={1}>1×</option><option value={2}>2×</option>
                    <option value={4}>4×</option>
                  </select>
                </>)}
                {mode === 'analyze' && (<>
                  <input type="file" accept="audio/*" onChange={(e) => setFile(e.target.files[0])} />
                  {samples.length > 0 && (
                    <select defaultValue="" onChange={(e) => e.target.value &&
                      fetch(`/api/analyze_sample?name=${e.target.value}&speed=${speed}`,
                            { method: 'POST' })}>
                      <option value="" disabled>pick a sample…</option>
                      {samples.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>)}
                  <select value={speed} onChange={(e) => setSpeed(+e.target.value)}>
                    <option value={1}>1×</option><option value={2}>2×</option>
                    <option value={4}>4×</option>
                  </select>
                  <button className="btn-start" onClick={runAnalysis} disabled={!file || active}>
                    Analyze
                  </button>
                  {active && <button className="btn-stop" onClick={stopAll}>Stop</button>}
                </>)}
                {mode === 'botfight' && (<>
                  {!active
                    ? <button className="btn-start" onClick={startBotfight}>⚔ Start the duel</button>
                    : <button className="btn-stop" onClick={stopAll}>■ Stop</button>}
                </>)}
                <span className="hint">
                  {mode === 'live' && 'You play the caller. Run a scam — or say the family codeword to get passed through.'}
                  {mode === 'replay' && 'A recorded IRS-scam attempt plays on the wire. Runs fully offline — no key needed.'}
                  {mode === 'analyze' && 'Feed the wire a recorded call. Watch every scam signal land live.'}
                  {mode === 'botfight' && 'A scripted scammer agent calls the firewall. Two voices, one wire. 3 min cap.'}
                </span>
              </div>
            </div>
          </div>

          <TranscriptPane lines={lines} flaggedIdx={flagged} mode={mode} />
          {stamp && !report && (
            <VerdictStamp risk={risk} trusted={trusted} passed={passed}
                          mode={mode} onClose={() => setStamp(false)} />)}
          {report && <ThreatReport report={report} onClose={() => setReport(null)} />}
        </div>

        <div className="col">
          <div className="panel">
            <h3>Call stats</h3>
            <div className="stats">
              <div className="stat"><div className="v">{mm}:{ss}</div><div className="k">on the line</div></div>
              <div className="stat"><div className="v" style={{ color: 'var(--hostile)' }}>{markers.length}</div><div className="k">markers</div></div>
              <div className="stat"><div className="v">{lines.filter((l) => l.speaker === 'caller').length}</div><div className="k">caller turns</div></div>
            </div>
          </div>
          <div className="panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            <h3>Threat intel</h3>
            <MarkerFeed markers={markers} />
          </div>
        </div>
      </main>

      {alert && <div className="alert-banner" onClick={() => setAlert(null)}>🔔 {alert}</div>}
    </div>
  )
}
