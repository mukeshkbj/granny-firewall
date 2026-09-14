/** Streaming PCM16 playback: schedules each chunk back-to-back and tracks
 * sources so flush() can hard-stop on barge-in. */
export function createPlayer() {
  let ctx = null
  let nextTime = 0
  let sources = new Set()

  const ensure = () => {
    if (!ctx) {
      try { ctx = new AudioContext({ sampleRate: 24000 }) }
      catch { ctx = new AudioContext() }
      nextTime = ctx.currentTime
    }
    return ctx
  }

  return {
    play(pcm) {  // ArrayBuffer of Int16 at ctx.sampleRate
      const c = ensure()
      const n = pcm.byteLength / 2
      if (!n) return
      const i16 = new Int16Array(pcm)
      const f32 = new Float32Array(n)
      for (let i = 0; i < n; i++) f32[i] = i16[i] / 32768
      const buf = c.createBuffer(1, n, c.sampleRate)
      buf.copyToChannel(f32, 0)
      const src = c.createBufferSource()
      src.buffer = buf
      src.connect(c.destination)
      src.onended = () => sources.delete(src)
      sources.add(src)
      nextTime = Math.max(nextTime, c.currentTime)
      src.start(nextTime)
      nextTime += buf.duration
    },
    playB64(b64) {
      const bin = atob(b64)
      const bytes = new Uint8Array(bin.length)
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
      this.play(bytes.buffer)
    },
    flush() {
      sources.forEach((s) => { try { s.stop() } catch {} })
      sources.clear()
      if (ctx) nextTime = ctx.currentTime
    },
    close() { this.flush(); ctx?.close(); ctx = null },
  }
}
