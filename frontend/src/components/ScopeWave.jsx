import { useEffect, useRef } from 'react'
import { levels } from '../audio/levels.js'

/** The wire: a live dual-channel oscilloscope. Caller energy draws
 * upward in hostile red, firewall energy downward in guard green.
 * Scrolling history — the "conversation waveform" as the signature visual. */
export default function ScopeWave({ active }) {
  const ref = useRef(null)

  useEffect(() => {
    const canvas = ref.current
    const c2d = canvas.getContext('2d')
    const W = 600, H = 96
    canvas.width = W * devicePixelRatio
    canvas.height = H * devicePixelRatio
    c2d.scale(devicePixelRatio, devicePixelRatio)

    const histCaller = new Float32Array(W)
    const histAgent = new Float32Array(W)
    let raf, t = 0

    const draw = () => {
      t++
      // sample live levels each frame, decay toward 0 when idle
      histCaller.copyWithin(0, 1); histAgent.copyWithin(0, 1)
      histCaller[W - 1] = active ? Math.min(1, levels.caller * 1.6) : 0
      histAgent[W - 1] = active ? Math.min(1, levels.agent * 1.6) : 0
      levels.caller *= 0.82; levels.agent *= 0.82

      c2d.clearRect(0, 0, W, H)
      // center line
      c2d.strokeStyle = '#1b2632'
      c2d.beginPath(); c2d.moveTo(0, H / 2); c2d.lineTo(W, H / 2); c2d.stroke()

      // caller = up (red), agent = down (green)
      for (const [hist, color, dir] of [
        [histCaller, '#ff5d5d', -1], [histAgent, '#2ef2a0', 1]]) {
        c2d.beginPath()
        c2d.moveTo(0, H / 2)
        for (let x = 0; x < W; x++) {
          const amp = hist[x] * (H / 2 - 6)
          const wob = amp * (0.55 + 0.45 * Math.sin(x * 0.35 + t * 0.3))
          c2d.lineTo(x, H / 2 + dir * Math.max(0.4, wob))
        }
        for (let x = W - 1; x >= 0; x--) c2d.lineTo(x, H / 2)
        c2d.closePath()
        c2d.fillStyle = color + '22'
        c2d.fill()
        c2d.strokeStyle = color
        c2d.lineWidth = 1.4
        c2d.beginPath()
        c2d.moveTo(0, H / 2)
        for (let x = 0; x < W; x++) {
          const amp = hist[x] * (H / 2 - 6)
          const wob = amp * (0.55 + 0.45 * Math.sin(x * 0.35 + t * 0.3))
          c2d.lineTo(x, H / 2 + dir * Math.max(0.4, wob))
        }
        c2d.stroke()
      }
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [active])

  return <canvas ref={ref} className="scope" />
}
