/** Static-demo replay driver: plays the bundled call through the exact same
 * event stream the backend emits — paced 50ms audio chunks, transcript
 * partials mid-line, detector events per caller line, then the report.
 * Used only when VITE_DEMO=1 (hosted build, no backend). */

const CHUNK_MS = 50

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function loadPcm(url) {
  const buf = await fetch(url).then((r) => r.arrayBuffer())
  const u8 = new Uint8Array(buf)
  // minimal RIFF scan for the data chunk (wav is PCM16 mono 24kHz)
  let off = 12
  while (off + 8 <= u8.length) {
    const id = String.fromCharCode(u8[off], u8[off + 1], u8[off + 2], u8[off + 3])
    const size = new DataView(buf).getUint32(off + 4, true)
    if (id === 'data') return buf.slice(off + 8, off + 8 + size)
    off += 8 + size + (size % 2)
  }
  return buf
}

function b64(bytes) {
  let s = ''
  for (let i = 0; i < bytes.length; i += 4096)
    s += String.fromCharCode.apply(null, bytes.subarray(i, i + 4096))
  return btoa(s)
}

export async function startDemoReplay(emit, speed = 1, stopRef) {
  const script = await fetch('demo_script.json').then((r) => r.json())
  const pcm = await loadPcm(script.wav)
  const RATE = 24000, BYTES_PER_MS = RATE * 2 / 1000
  const totalBytes = Math.floor(script.total_s * 1000 / CHUNK_MS) *
    CHUNK_MS * BYTES_PER_MS

  // push a pcm window [t0,t1) as paced call_audio chunks
  const playSpan = async (t0, t1, speaker) => {
    const ch = speaker === 'caller' ? 'caller' : 'agent'
    for (let t = t0; t < t1; t += CHUNK_MS / 1000) {
      if (stopRef.current) return false
      const s = Math.floor(t * 1000 / CHUNK_MS) * CHUNK_MS * BYTES_PER_MS
      const e = Math.min(s + CHUNK_MS * BYTES_PER_MS, pcm.byteLength, totalBytes)
      if (e <= s) return true
      emit({ type: 'call_audio', speaker: ch, audio: b64(new Uint8Array(pcm, s, e - s)) })
      await sleep(CHUNK_MS / speed)
    }
    return true
  }

  emit({ type: 'call_started', mode: 'replay', call_id: 'demo0001' })
  let t = 0
  for (let i = 0; i < script.lines.length; i++) {
    if (stopRef.current) return
    const line = script.lines[i]
    if (line.start_s > t && !(await playSpan(t, line.start_s, 'caller'))) return
    // play this line, revealing transcript partials at 40% / 75% of words
    const words = line.text.split(' ')
    const marks = [0.4, 0.75].map((f) => Math.floor(words.length * f))
      .filter((m, ix, a) => m > 0 && m < words.length && a.indexOf(m) === ix)
      .sort()
    const dur = line.end_s - line.start_s
    const ch = line.speaker === 'caller' ? 'caller' : 'agent'
    let pos = 0, mi = 0
    for (let lt = 0; lt < dur; lt += CHUNK_MS / 1000) {
      if (stopRef.current) return
      const s = Math.floor((line.start_s + lt) * 1000 / CHUNK_MS) * CHUNK_MS * BYTES_PER_MS
      const e = Math.min(s + CHUNK_MS * BYTES_PER_MS, pcm.byteLength)
      if (e > s)
        emit({ type: 'call_audio', speaker: ch, audio: b64(new Uint8Array(pcm, s, e - s)) })
      pos += CHUNK_MS / 1000
      await sleep(CHUNK_MS / speed)
      while (mi < marks.length && pos >= dur * marks[mi] / words.length) {
        emit({ type: 'transcript', speaker: line.speaker,
               text: words.slice(0, marks[mi]).join(' '), final: false })
        mi++
      }
    }
    emit({ type: 'transcript', speaker: line.speaker, text: line.text, final: true })
    for (const ev of script.per_line[i] || []) emit(ev)
    t = line.end_s
  }
  if (t < script.total_s && !(await playSpan(t, script.total_s, 'caller'))) return
  await sleep(1200 / speed)
  emit({ type: 'call_ended', reason: 'completed' })
  await sleep(2600 / speed)
  if (!stopRef.current) emit({ type: 'report', report: script.report })
}
