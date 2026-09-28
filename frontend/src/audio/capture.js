import { levels, rmsOfInt16 } from './levels.js'

/** Mic capture: AudioWorklet → Int16 PCM at the AudioContext's rate →
 * binary WS frames. Requests a 24kHz context (supported in modern
 * browsers); server resamples if the platform ignores it. */
export async function startCapture(ws) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
  })
  let ctx
  try { ctx = new AudioContext({ sampleRate: 24000 }) } catch { ctx = new AudioContext() }
  ws.send(JSON.stringify({ type: 'start', rate: ctx.sampleRate }))

  const src = ctx.createMediaStreamSource(stream)
  await ctx.audioWorklet.addModule('/pcm-worklet.js')
  const node = new AudioWorkletNode(ctx, 'pcm-capture')
  node.port.onmessage = (e) => {
    levels.caller = rmsOfInt16(e.data)
    if (ws.readyState === 1) ws.send(e.data)
  }
  src.connect(node)

  return () => {
    node.disconnect(); src.disconnect()
    stream.getTracks().forEach((t) => t.stop())
    ctx.close()
  }
}
