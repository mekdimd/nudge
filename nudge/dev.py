"""Offline stand-ins so the UI can be rehearsed without API keys: `uv run nudge --offline gmail`."""

from __future__ import annotations

import time

from .core.actions import NONE_KEY, OptionSet, option_label
from .core.jev import JevDecision
from .core.models import Snapshot
from .core.writer import EMAIL, FillDraft

PATHS = {
    "live_caption": ["Chrome", "Settings", "Accessibility", "Live Caption"],
    "gmail": ["Compose", "Type into the empty fields", "Send"],
}

GOALS = {
    "live_caption": "turn on Live Caption",
    "gmail": "email prof.lee@sfu.ca that I'm sick and will miss lecture",
}


class OfflineJev:
    """Walks a fixed path of option labels. Not a planner; only for rehearsing the UI on a fixture."""

    def __init__(self, path: list[str]):
        self.path = list(path)

    def decide(self, task: str, snapshot: Snapshot, history: list[str], options: OptionSet) -> JevDecision:
        time.sleep(0.09)
        if len(history) >= len(self.path):
            return JevDecision(NONE_KEY, [(NONE_KEY, 1.0)], 0.96, 0.0, 90)
        target = self.path[len(history)].lower()
        keys = [k for k in options.keys if k != NONE_KEY]
        chosen = next((k for k in keys if option_label(k, snapshot).lower() == target), NONE_KEY)
        others = [k for k in keys if k != chosen][:2]
        ranked = [(chosen, 0.86)] + list(zip(others, (0.09, 0.03)))
        return JevDecision(chosen, ranked, 0.04, 0.03, 90)


class OfflineWriter:
    def fill(self, goal, fields, filled=None) -> FillDraft:
        time.sleep(0.6)
        address = (EMAIL.findall(goal) or [""])[0]
        values = {}
        for f in fields:
            label = (f.label or "").lower()
            if "to" in label.split() or "recipient" in label:
                values[f.id] = address
            elif "subject" in label:
                values[f.id] = "Missing lecture today"
            elif "body" in label or "message" in label:
                values[f.id] = "Hi Professor Lee,\n\nI'm sick today and will miss lecture. Sorry for the short notice.\n\nThank you"
            else:
                values[f.id] = ""
        return FillDraft(values=values, milliseconds=600)

    def url(self, goal):
        return None, 0
