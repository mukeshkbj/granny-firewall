// Captures mic frames and posts Int16 PCM (at the AudioContext's rate)
// to the main thread via port messages.
class PcmCapture extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0] && inputs[0][0]
    if (ch && ch.length) {
      const out = new Int16Array(ch.length)
      for (let i = 0; i < ch.length; i++) {
        out[i] = Math.max(-32768, Math.min(32767, ch[i] * 32767))
      }
      this.port.postMessage(out.buffer, [out.buffer])
    }
    return true
  }
}
registerProcessor('pcm-capture', PcmCapture)
