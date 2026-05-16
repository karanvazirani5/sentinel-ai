"""Single LLM helper. OpenAI-compatible, so it works with OpenAI, TokenRouter,
Qwen Cloud, Z.ai, and any sponsor offering an OpenAI-style endpoint.

DEMO_MODE: when true, any failure (missing key, network error, rate limit)
falls back to a plausible canned response instead of raising. This is the
fail-safe that keeps the stage demo working when external APIs flake."""

import json
import os
import time
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}

_FALLBACK_DRAFT = (
    "Hi {contact_name},\n\n"
    "I've been looking at {company} and how teams in your space stay on top of "
    "manual outreach work. From the outside it looks like there may be real "
    "leverage in automating the repetitive parts of your sales follow-up.\n\n"
    "I'm working on Sentinel, a lightweight agent system that takes over the "
    "research and drafting work, so your team can stay focused on the "
    "conversations that actually close. Happy to share a couple of tailored "
    "ideas if it's useful.\n\n"
    "Best,\nKaran"
)


def _build_client() -> Optional["OpenAI"]:
    if OpenAI is None:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL") or None
    return OpenAI(api_key=api_key, base_url=base_url)


def call_llm(
    messages: list[dict],
    *,
    max_tokens: int = 600,
    response_format: Optional[dict] = None,
) -> dict:
    """Call the configured LLM and return a normalized result.

    Returns: {
        "text": str,
        "tokens_in": int,
        "tokens_out": int,
        "latency_ms": int,
        "fallback": bool,   # true when DEMO_MODE rescued a failure
        "error": str | None,
    }
    """
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    started = time.time()
    client = _build_client()

    if client is None:
        return _demo_fallback(messages, started, error="no_client")

    try:
        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        resp = client.chat.completions.create(**kwargs)
        text = (resp.choices[0].message.content or "").strip()
        usage = getattr(resp, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", 0) if usage else 0
        tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0
        return {
            "text": text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": int((time.time() - started) * 1000),
            "fallback": False,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 — last-resort safety net for live demo
        return _demo_fallback(messages, started, error=str(exc))


def _demo_fallback(messages: list[dict], started: float, *, error: str) -> dict:
    """Always return a usable string. We never let the demo crash."""
    if not DEMO_MODE:
        # Still don't crash — but signal that no real call happened. Caller
        # decides whether to surface the error.
        pass
    user_text = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")
    text = _heuristic_text(user_text)
    return {
        "text": text,
        "tokens_in": 0,
        "tokens_out": 0,
        "latency_ms": int((time.time() - started) * 1000),
        "fallback": True,
        "error": error,
    }


def _heuristic_text(user_text: str) -> str:
    """Cheap canned output that at least mentions the company/contact if present."""
    lower = user_text.lower()
    if "json" in lower or "{" in user_text:
        return json.dumps(
            {
                "company_summary": (
                    "Small business operating in their local market, likely "
                    "leaning on a small team to keep operations moving."
                ),
                "pain_points": (
                    "manual outreach and follow-up; limited team capacity; "
                    "scattered customer communications"
                ),
                "personalization_note": (
                    "Reference the team's small size and the volume of repetitive "
                    "manual work they likely handle every week."
                ),
                "cited_fact": None,
            }
        )
    company = _extract_field(user_text, "Company:")
    contact = _extract_field(user_text, "Contact:") or "there"
    return _FALLBACK_DRAFT.format(company=company or "your team", contact_name=contact)


def _extract_field(user_text: str, label: str) -> Optional[str]:
    idx = user_text.find(label)
    if idx < 0:
        return None
    after = user_text[idx + len(label):]
    # Take until newline
    line_end = after.find("\n")
    value = (after[:line_end] if line_end != -1 else after).strip()
    return value or None
