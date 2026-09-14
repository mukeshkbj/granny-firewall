import { useRef, useState } from 'react'
import useDashboardSocket from './useDashboardSocket.js'
import { startCapture } from './audio/capture.js'
import { createPlayer } from './audio/playback.js'
import TranscriptPane from './components/TranscriptPane.jsx'
import MarkerFeed from './components/MarkerFeed.jsx'
import RiskGauge from './components/RiskGauge.jsx'
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
  const [report, setReport] = useState(null)
  const [alert, setAlert] = useState(null)
  const [callId, setCallId] = useState(null)
  const [samples, setSamples] = useState([])
  const [file, setFile] = useState(null)
  const [speed, setSpeed] = useState(1)

  const callWs = useRef(null)
  const stopCapture = useRef(null)
  const player = useRef(createPlayer())

  const onEvent = (ev) => {
    switch (ev.type) {
      case 'state':
        if (ev.risk) setRisk(ev.risk)
        if (ev.persona) setPersona(ev.persona)
        if (ev.mode) setMode(ev.mode)
        break
      case 'call_started':
        setLines([]); setMarkers([]); setFlagged(new Set())
        setRisk(null); setReport(null); setAlert(null)
        setPersona('screener'); setTrusted(false)
        setCallId(ev.call_id); setActive(true)
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
        setRisk(ev); setTrusted(!!ev.trusted)
        break
      case 'tool_call':
        if (ev.name === 'set_persona') setPersona(ev.arguments?.persona || 'screener')
        if (ev.name === 'verify_codeword' && /verified/i.test(ev.result || '')) setTrusted(true)
        if (ev.name === 'whisper_alert') setAlert(ev.arguments?.summary || 'Family alerted')
        break
      case 'call_audio':
        player.current.playB64(ev.audio)
        break
      case 'interrupted':
        player.current.flush()
        break
      case 'report':
        setReport(ev.report); setActive(false)
        break
      case 'call_ended': case 'analysis_done': case 'session_closed':
        setActive(false)
        break
      case 'error':
        setAlert(`Error: ${ev.detail}`)
        break
    }
  }
  useDashboardSocket(onEvent)

  // ---- live mode -------------------------------------------------------
  const startLive = async () => {
    setReport(null)
    const ws = new WebSocket(`ws://${location.host}/ws/call`)
    callWs.current = ws
    ws.binaryType = 'arraybuffer'
    ws.onmessage = (e) => { if (e.data instanceof ArrayBuffer) player.current.play(e.data) }
    ws.onclose = () => setActive(false)
    await new Promise((r) => { ws.onopen = r })
    stopCapture.current = await startCapture(ws)   // sends {type:'start',rate}
  }
  const stopLive = () => {
    try { callWs.current?.send(JSON.stringify({ type: 'stop' })) } catch {}
    stopCapture.current?.()
    callWs.current?.close()
  }

  // ---- analyze mode ----------------------------------------------------
  const runAnalysis = async () => {
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    await fetch(`/api/analyze?speed=${speed}`, { method: 'POST', body: fd })
  }

  // ---- botfight ---------------------------------------------------------
  const startBotfight = () => fetch('/api/botfight?cap_s=180', { method: 'POST' })
  const stopAll = () => fetch('/api/call/stop', { method: 'POST' })
  const makeReport = () => fetch('/api/report', { method: 'POST' })
    .then((r) => r.json()).then((r) => r.report ? setReport(r.report) : setReport(r))

  return (
    <div className="app">
      <header>
        <div className="logo">🛡 Granny<em>Firewall</em></div>
        <div className="tagline">every call screened · every scammer stalled</div>
        <span className={`status-dot ${active ? 'on' : ''}`} />
        <span style={{ color: 'var(--dim)', fontSize: 11 }}>
          {active ? `call ${callId || ''} live` : 'idle'}
        </span>
        <nav className="modes">
          {[['live', '🎙 Live screen'], ['analyze', '📼 Analyze a call'],
            ['botfight', '🤖 Botfight']].map(([m, label]) => (
            <button key={m} className={mode === m ? 'active' : ''}
                    onClick={() => { setMode(m); if (m === 'analyze') fetch('/api/samples').then(r => r.json()).then(setSamples) }}>
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        <div className="col" style={{ position: 'relative' }}>
          <div className="panel controls">
            {mode === 'live' && (<>
              {!active
                ? <button className="btn-start" onClick={startLive}>Answer the phone</button>
                : <button className="btn-stop" onClick={stopLive}>Hang up</button>}
              {!active && callId &&
                <button className="btn-sec" onClick={makeReport}>Threat report</button>}
              <span className="hint">
                You are the caller. Try to get past Ethel's firewall — or say the codeword.
              </span>
            </>)}
            {mode === 'analyze' && (<>
              <input type="file" accept="audio/*" onChange={(e) => setFile(e.target.files[0])} />
              {samples.length > 0 && (
                <select defaultValue="" onChange={(e) => e.target.value &&
                  fetch(`/api/analyze_sample?name=${e.target.value}&speed=${speed}`,
                        { method: 'POST' })}>
                  <option value="" disabled>or pick a sample…</option>
                  {samples.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>)}
              <select value={speed} onChange={(e) => setSpeed(+e.target.value)}>
                <option value={1}>real time</option><option value={2}>2×</option>
                <option value={4}>4×</option>
              </select>
              <button className="btn-start" onClick={runAnalysis} disabled={!file || active}>
                Analyze
              </button>
              {active && <button className="btn-stop" onClick={stopAll}>Stop</button>}
              <span className="hint">Drop a scam-call recording — watch markers land live.</span>
            </>)}
            {mode === 'botfight' && (<>
              {!active
                ? <button className="btn-start" onClick={startBotfight}>Start the duel</button>
                : <button className="btn-stop" onClick={stopAll}>Stop</button>}
              <span className="hint">
                A scripted scammer agent calls the firewall. Both sides audible. 3 min cap.
              </span>
            </>)}
          </div>

          <TranscriptPane lines={lines} flaggedIdx={flagged} mode={mode} />
          {report && <ThreatReport report={report} onClose={() => setReport(null)} />}
        </div>

        <div className="col">
          <RiskGauge risk={risk} persona={persona} trusted={trusted} />
          <MarkerFeed markers={markers} />
        </div>
      </main>

      {alert && <div className="alert-banner" onClick={() => setAlert(null)}>
        🔔 {alert}
      </div>}
    </div>
  )
}
