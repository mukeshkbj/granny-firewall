"""Bake the replay demo into frontend/public/demo_script.json.

Runs the REAL Detector over the sample's caller lines so the static build
replays byte-identical marker/risk events - the browser driver is just a
timer, no detector port needed. Report comes from the captured rp2 run.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from detector import Detector  # noqa: E402

lines = json.loads((ROOT / "samples/irs_scam_call.lines.json").read_text())
report = json.loads(
    (ROOT / "reports/2560c4dc74.report.json").read_text())

det = Detector()
per_line = {}
for i, line in enumerate(lines):
    if line["speaker"] != "caller":
        continue
    evs = [m.to_dict() for m in det.feed(line["text"], speaker="caller")]
    if evs:
        per_line[i] = [{"type": "marker", **e} for e in evs]
        per_line[i].append({"type": "risk", **det.snapshot()})

out = {
    "wav": "irs_scam_call.wav",
    "lines": lines,
    "per_line": per_line,
    "report": report,
    "total_s": max(l["end_s"] for l in lines) + 1.5,
}
dst = ROOT / "frontend/public/demo_script.json"
dst.write_text(json.dumps(out))
print(f"{dst}  {len(lines)} lines, "
      f"{sum(len(v) for v in per_line.values())} events, "
      f"report={report['verdict']['scam_type']} risk={report['verdict']['risk_score']}")
