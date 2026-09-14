# Granny Firewall — agent notes

Hackathon project: AI scam-call firewall on AssemblyAI. Python FastAPI backend,
React+Vite frontend.

## Commands

- Install: `uv venv .venv && uv pip install -r requirements.txt --python .venv/bin/python`
- Backend: `cd backend && ../.venv/bin/python -m uvicorn server:app --port 8008`
- Frontend dev: `cd frontend && npm run dev` (proxies `/api`,`/ws` → :8008)
- Prod: `cd frontend && npm run build` then serve via backend static mount
- Tests: `.venv/bin/python -m pytest tests/ -q` (detector tests need no API key)
- Lint: `.venv/bin/python -m ruff check backend/ tests/`
- Sample audio: `.venv/bin/python scripts/make_sample.py` (macOS `say` → wav)

## Key facts

- `ASSEMBLYAI_API_KEY` in `.env` (repo root). `FAMILY_CODEWORD` default `blueberry`.
- Voice Agent API: `wss://agents.assemblyai.com/v1/ws`, `Authorization: Bearer KEY`
  (Bearer prefix is required — other AAI endpoints take the raw key).
  Send `session.update` first; wait `session.ready`; audio = base64 PCM16 24kHz.
  Tool results go inside the `reply.done` handler, not at `tool.call` time.
- Universal-Streaming (analyze mode): SDK `assemblyai.streaming.v3`,
  pcm_s16le @16kHz, `llm_gateway` config = per-turn LLM classification
  (`{{turn}}` template), events: Begin/Turn/LLMGatewayResponse/Termination.
  Streaming is billed per open-session duration — always `disconnect(terminate=True)`.
- LLM Gateway REST: POST `https://llm-gateway.assemblyai.com/v1/chat/completions`,
  raw-key auth, `{model:"claude-sonnet-4-6", messages|prompt, max_tokens}`.
- Docs MCP for current API details: `https://assemblyai.com/docs/mcp`;
  integration prompt: `https://www.assemblyai.com/docs/agent-instructions.md`.
- Single active call at a time (`CallManager`) — deliberate hackathon scope.
- Only `speaker="caller"` text is fed to the detector; the agent's own words
  legitimately contain scam terms.
