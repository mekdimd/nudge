from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .models import Control

MODEL = "gemini-3.5-flash-lite"
RACE_MODELS = ("gemini-3.5-flash",)  # asked in parallel; the first good answer wins
FALLBACK_MODEL = "gemini-3.8-flash"
OVERLOADED = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "timed out", "Timeout")
TIMEOUT_MS = 10_000  # the API rejects deadlines under 10 s
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

FILL_SYSTEM = """You write short text that a person would type into a desktop app form.
The person finds precise mouse and keyboard work tiring, so they describe their goal and you draft the text.
Rules:
- Fill only the fields you are given, keyed by their id.
- Write in the person's own voice: plain, polite, brief. No placeholders like [Name].
- Never invent email addresses, phone numbers, or people's names that do not appear in the goal.
  If a field needs one and the goal does not contain it, return an empty string for that field.
- A recipient field ("To", "Cc", "Recipients") gets only the address from the goal.
- If a field is unrelated to the goal, return an empty string.
- A search box gets a short query (just what to find, e.g. "how to change a tire") only when the goal is to
  find, watch, play, or look something up. Otherwise leave it empty.
- AI-assistant prompt boxes ("Ask ...", "Describe your message", "Help me write") are never filled.
- If the goal names a particular site or app (YouTube, Spotify, Gmail, ...) and the page is not it,
  leave every field empty: the person has to go there first."""

URL_SYSTEM = """Return the single web address that best matches what the person wants to open.
If they want to find, watch, or listen to something, return that site's search results page with the query,
for example https://www.youtube.com/results?search_query=how+to+change+a+tire or
https://www.google.com/search?q=..., https://www.google.com/maps/search/..., https://open.spotify.com/search/...
Only return a URL you are confident exists. If you are not confident, set confident to false and url to an empty string."""


class WriterError(RuntimeError):
    pass


@dataclass
class FillDraft:
    values: dict[str, str]
    milliseconds: int
    rejected: dict[str, str] = field(default_factory=dict)


def addresses_not_in_goal(text: str, goal: str) -> list[str]:
    allowed = {a.lower() for a in EMAIL.findall(goal)}
    return [a for a in EMAIL.findall(text) if a.lower() not in allowed]


def validate_fill(goal: str, fields: list[Control], raw: dict) -> tuple[dict[str, str], dict[str, str]]:
    """Keep only known field ids with string values; blank any field containing an invented address."""
    known = {f.id for f in fields}
    values: dict[str, str] = {}
    rejected: dict[str, str] = {}
    for field_id in known:
        text = raw.get(field_id, "")
        text = text.strip() if isinstance(text, str) else ""
        invented = addresses_not_in_goal(text, goal)
        if invented:
            rejected[field_id] = f"made-up address {', '.join(invented)}"
            text = ""
        values[field_id] = text
    return values, rejected


def validate_url(raw: dict) -> str | None:
    url = (raw.get("url") or "").strip()
    if not raw.get("confident") or not url:
        return None
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or "." not in parsed.netloc or " " in url:
        return None
    return url


class Writer:
    def __init__(self, api_key: str, model: str = MODEL):
        if not api_key:
            raise WriterError("No GEMINI_API_KEY set. Add it to .env.")
        from google import genai
        from google.genai import types

        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1)),
        )
        self.model = model

    def _generate(self, system: str, prompt: str, schema: dict) -> tuple[dict, int]:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        )
        call = lambda model: self._client.models.generate_content(model=model, contents=prompt, config=config)
        started = time.perf_counter()
        response, error = None, None
        racers = [self.model] + [m for m in RACE_MODELS if m != self.model]
        pool = ThreadPoolExecutor(len(racers))
        futures = [pool.submit(call, m) for m in racers]
        for future in as_completed(futures):
            try:
                response = future.result()
                break
            except Exception as exc:
                error = exc
        pool.shutdown(wait=False, cancel_futures=True)  # don't wait for the slower model
        if response is None:
            if error is not None and not any(s in str(error) for s in OVERLOADED):
                raise WriterError(f"Gemini request failed: {error}") from error
            try:
                response = call(FALLBACK_MODEL)
            except Exception as exc:
                raise WriterError(f"Gemini request failed: {exc}") from exc
        elapsed = int((time.perf_counter() - started) * 1000)
        try:
            return json.loads(response.text or "{}"), elapsed
        except json.JSONDecodeError as exc:
            raise WriterError(f"Gemini returned unreadable JSON: {exc}") from exc

    def fill(self, goal: str, fields: list[Control], page: str = "") -> FillDraft:
        schema = {
            "type": "object",
            "properties": {f.id: {"type": "string", "description": f.label or "text field"} for f in fields},
            "required": [f.id for f in fields],
        }
        prompt = json.dumps(
            {
                "goal": goal,
                "page": page,
                "fields": [{"id": f.id, "label": f.label or "unlabeled", "kind": f.role} for f in fields],
            },
            ensure_ascii=False,
        )
        raw, elapsed = self._generate(FILL_SYSTEM, prompt, schema)
        values, rejected = validate_fill(goal, fields, raw)
        return FillDraft(values=values, milliseconds=elapsed, rejected=rejected)

    def url(self, goal: str) -> tuple[str | None, int]:
        schema = {
            "type": "object",
            "properties": {"url": {"type": "string"}, "confident": {"type": "boolean"}},
            "required": ["url", "confident"],
        }
        raw, elapsed = self._generate(URL_SYSTEM, json.dumps({"goal": goal}), schema)
        return validate_url(raw), elapsed
