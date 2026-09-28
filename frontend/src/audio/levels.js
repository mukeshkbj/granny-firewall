/** Shared live audio levels (0..1 RMS), written by capture/playback,
 * read by the scope every animation frame. */
export const levels = { caller: 0, agent: 0 }

export function rmsOfInt16(buf) {
  const a = new Int16Array(buf)
  if (!a.length) return 0
  let s = 0
  for (let i = 0; i < a.length; i += 4) s += a[i] * a[i]   // ¼-sample for speed
  return Math.min(1, Math.sqrt(s / (a.length / 4)) / 12000)
}
