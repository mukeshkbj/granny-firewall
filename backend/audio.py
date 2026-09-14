"""Audio helpers: decode any media file to PCM16 mono at a target rate.

Uses soundfile (bundled libsndfile: wav/flac/ogg/mp3) + numpy linear
resampling — no ffmpeg system dependency. For best fidelity on odd formats,
scripts/convert_audio.sh uses ffmpeg when available.
"""

import numpy as np
import soundfile as sf

CHUNK_MS = 50  # ~50ms chunks for low-latency streaming


def load_pcm16(path: str, target_rate: int = 24000) -> tuple[bytes, int]:
    """Decode an audio file to PCM16 mono bytes at target_rate."""
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != target_rate:
        n_out = int(len(mono) * target_rate / rate)
        mono = np.interp(
            np.linspace(0, len(mono) - 1, n_out), np.arange(len(mono)), mono
        ).astype(np.float32)
    pcm = np.clip(mono, -1.0, 1.0)
    return (pcm * 32767).astype("<i2").tobytes(), target_rate


def chunk_bytes(pcm: bytes, rate: int, ms: int = CHUNK_MS):
    """Yield (chunk, duration_s) pairs of ~ms milliseconds each."""
    size = int(rate * 2 * ms / 1000)
    for i in range(0, len(pcm), size):
        piece = pcm[i : i + size]
        if piece:
            yield piece, len(piece) / (rate * 2)


def resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    """Linear-interp resample of PCM16 mono — good enough for speech."""
    if src_rate == dst_rate or not pcm:
        return pcm
    a = np.frombuffer(pcm, dtype="<i2").astype(np.float32)
    n_out = int(len(a) * dst_rate / src_rate)
    if n_out <= 0:
        return b""
    out = np.interp(np.linspace(0, len(a) - 1, n_out), np.arange(len(a)), a)
    return np.clip(out, -32768, 32767).astype("<i2").tobytes()


def pcm16_to_float32(pcm: bytes) -> np.ndarray:
    return np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32767.0


def wav_bytes(pcm: bytes, rate: int) -> bytes:
    """Wrap raw PCM16 in a WAV container (for saving call audio)."""
    import io

    buf = io.BytesIO()
    sf.write(buf, pcm16_to_float32(pcm), rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()
