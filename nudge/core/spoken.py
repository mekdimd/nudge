from __future__ import annotations

import re
from difflib import SequenceMatcher

STOP = {"stop", "cancel", "quit", "neither", "none", "nevermind", "abort"}
ORDINALS = {
    "1": 0, "one": 0, "first": 0,
    "2": 1, "two": 1, "second": 1,
    "3": 2, "three": 2, "third": 2,
    "4": 3, "four": 3, "fourth": 3,
    "5": 4, "five": 4, "fifth": 4,
}
# Speech-to-text writes these for "two" and "four"; only trust them in very short replies.
HOMOPHONES = {"to": 1, "too": 1, "for": 3}
FILLER = {"the", "a", "an", "option", "number", "choice", "pick", "choose", "select", "press", "click", "please", "one"}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower().replace("'", ""))


def match_choice(text: str, labels: list[str]) -> int | str | None:
    """Map a spoken reply to an option index, 'stop', or None when it can't be told."""
    tokens = _tokens(text)
    if not tokens:
        return None
    joined = " ".join(tokens)
    if STOP & set(tokens) or "never mind" in joined:
        return "stop"

    for token in tokens:
        index = ORDINALS.get(token)
        if index is not None and index < len(labels):
            return index
    if len(tokens) <= 2:
        for token in tokens:
            index = HOMOPHONES.get(token)
            if index is not None and index < len(labels):
                return index

    spoken = [t for t in tokens if t not in FILLER]
    scores = []
    for label in labels:
        words = [t for t in _tokens(label) if t not in FILLER]
        if not words or not spoken:
            scores.append(0.0)
            continue
        hits = sum(1 for w in words if any(SequenceMatcher(None, w, s).ratio() >= 0.8 for s in spoken))
        scores.append(hits / len(words))
    best = max(scores, default=0.0)
    if best < 0.5 or scores.count(best) > 1:
        return None
    return scores.index(best)


INTENTS = {
    "stop": ("stop", "cancel", "quit", "abort", "never mind", "nevermind"),
    "yes": ("yes", "yeah", "yep", "yup", "sure", "ok", "okay", "go", "go ahead", "do it", "confirm", "continue", "approve", "proceed", "looks good", "type it", "correct", "skip", "nothing"),
    "no": ("no", "nope", "nah", "dont", "do not"),
    "retry": ("retry", "try again", "again"),
    "click": ("click", "click it"),
    "other": ("other", "else", "something else", "pick something"),
}
MAX_INTENT_WORDS = 4  # longer replies are sentences, not commands


def _has_phrase(tokens: list[str], phrase: str) -> bool:
    words = phrase.split()
    return any(tokens[i : i + len(words)] == words for i in range(len(tokens) - len(words) + 1))


def match_intent(text: str, allowed: tuple[str, ...]) -> str | None:
    """The first allowed intent (in the order given) the reply expresses, or None."""
    tokens = _tokens(text)
    for intent in allowed:
        if intent != "stop" and len(tokens) > MAX_INTENT_WORDS:
            continue
        if any(_has_phrase(tokens, phrase) for phrase in INTENTS[intent]):
            return intent
    return None
