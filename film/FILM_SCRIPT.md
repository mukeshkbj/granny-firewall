# FILM: Granny Firewall — hackathon demo

SURFACE: web app at localhost:8008 (the security-console dashboard)
PLACEMENT: lablab.ai submission page (embedded YouTube)
CANVAS: 2560x1440 landscape   TARGET LENGTH: ~80s
VIBE: tense watch-floor — a wiretap in a heist film; biggest moment: the dial
  pegging 100/CRITICAL as the stage pulses red; avoid: playful, chipper, corporate,
  slow ambient drift with no tension

OPENING CARD: "GRANNY//FIREWALL" — sub: "the bouncer at grandma's phone line"

SCENES:
1. The call — idea: an unknown caller hits the wire and gets screened live
   start: dashboard idle, replay mode selected
   interaction: press "Replay the scam call" — caller audio flows onto the wire
   payoff: transcript types out while markers land mid-sentence:
     IMPERSONATION +25, URGENCY +15, dial climbs through elevated
   data: bundled irs_scam_call.wav + lines.json (offline replay)
   ~28s (trimmed from the 66s take at the strong beats)

2. The escalation — idea: every scam tell stacks until the console goes to alert
   start: continuing the same call
   interaction: none — the scammer keeps talking; this scene is watch-and-build
   payoff: PAYMENT DEMANDED +35, ISOLATION +20, CREDENTIAL PHISHING +30 —
     dial hits 100/CRITICAL, status flips THREAT ACTIVE, stage border pulses red,
     "IRS IMPERSONATION" badge locks in under the dial
   ~14s

3. The verdict — idea: the family gets a case file, not a mystery call
   start: call ends
   interaction: report panel slides in
   payoff: scam type IRS IMPERSONATION · 100/100, claimed identity
     "Officer David Miller, IRS Tax Crime Unit", money "five hundred dollars",
     red flags with quotes, recommended actions, time held on the line
   ~10s

4. Proof of life — idea: it isn't canned — a scammer agent calls the firewall live
   start: botfight mode
   interaction: press "Start the duel"
   payoff: firewall greets, scammer runs its script, agent tool calls fire
     (flag_marker, set_persona), the firewall flips into the waster voice —
     "Oh dear, oh my…"
   ~20s

TITLE CARDS:
  before 1 "EVERY CALL HITS THE WIRE FIRST"
  before 4 "NOT A PLAYBACK — A SECOND AGENT"
END CARD: "GRANNY//FIREWALL" + "built on AssemblyAI" +
  "github.com/mukeshkbj/granny-firewall · +1 (331) 320-8381"

BRAND: Space Grotesk (display) + JetBrains Mono (data), dark console palette
  — bg #07090c, phosphor green #2ef2a0, signal red #ff5d5d, amber #ffb648
  full-bleed desktop path (FILL=1), synthetic arrow cursor + click rings
SOUND: synthesized score, cinematic-epic preset — sparse tension bed under
  dialogue, build into the 100/CRITICAL reveal, duck under title cards.
  The actual call audio stays ON TOP — the scammer's voice is the demo.
