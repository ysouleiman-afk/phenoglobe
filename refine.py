"""
Optional vision-LLM refiner: turns the coarse FairFace macro estimate into an
IllustrativeDNA-style population breakdown by actually looking at the face.

Providers (first configured one wins):
  ANTHROPIC_API_KEY  -> Claude (claude-opus-5) with structured JSON output
  GEMINI_API_KEY     -> Gemini (gemini-2.5-flash) via REST, JSON response

Returns {population_id: share} over ALL populations (sums to 1), or None when no
provider is configured or the call fails. The caller blends this with FairFace.
"""
import base64
import json
import os
import urllib.request

import populations as P

PROMPT = """You are the scoring engine inside a playful "phenotype globe" app. The user uploaded a photo of their
own face and consented to a fun, non-scientific estimate of which regional populations their facial features
most resemble, in the style of a consumer ancestry report. This is not identification: do not name or guess
who the person is, and do not mention celebrities.

An automated classifier (FairFace) already produced these coarse group probabilities:
{macro}

Look at the face and distribute 100 points across the populations below according to how strongly the visible
features resemble typical members of each population. Use the classifier as a prior but correct it when the image
clearly disagrees (e.g. it tends to file Mediterranean faces under Latin American). Put most of the points on a
few populations; give 0 to those that do not fit. Only the JSON matters.

Populations (id: name [group]):
{catalog}
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "points": {"type": "number"}},
                "required": ["id", "points"],
                "additionalProperties": False,
            },
        },
        "note": {"type": "string"},
    },
    "required": ["scores", "note"],
    "additionalProperties": False,
}


def provider() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return None


def _prompt(macro: dict[str, float]) -> str:
    catalog = "\n".join(f"- {c['id']}: {c['name']} [{c['group']}]" for c in P.refiner_catalog())
    macro_txt = ", ".join(f"{k}: {v * 100:.0f}%" for k, v in sorted(macro.items(), key=lambda kv: -kv[1]) if v >= 0.01)
    return PROMPT.format(macro=macro_txt, catalog=catalog)


def _to_shares(data: dict) -> dict[str, float] | None:
    scores = {s["id"]: max(0.0, float(s["points"])) for s in data.get("scores", []) if s.get("id") in P.POPULATIONS}
    total = sum(scores.values())
    if total <= 0:
        return None
    return {k: scores.get(k, 0.0) / total for k in P.POPULATIONS}


def refine_claude(jpeg: bytes, macro: dict[str, float]) -> dict[str, float] | None:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ.get("PHENO_CLAUDE_MODEL", "claude-opus-5"),
        max_tokens=2048,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.standard_b64encode(jpeg).decode()}},
                {"type": "text", "text": _prompt(macro)},
            ],
        }],
    )
    if response.stop_reason == "refusal":
        return None
    text = next((b.text for b in response.content if b.type == "text"), "")
    return _to_shares(json.loads(text))


def refine_gemini(jpeg: bytes, macro: dict[str, float]) -> dict[str, float] | None:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    model = os.environ.get("PHENO_GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.standard_b64encode(jpeg).decode()}},
            {"text": _prompt(macro)},
        ]}],
        "generationConfig": {"response_mime_type": "application/json", "response_schema": {
            "type": "OBJECT",
            "properties": {
                "scores": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                    "id": {"type": "STRING"}, "points": {"type": "NUMBER"}}, "required": ["id", "points"]}},
                "note": {"type": "STRING"},
            },
            "required": ["scores", "note"],
        }},
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        out = json.load(r)
    text = out["candidates"][0]["content"]["parts"][0]["text"]
    return _to_shares(json.loads(text))


def refine(jpeg: bytes, macro: dict[str, float]) -> tuple[str | None, dict[str, float] | None]:
    """(provider name, shares) - shares is None if unavailable/failed."""
    prov = provider()
    try:
        if prov == "claude":
            return prov, refine_claude(jpeg, macro)
        if prov == "gemini":
            return prov, refine_gemini(jpeg, macro)
    except Exception as exc:  # network / quota / refusal: fall back to heuristic silently but report it
        return f"{prov} (failed: {type(exc).__name__})", None
    return None, None
