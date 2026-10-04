from __future__ import annotations

import re

from .jev import JevDecision

DONE_THRESHOLD = 0.70
MIN_TOP_PROBABILITY = 0.40
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
    # Compare on the same scale as the bar (whole-percent). Raw floats like 0.49 - 0.34
    # are often 0.14999… and would spuriously fail a 15% margin gate.
    top = round(decision.top_probability, 3)
    margin = round(decision.margin, 3)
    return top < MIN_TOP_PROBABILITY or margin < MIN_MARGIN


def is_done(decision: JevDecision) -> bool:
    return decision.done >= DONE_THRESHOLD
