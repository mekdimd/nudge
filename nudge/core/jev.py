from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

import httpx

from .actions import NONE_KEY, OptionSet
from .models import Snapshot

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"
MAX_CHOICES = 255


class JevError(RuntimeError):
    pass


@dataclass
class JevDecision:
    choice: str
    ranked: list[tuple[str, float]]
    done: float
    absent: float
    milliseconds: int
    input_tokens: int = 0

    @property
    def chose_none(self) -> bool:
        return self.choice == NONE_KEY

    @property
    def top_probability(self) -> float:
        return self.ranked[0][1] if self.ranked else 0.0

    @property
    def margin(self) -> float:
        if len(self.ranked) < 2:
            return self.top_probability
        return self.ranked[0][1] - self.ranked[1][1]

    def top(self, n: int, include_none: bool = False) -> list[tuple[str, float]]:
        return [(k, p) for k, p in self.ranked if include_none or k != NONE_KEY][:n]


def build_request(task: str, snapshot: Snapshot, history: list[str], options: OptionSet) -> tuple[dict, dict]:
    """State and questions for one step. State and criteria describe the same world."""
    state: dict[str, Any] = {
        "task": task,
        "app": snapshot.app.name,
        "window": snapshot.window_title,
        "step": len(history) + 1,
        "already_done": history or ["nothing yet"],
        "screen_elements": [{"id": c.id, "describes": c.describe()} for c in options.controls],
        "empty_text_fields": [f.label or "unlabeled field" for f in options.fields],
    }
    questions: dict[str, Any] = {
        "done": {
            "type": "noul",
            "instructions": (
                f'Judging only by what is on screen now and the actions already taken, '
                f'has this task been completed: "{task}"? '
                "Music and video apps put the playing artist and title in the window title; "
                "if it shows only the app's name, nothing is playing yet."
            ),
        },
        "absent": {
            "type": "noul",
            "instructions": "Is the control needed to make the next bit of progress on the task missing from the screen?",
        },
        "pick": {
            "type": "choice",
            "instructions": (
                f'Which single action should be taken next to make progress on the task: "{task}"? '
                "Consider what has already been done; do not repeat a step that already succeeded. "
                "To write text into fields, choose the option to type into the empty text fields; "
                "do not press a field label or a button that opens a picker first. "
                "Play controls in a bottom bar only resume whatever is already loaded; to play a particular "
                "song or artist, double-click it in the results or press the large play button on its page."
            ),
            "criteria": options.criteria,
        },
    }
    return state, questions


def parse_decision(answers: dict[str, Any], options: OptionSet, milliseconds: int, input_tokens: int = 0) -> JevDecision:
    valid = set(options.keys)
    try:
        pick = answers["pick"]
        choice = pick["choice"]
        probabilities: dict[str, float] = pick["probabilities"]
        done = float(answers["done"]["noul"])
        absent = float(answers["absent"]["noul"])
    except (KeyError, TypeError, ValueError) as exc:
        raise JevError(f"incomplete decision: {exc}") from exc

    if choice not in valid:
        raise JevError(f"Jev chose an option that does not exist: {choice}")
    if not probabilities or not set(probabilities) <= valid:
        raise JevError("Jev returned probabilities for unknown options")
    if not all(isinstance(p, (int, float)) and math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values()):
        raise JevError("Jev returned invalid probabilities")
    if not (0 <= done <= 1 and 0 <= absent <= 1):
        raise JevError("Jev returned invalid noul values")
    if probabilities.get(choice) != max(probabilities.values()):
        raise JevError("Jev's choice is not its most likely option")

    ranked = sorted(
        probabilities.items(),
        key=lambda kv: (-kv[1], kv[0] != choice, kv[0]),
    )
    return JevDecision(
        choice=choice,
        ranked=[(k, float(p)) for k, p in ranked],
        done=done,
        absent=absent,
        milliseconds=milliseconds,
        input_tokens=input_tokens,
    )


class JevClient:
    def __init__(self, api_key: str, client: httpx.Client | None = None, model: str = MODEL):
        if not api_key:
            raise JevError("No TYPESAFE_API_KEY set. Add it to .env.")
        self.api_key = api_key
        self.model = model
        self.http = client or httpx.Client(timeout=httpx.Timeout(20.0, connect=10.0))

    def ask(self, state: dict, questions: dict) -> tuple[dict[str, Any], int, int]:
        for q in questions.values():
            if q.get("type") == "choice" and len(q["criteria"]) > MAX_CHOICES:
                raise JevError(f"Jev accepts at most {MAX_CHOICES} options; this call had {len(q['criteria'])}")
        started = time.perf_counter()
        try:
            response = self.http.post(
                ENDPOINT,
                headers={"authorization": f"Bearer {self.api_key}", "content-type": "application/json"},
                json={"state": state, "model": self.model, "questions": questions},
            )
        except httpx.HTTPError as exc:
            raise JevError(f"Could not reach Jev: {exc}") from exc
        elapsed = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 300:
            raise JevError(f"Jev returned {response.status_code}: {response.text[:300]}")
        try:
            body = response.json()
            answers = body["answers"]
        except (ValueError, KeyError) as exc:
            raise JevError(f"Jev sent something unreadable: {exc}") from exc
        tokens = int((body.get("usage") or {}).get("input_tokens") or 0)
        return answers, elapsed, tokens

    def decide(self, task: str, snapshot: Snapshot, history: list[str], options: OptionSet) -> JevDecision:
        state, questions = build_request(task, snapshot, history, options)
        answers, elapsed, tokens = self.ask(state, questions)
        return parse_decision(answers, options, elapsed, tokens)
