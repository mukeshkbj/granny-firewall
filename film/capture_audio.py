"""Capture call_audio events from the dashboard WS — writes incrementally.

Usage: capture_audio.py <out_dir/prefix>
Writes <prefix>_<speaker>.raw (PCM16 24k mono) + <prefix>_events.log live.
"""
import asyncio, base64, json, sys, time

prefix = sys.argv[1]

async def main():
    import websockets
    t0 = None
    files, logf = {}, open(f"{prefix}_events.log", "w", buffering=1)
    try:
        async with websockets.connect("ws://localhost:8008/ws/dashboard") as ws:
            print("connected", flush=True)
            async for raw in ws:
                if t0 is None:
                    t0 = time.monotonic()
                t = time.monotonic() - t0
                if isinstance(raw, bytes):
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                et = msg.get("type")
                if et == "call_audio" and msg.get("audio"):
                    spk = msg.get("speaker", "other")
                    if spk not in files:
                        files[spk] = open(f"{prefix}_{spk}.raw", "wb")
                    files[spk].write(base64.b64decode(msg["audio"]))
                    files[spk].flush()
                elif et in ("call_started", "call_ended", "report",
                            "marker", "risk", "verdict", "persona", "tool"):
                    logf.write(f"{t:.3f}\t{et}\t{json.dumps(msg)[:200]}\n")
    finally:
        for f in files.values():
            f.close()
        logf.close()
        print("closed", flush=True)

asyncio.run(main())
