"""Voice Agent API tool schemas + dispatch.

The agent calls these; dispatch_tool returns the string the agent hears back.
Side effects (dashboard events, detector flags, persona state) go through the
CallContext passed in.
"""


TOOLS = [
    {
        "type": "function",
        "name": "flag_marker",
        "description": "Flag a scam signal detected in what the caller just said.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "impersonation", "urgency_threat", "payment_vector",
                        "credential_phishing", "isolation",
                        "too_good_to_be_true", "grandparent_emergency",
                    ],
                },
                "quote": {"type": "string", "description": "What the caller said, verbatim."},
                "severity": {"type": "integer", "minimum": 1, "maximum": 3},
            },
            "required": ["category", "quote"],
        },
    },
    {
        "type": "function",
        "name": "verify_codeword",
        "description": "Verify the family codeword a caller gives when claiming to be family.",
        "parameters": {
            "type": "object",
            "properties": {"codeword": {"type": "string"}},
            "required": ["codeword"],
        },
    },
    {
        "type": "function",
        "name": "pass_to_family",
        "description": "Pass a verified legitimate caller through to Ethel.",
        "parameters": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
    {
        "type": "function",
        "name": "set_persona",
        "description": "Switch persona: 'screener' (default gatekeeper) or 'waster' (confused elder who stalls scammers).",
        "parameters": {
            "type": "object",
            "properties": {"persona": {"type": "string", "enum": ["screener", "waster"]}},
            "required": ["persona"],
        },
    },
    {
        "type": "function",
        "name": "whisper_alert",
        "description": "Silently alert the family dashboard about this call without the caller knowing.",
        "parameters": {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
            "required": ["summary"],
        },
    },
    {
        "type": "function",
        "name": "end_call",
        "description": "End the call immediately.",
        "parameters": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
    {
        "type": "function",
        "name": "get_risk_assessment",
        "description": "Get the current scam risk score and detected markers.",
        "parameters": {"type": "object", "properties": {}},
    },
]


def dispatch_tool(name: str, args: dict, ctx) -> str:
    """ctx: CallContext (detector, log, persona state, codeword, event hook)."""
    if name == "flag_marker":
        marker = ctx.detector.agent_flag(
            args.get("category", ""), args.get("quote", ""), int(args.get("severity", 1))
        )
        ctx.log.log("tool_flag_marker", **(marker.to_dict() if marker else args))
        return "Marker logged." if marker else "Category not recognized."

    if name == "verify_codeword":
        ok = ctx.detector.verify_codeword(
            args.get("codeword", ""), ctx.codeword
        )
        ctx.log.log("tool_verify_codeword", ok=ok)
        return (
            "Codeword verified. This caller is trusted — you may pass them to Ethel."
            if ok
            else "That is NOT the family codeword. Do not trust this caller."
        )

    if name == "pass_to_family":
        ctx.passed = True
        ctx.log.log("tool_pass_to_family", reason=args.get("reason", ""))
        if getattr(ctx, "bridge", None):   # Twilio mode: bridge to the real number
            import asyncio
            asyncio.get_event_loop().create_task(ctx.bridge())
        return "Passing the caller through to Ethel now. Say: 'Let me get her for you.'"

    if name == "set_persona":
        persona = args.get("persona", "screener")
        ctx.persona = persona
        ctx.log.log("tool_set_persona", persona=persona)
        if persona == "waster":
            from personas import WASTER_PROMPT_SUFFIX

            return "Persona switched. " + WASTER_PROMPT_SUFFIX
        return "Back to screener mode."

    if name == "whisper_alert":
        ctx.log.log("tool_whisper_alert", summary=args.get("summary", ""))
        return "Family dashboard alerted silently. Continue the conversation."

    if name == "end_call":
        ctx.should_end = True
        ctx.log.log("tool_end_call", reason=args.get("reason", ""))
        return "Call ending. Say a brief goodbye and stop talking."

    if name == "get_risk_assessment":
        snap = ctx.detector.snapshot()
        ctx.log.log("tool_get_risk", **snap)
        return (
            f"Risk score {snap['score']}/100 ({snap['level']}). "
            f"Categories hit: {', '.join(snap['categories_hit']) or 'none'}. "
            f"Recommended: {snap['action']}."
        )

    return f"Unknown tool: {name}"
