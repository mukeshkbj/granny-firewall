"""Build the film's voice track: replay wav slices + interleaved botfight voices.

Timeline: title 0-3.1 | act1 3.2-5.4 | REPLAY 5.5-49.5 | act2 49.6-51.8 |
          BOTFIGHT 51.9-76.4 | end 77.3-80.7
"""
import numpy as np, wave, subprocess

SR = 44100
FILM = 80.7
REPLAY_AT = 5.5
BF_AT = 51.9

def load_wav(path):
    with wave.open(path) as w:
        rate, n = w.getframerate(), w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    return data, rate

def load_raw(path):
    return np.fromfile(path, dtype=np.int16).astype(np.float32) / 32768.0

def resample(x, src, dst=SR):
    if src == dst:
        return x
    idx = np.linspace(0, len(x) - 1, int(len(x) * dst / src))
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)

def place(track, audio, at_s, gain=1.0):
    i = int(at_s * SR)
    end = min(len(track), i + len(audio))
    if end > i:
        track[i:end] += audio[:end - i] * gain

out = np.zeros(int(FILM * SR), dtype=np.float32)

# ---------- replay: slice source wav at call-relative windows ----------
# condense segs (take-time) -> clip out-time; call starts at take 7.4s
segs = [(5.5, 12.5), (20.5, 27.5), (46.5, 53.5), (58.5, 66.5),
        (70.5, 74.5), (88.0, 93.0), (95.5, 101.5)]
CALL_T0 = 7.4
wav, rate = load_wav("/Users/mukeshagrawal/AssemblyAI/samples/irs_scam_call.wav")
wav = resample(wav, rate)

cursor = 0.0
for a, b in segs:
    w0, w1 = a - CALL_T0, b - CALL_T0          # wav-time window
    s0 = max(0, int(w0 * SR)); s1 = min(len(wav), int(w1 * SR))
    piece = wav[s0:s1] if s1 > s0 else np.zeros(0, np.float32)
    lead = int(max(0, -w0) * SR)                # silence if seg starts pre-call
    clip_at = REPLAY_AT + cursor + lead / SR
    place(out, piece, clip_at)
    cursor += (b - a)

# ---------- botfight: silence-split raws into turns, alternate ----------
def turns(pcm, rate=24000, thresh=0.012, min_gap=0.28, min_turn=0.35):
    env = np.abs(pcm)
    k = int(0.02 * rate)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    speech = env > thresh
    gaps, res, start = [], [], None
    for i, s in enumerate(speech):
        if s and start is None:
            start = i
        elif not s and start is not None:
            if (i - start) / rate >= min_turn:
                res.append((start, i))
            start = None
    if start is not None and (len(pcm) - start) / rate >= min_turn:
        res.append((start, len(pcm)))
    # merge turns separated by < min_gap
    merged = []
    for s, e in res:
        if merged and (s - merged[-1][1]) / rate < min_gap:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return [pcm[s:e] for s, e in merged]

scam = turns(load_raw("/Users/mukeshagrawal/AssemblyAI/film/takes/bf5_scammer.raw"))
fw = turns(load_raw("/Users/mukeshagrawal/AssemblyAI/film/takes/bf5_firewall.raw"))
print(f"turns: scammer={len(scam)} firewall={len(fw)}")

# duel order: fw greets, scammer answers, alternating. Lay turns across the
# bf clip segments (clip out-times), conversation flowing across segment cuts.
bf_segs = [(4.5, 12.5), (18.0, 24.0), (47.0, 52.0), (121.5, 127.0)]
# duel-time windows per kept segment (call starts ~take 7.4)
windows = [(a - 7.4, b - 7.4) for a, b in bf_segs]
total = sum(b - a for a, b in windows)

# interleave: fw,sc,fw,sc... distributed across segment windows
seq = []
fi = si = 0
while fi < len(fw) or si < len(scam):
    if fi < len(fw):
        seq.append(("fw", fw[fi])); fi += 1
    if si < len(scam):
        seq.append(("sc", scam[si])); si += 1

# spread turns across windows: fill each window greedily
t_cursor = 0.0
wi = 0
w_start, w_end = windows[0]
for who, pcm in seq:
    dur = len(pcm) / 24000.0
    if t_cursor + dur > w_end - w_start:          # advance window
        wi += 1
        if wi >= len(windows):
            break
        w_start, w_end = windows[wi]
        t_cursor = w_start
    else:
        if t_cursor < w_start:
            t_cursor = w_start
    # film time = BF_AT + clip_out_time(= sum of prior segs + (t_cursor - w_start))
    prior = sum(b - a for a, b in windows[:wi])
    clip_t = prior + (t_cursor - w_start)
    place(out, resample(pcm, 24000), BF_AT + clip_t, gain=0.95)
    t_cursor += dur + 0.35                        # breath between turns

out = np.clip(out, -1, 1)
pcm16 = (out * 32767).astype(np.int16)
with wave.open("/Users/mukeshagrawal/AssemblyAI/film/work/voice.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm16.tobytes())
print("voice.wav", FILM, "s")
