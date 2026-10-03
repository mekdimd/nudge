"""Check that the Jev and Gemini keys in .env work. Run: uv run python scripts/smoke.py"""

from __future__ import annotations

import sys

from nudge.config import load_config
from nudge.core.actions import build_options
from nudge.core.jev import JevClient, JevError
from nudge.core.writer import Writer, WriterError
from nudge.platform.fake import FakeAdapter


def check_jev(key: str) -> bool:
    adapter = FakeAdapter.from_fixture("live_caption")
    adapter.screen = "menu"
    snapshot = adapter.snapshot(adapter.app)
    options = build_options(snapshot)
    try:
        client = JevClient(key)
        for attempt in (1, 2):
            decision = client.decide("turn on Live Caption", snapshot, ["Press “Chrome”: worked"], options)
            print(f"Jev call {attempt}: picked {decision.choice} p={decision.top_probability:.2f} "
                  f"done={decision.done:.2f} in {decision.milliseconds} ms")
    except JevError as exc:
        print(f"Jev FAILED: {exc}")
        return False
    return True


def check_gemini(key: str) -> bool:
    adapter = FakeAdapter.from_fixture("gmail")
    adapter.screen = "compose"
    fields = adapter.snapshot(adapter.app).empty_fields
    try:
        writer = Writer(key)
        draft = writer.fill("email prof.lee@sfu.ca that I'm sick and will miss lecture", fields)
        print(f"Gemini fill in {draft.milliseconds} ms:")
        for field in fields:
            print(f"  {field.label}: {draft.values.get(field.id, '')!r}")
        url, ms = writer.url("open the SFU course registration page")
        print(f"Gemini url in {ms} ms: {url}")
    except WriterError as exc:
        print(f"Gemini FAILED: {exc}")
        return False
    return True


def main() -> int:
    config = load_config()
    ok = check_jev(config.typesafe_api_key)
    ok = check_gemini(config.gemini_api_key) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
