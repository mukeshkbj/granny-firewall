# Granny Firewall

**The bouncer at grandma's phone line.**

## lablab form fields (copy-paste)

- **Project name:** Granny Firewall
- **Tagline:** The bouncer at grandma's phone line. Every unknown caller gets screened, scam markers light up live, and scammers get their time wasted instead of hers.
- **GitHub repo:** https://github.com/mukeshkbj/granny-firewall
- **Live demo:** Call **+1 (331) 320-8381** — the firewall answers and screens you. (Runs while the demo tunnel is up; Replay mode in the repo works offline forever.)
- **Tech stack:** AssemblyAI Voice Agent API · AssemblyAI Universal-Streaming · AssemblyAI Speech Understanding · Python / FastAPI · React + Vite · Twilio Media Streams
- **Built with:** AssemblyAI (required sponsor tech — Voice Agent sessions, streaming STT, tool calling, post-call Speech Understanding)
- **Description:** paste everything below this line.

## The problem

Americans over 60 reported nearly $5 billion lost to fraud in 2024 (FBI IC3), and the phone is still the scammers' favorite door. The IRS call, the bail-money call, the "your grandson is in trouble" call — they all work the same way: authority, urgency, secrecy, then gift cards. By the time a family member hears about it, the money is gone.

The obvious fix — "just don't answer unknown numbers" — doesn't survive contact with real life. Pharmacies call. Doctors' offices call. The plumber calls from a cell phone. Someone has to pick up.

Granny Firewall picks up instead.

## What it does

Every call from an unknown number hits the firewall before it ever rings grandma's phone. The screener answers politely — "Hello, you've reached the Miller residence, who's calling?" — and starts listening.

As the caller talks, a detection engine scores the conversation in real time across seven scam categories: impersonation, urgency and threats, payment demands, credential phishing, isolation tactics, fake prizes, and family-emergency cons. Each hit lands on a live dashboard mid-sentence, with the exact words that tripped it. A risk dial climbs as the case builds.

Then the call forks three ways:

- **Legitimate caller.** A pharmacy reminder, a neighbor, a real friend — passed through. If someone claims to be family, they're asked for the family codeword.
- **Suspicious.** The screener keeps asking questions. The family gets a quiet alert.
- **Clearly a scam.** Here's the part people don't expect: instead of hanging up, the firewall switches into a sweet, slightly confused 78-year-old persona and lets the scammer explain themselves. Slowly. Every minute a scammer spends coaxing card numbers out of "Ethel" is a minute they're not calling an actual victim.

When it ends, the family gets a threat report: who the caller claimed to be, what they asked for, how much money they wanted, the red flags that fired, and what to do next.

## How it's built

The whole stack rides on AssemblyAI:

- **Voice Agent API** runs the live conversation — speech-to-text, reasoning, voice, turn-taking, and tool calls over a single WebSocket. The agent's tools are the product: `flag_marker`, `verify_codeword`, `pass_to_family`, `set_persona`, `whisper_alert`, `end_call`, `get_risk_assessment`.
- **Universal-Streaming** powers Analyze mode — feed any recorded call through the pipeline and watch markers land as the transcript streams.
- **LLM Gateway** runs per-turn classification on the stream and writes the structured verdict for the post-call report.
- **Speech Understanding** (async transcription with speaker labels, entities, sentiment, PII redaction) fills in the report with what was actually said and asked.

Detection runs on three layers at once — signature rules for speed, the agent's own tool calls for judgment, and the gateway pass for what the first two miss.

## Four ways to see it work

- **Replay** — a recorded IRS-impersonation call plays on the wire, start to verdict, with zero credentials. This is the mode to try first.
- **Analyze** — upload or pick any call recording and watch it screened live.
- **Live screen** — you play the caller through your browser mic. Run a scam, or say the codeword and watch the gates open.
- **Botfight** — a scripted scammer agent calls the firewall directly. Two voices, one wire, no humans required.

## What I'd take further

A real phone number (the Twilio bridge is written — μ-law audio end to end, no transcoding), an allowlist for known contacts, and a way for families to share scam fingerprints so one household's close call becomes everyone's shield.

---

## Demo video script (~2:30)

Target: judges should understand the product by second 10 and believe it by minute 1.

**0:00–0:15 — Cold open.**
Black screen, phone rings. On-screen text: "Every year, scammers take $5B from Americans over 60. This is one of their calls." Cut to the dashboard in Replay mode, line ringing.

**0:15–0:55 — The catch.**
Press "Replay the scam call." The scammer's voice plays ("This is Officer David Miller, IRS Tax Crime Unit…"). Keep the camera on the Threat Intel rail — markers land mid-sentence: IMPERSONATION +25, URGENCY +15. Risk dial climbs through HIGH, the stage border pulses red, status flips to THREAT ACTIVE. Grandma's voice answers from the lower channel.

**0:55–1:25 — The twist.**
Payment demand lands — PAYMENT DEMANDED +35, dial hits 75. Then ISOLATION +20 ("Do not tell your family"), CREDENTIAL PHISHING +30, dial pegs at 100, scam type badge reads IRS IMPERSONATION. Zoom on the marker quotes: "…We accept Apple gift cards…"

**1:25–1:55 — The report.**
Call ends, threat report slides in: claimed identity, "five hundred dollars" in the money column, red flags, recommended actions, call duration. Read the first recommended action aloud — it's the thesis of the product.

**1:55–2:20 — Prove it's live, not canned.**
If the API key is working, cut to Botfight ("now a scammer agent calls the firewall directly — watch two voices fight over the wire") or a short Live Screen clip where you ad-lib a scam through the mic. If the Twilio number is live: end on "call it yourself, the number's on the submission page."

**2:20–2:30 — Card.**
GRANNY//FIREWALL wordmark, the tagline, repo URL.

### Recording notes

- Capture at 1440×900 or 1920×1080 with the browser fullscreened — the dashboard is designed dark for video.
- Replay at 1× reads best on camera; use 2× only for a timelapse beat.
- The audio must be audible in the recording — the scammer's voice is what makes the markers feel earned. Screen-record with system audio on.
- If live modes flake on recording day, Replay alone still carries the entire three-act story.
