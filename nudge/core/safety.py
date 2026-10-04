from __future__ import annotations

import re

from .jev import JevDecision

DONE_THRESHOLD = 0.70
MIN_TOP_PROBABILITY = 0.60
MIN_MARGIN = 0.15
MAX_STEPS = 12
HOLD_SECONDS = 0.5
ABSENT_THRESHOLD = 0.5
SPARSE_TREE = 8  # fewer pressable controls than this and the app probably draws its own UI

CONSEQUENTIAL_WORDS = (
    "send",
    "delete",
    "remove",
    "buy",
    "purchase",
    "pay",
    "submit",
    "clear",
    "erase",
    "reset",
    "sign out",
    "log out",
    "uninstall",
    "place order",
    "checkout",
    "discard",
)

_PATTERN = re.compile(r"\b(" + "|".join(re.escape(w) for w in CONSEQUENTIAL_WORDS) + r")\b", re.IGNORECASE)


def consequential_word(label: str) -> str | None:
    """The consequential word in a control label, if any. Jev cannot remove this requirement."""
    match = _PATTERN.search(label or "")
    return match.group(1).lower() if match else None


def is_unsure(decision: JevDecision) -> bool:
    return decision.top_probability < MIN_TOP_PROBABILITY or decision.margin < MIN_MARGIN


def is_done(decision: JevDecision) -> bool:
    return decision.done >= DONE_THRESHOLD
