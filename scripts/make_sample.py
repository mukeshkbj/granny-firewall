"""Render a scripted scam call to a WAV using macOS `say` voices.

Two voices alternate (scammer / Ethel). Output: samples/irs_scam_call.wav
Run: .venv/bin/python scripts/make_sample.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples" / "irs_scam_call.wav"

SCAMMER = "Daniel"   # British male — reads as "Officer Miller"
ETHEL = "Victoria"   # older-sounding female

SCRIPT = [
    (SCAMMER, "Hello, am I speaking with Missus Ethel Miller?"),
    (ETHEL, "Yes, this is Ethel. Who is calling?"),
    (SCAMMER, "This is Officer David Miller from the IRS Tax Crime Unit. "
              "Ma'am, a federal arrest warrant has been issued in your name "
              "for tax fraud."),
    (ETHEL, "Oh my goodness, a warrant? That can't be right."),
    (SCAMMER, "You must act within 24 hours or officers will come to your "
              "home. Do you understand the severity, ma'am?"),
    (ETHEL, "Well, I, I don't understand, I always pay my taxes."),
    (SCAMMER, "To cancel the warrant you must pay the outstanding balance "
              "immediately. We accept Apple gift cards. Go to the store and "
              "buy five cards of five hundred dollars each."),
    (ETHEL, "Gift cards? My grandson buys me those at Christmas."),
    (SCAMMER, "Stay on the line. Do not tell your family or anyone about "
              "this call — this is a sensitive federal case."),
    (ETHEL, "Oh dear. Hold on, let me find my glasses and my purse."),
    (SCAMMER, "No ma'am, do not put the phone down. Read me the card numbers "
              "and the security code on the back as soon as you have them."),
    (ETHEL, "Alright dear, give me just a minute."),
]

GAP_S = 0.45


def main():
    OUT.parent.mkdir(exist_ok=True)
    rate = 22050
    parts = []
    with tempfile.TemporaryDirectory() as td:
        for i, (voice, line) in enumerate(SCRIPT):
            aiff = Path(td) / f"{i}.aiff"
            subprocess.run(["say", "-v", voice, "-o", str(aiff), line],
                           check=True)
            data, r = sf.read(aiff, dtype="float32")
            parts.append(data)
            parts.append(np.zeros(int(GAP_S * rate), dtype=np.float32))
    audio = np.concatenate(parts)
    sf.write(OUT, audio, rate, subtype="PCM_16")
    print(f"wrote {OUT} ({len(audio)/rate:.0f}s)")


if __name__ == "__main__":
    if sys.platform != "darwin":
        sys.exit("requires macOS `say`")
    main()
