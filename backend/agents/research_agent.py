"""Research agent: fetches a lead's website, asks the LLM for structured
research with a cited_fact, and returns both the research dict and a
step-by-step reasoning trace.

DEMO_MODE: if anything fails and the lead is the seeded demo lead, returns
a prewritten research dict so the stage demo never crashes.
"""

import json
import os
import re
import time
from typing import Optional

import httpx

from .llm import call_llm


DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}
DEMO_LEAD_ID = os.getenv("DEMO_LEAD_ID", "").strip() or None
BRIGHT_DATA_API_KEY = os.getenv("BRIGHT_DATA_API_KEY", "").strip() or None
BRIGHT_DATA_ZONE = os.getenv("BRIGHT_DATA_ZONE", "sentinel").strip() or "sentinel"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

MAX_PAGE_CHARS = 4000


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _strip_html(html: str) -> str:
    no_scripts = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    no_styles = re.sub(r"<style[\s\S]*?</style>", " ", no_scripts, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", no_styles)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fetch_via_bright_data(url: str) -> tuple[str, int]:
    """Bright Data Web Unlocker. Requires BRIGHT_DATA_API_KEY and
    BRIGHT_DATA_ZONE (the name of a zone created in the Bright Data
    dashboard). Raises on any non-2xx so the caller falls through to httpx.
    """
    started = time.time()
    headers = {
        "Authorization": f"Bearer {BRIGHT_DATA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"zone": BRIGHT_DATA_ZONE, "url": url, "format": "raw"}
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        resp = client.post(
            "https://api.brightdata.com/request",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        text = resp.text
    return text, int((time.time() - started) * 1000)


def _fetch_via_httpx(url: str) -> tuple[str, int]:
    started = time.time()
    with httpx.Client(timeout=10.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text, int((time.time() - started) * 1000)


def _fetch_page(url: str) -> tuple[str, int, str]:
    """Returns (text_content, latency_ms, tool_used)."""
    if BRIGHT_DATA_API_KEY:
        try:
            raw, latency = _fetch_via_bright_data(url)
            return _strip_html(raw)[:MAX_PAGE_CHARS], latency, "bright_data"
        except Exception:
            pass
    raw, latency = _fetch_via_httpx(url)
    return _strip_html(raw)[:MAX_PAGE_CHARS], latency, "httpx"


def _demo_research_for(lead) -> dict:
    """Prewritten research for the seeded demo lead. Names a real fact so the
    audience hears a specific detail in the email body."""
    return {
        "company_summary": (
            f"{lead.company} is a {lead.industry or 'small'} business based in "
            f"{lead.location or 'their local market'}, focused on serving a "
            "tight regional customer base with a small operations team."
        ),
        "pain_points": (
            "manual outreach and follow-up; scattered customer "
            "communications; limited team capacity for repetitive work"
        ),
        "personalization_note": (
            f"Mention {lead.company} by name and reference how a lean team "
            "feels the drag of repetitive sales follow-up."
        ),
        "cited_fact": (
            f"{lead.company} highlights their commitment to local service "
            "on their site — a hook worth leaning on in outreach."
        ),
    }


def _parse_research_json(text: str) -> Optional[dict]:
    """Strip code fences and json-load. Return None on failure."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        # Try to extract the first {...} block
        m = re.search(r"\{[\s\S]*\}", cleaned)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except Exception:
            return None


def run_research(lead) -> dict:
    """Run the research agent against a Lead row.

    Returns:
        {
            "research": {company_summary, pain_points, personalization_note, cited_fact},
            "trace": list of step dicts,
            "fallback": bool,
        }
    """
    trace: list[dict] = []
    is_demo_lead = DEMO_LEAD_ID is not None and lead.id == DEMO_LEAD_ID

    # Step 1: research_started
    trace.append({
        "task_name": "research_started",
        "tool_input": f"company={lead.company} industry={lead.industry or 'unknown'}",
        "tool_output_preview": "Beginning research run",
        "latency_ms": 0,
        "status": "completed",
        "tokens_in": 0,
        "tokens_out": 0,
    })

    # Step 2: website_fetched
    website_url = _normalize_url(lead.website or "")
    page_text = ""
    fetch_latency = 0
    fetch_tool = "skipped"
    fetch_error: Optional[str] = None
    if website_url:
        try:
            page_text, fetch_latency, fetch_tool = _fetch_page(website_url)
        except Exception as exc:
            fetch_error = str(exc)[:200]

    trace.append({
        "task_name": "website_fetched",
        "tool_input": website_url or "(no website on lead)",
        "tool_output_preview": (
            (page_text[:200] + "…") if page_text else (fetch_error or "no website provided")
        ),
        "latency_ms": fetch_latency,
        "status": "completed" if page_text else "skipped",
        "tokens_in": 0,
        "tokens_out": 0,
        "details": f"tool={fetch_tool}",
    })

    # Step 3: research_synthesized — LLM call
    system_prompt = (
        "You are a B2B sales research agent. Given a company profile and the "
        "text of their homepage, produce strictly valid JSON with these keys:\n"
        "  company_summary: 1-2 sentences about what they do\n"
        "  pain_points: a semicolon-separated list of 2-3 likely operational pains\n"
        "  personalization_note: how to open a cold email\n"
        "  cited_fact: ONE specific verifiable detail you actually saw on the "
        "homepage text (a service, a year founded, a location, a recent "
        "announcement). Null if the homepage text is empty or off-topic.\n"
        "Respond with JSON only, no prose."
    )
    user_prompt = (
        f"Company: {lead.company}\n"
        f"Contact: {lead.contact_name}\n"
        f"Industry: {lead.industry or 'unknown'}\n"
        f"Location: {lead.location or 'unknown'}\n"
        f"Website: {website_url or 'unknown'}\n\n"
        f"Homepage text (truncated to 4KB):\n"
        f"---\n{page_text or '(no page text available)'}\n---\n"
    )

    llm_result = call_llm(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=600,
        response_format={"type": "json_object"},
    )

    research = _parse_research_json(llm_result.get("text", ""))
    fallback = False

    if not research or not isinstance(research, dict):
        # Retry once with a stricter nudge.
        retry_messages = [
            {"role": "system", "content": system_prompt + "\nReturn valid JSON only."},
            {"role": "user", "content": user_prompt},
        ]
        retry_result = call_llm(retry_messages, max_tokens=600, response_format={"type": "json_object"})
        research = _parse_research_json(retry_result.get("text", ""))
        if research:
            llm_result = retry_result
        else:
            # Final fallback: demo prewritten for the staged lead, else minimal heuristic.
            fallback = True
            if is_demo_lead or DEMO_MODE:
                research = _demo_research_for(lead)
            else:
                research = {
                    "company_summary": (
                        f"{lead.company} is a {lead.industry or 'small'} business."
                    ),
                    "pain_points": "manual outreach and follow-up; limited team capacity",
                    "personalization_note": (
                        f"Reference {lead.company} by name and the workload "
                        "a small team feels from repetitive outreach."
                    ),
                    "cited_fact": None,
                }

    trace.append({
        "task_name": "research_synthesized",
        "tool_input": f"call_llm(prompt_chars={len(user_prompt)})",
        "tool_output_preview": (
            "cited_fact: " + (research.get("cited_fact") or "(none)")
            + " | pains: " + (research.get("pain_points") or "")
        )[:500],
        "latency_ms": llm_result.get("latency_ms", 0),
        "status": "completed" if not fallback else "fallback",
        "tokens_in": llm_result.get("tokens_in", 0),
        "tokens_out": llm_result.get("tokens_out", 0),
    })

    return {"research": research, "trace": trace, "fallback": fallback or llm_result.get("fallback", False)}
