"""Per-call event store: JSONL append + in-memory transcript accumulation.

Every call gets a call_id; all transcript/marker/tool events are persisted to
reports/{call_id}.jsonl and the plain transcript is kept for the post-call
threat report.
"""

import json
import time
import uuid
from pathlib import Path

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


class CallLog:
    def __init__(self, mode: str):
        self.call_id = uuid.uuid4().hex[:10]
        self.mode = mode
        self.started_at = time.time()
        self.transcript: list[dict] = []   # {speaker, text, ts}
        REPORTS_DIR.mkdir(exist_ok=True)
        self.path = REPORTS_DIR / f"{self.call_id}.jsonl"
        self._write({"type": "call_started", "mode": mode, "ts": self.started_at})

    def _write(self, event: dict):
        with open(self.path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def log(self, event_type: str, **fields):
        self._write({"type": event_type, "ts": time.time(), **fields})

    def add_transcript(self, speaker: str, text: str, final: bool = True):
        if not text.strip():
            return
        entry = {"speaker": speaker, "text": text.strip(), "ts": time.time()}
        if final:
            self.transcript.append(entry)
        self.log("transcript", **entry, final=final)

    def transcript_text(self) -> str:
        return "\n".join(f"{t['speaker'].upper()}: {t['text']}" for t in self.transcript)

    def end(self):
        self.log("call_ended", duration_s=round(time.time() - self.started_at, 1))
