from __future__ import annotations

from dataclasses import dataclass, field

from nudge.core.actions import NONE_KEY, OptionSet, option_label
from nudge.core.jev import JevDecision
from nudge.core.models import Snapshot
from nudge.core.writer import FillDraft


class ScriptedJev:
    """Stands in for Jev: follows a list of option labels (or option keys), one per step.

    A step can be ("label", probability) to control confidence. When the script is
    exhausted it reports the task done.
    """

    def __init__(self, script: list, done_after: bool = True):
        self.script = list(script)
        self.calls = 0
        self.done_after = done_after
        self.seen_history: list[list[str]] = []

    def decide(self, task: str, snapshot: Snapshot, history: list[str], options: OptionSet) -> JevDecision:
        self.calls += 1
        self.seen_history.append(list(history))
        if not self.script:
            return JevDecision(choice=NONE_KEY, ranked=[(NONE_KEY, 1.0)], done=0.95 if self.done_after else 0.0, absent=0.0, milliseconds=90)
        step = self.script.pop(0)
        target, p = step if isinstance(step, tuple) else (step, 0.9)
        key = target if target in options.criteria else None
        if key is None:
            for k in options.keys:
                if option_label(k, snapshot).lower() == str(target).lower():
                    key = k
                    break
        if key is None:
            raise AssertionError(f"scripted target {target!r} not among options {options.keys}")
        others = [k for k in options.keys if k != key]
        rest = (1.0 - p) / max(len(others), 1)
        runner_up = others[0] if others else None
        ranked = [(key, p)]
        if runner_up:
            ranked.append((runner_up, rest if p >= 0.5 else min(p - 0.05, 1 - p)))
        ranked += [(k, 0.0) for k in others[1:]]
        return JevDecision(choice=key, ranked=ranked, done=0.05, absent=0.05, milliseconds=90)


class FakeWriter:
    def __init__(self, values_by_label: dict[str, str], url: str | None = None):
        self.values_by_label = values_by_label
        self._url = url
        self.fill_calls = 0

    def fill(self, goal, fields, page="") -> FillDraft:
        self.fill_calls += 1
        return FillDraft(values={f.id: self.values_by_label.get(f.label, "") for f in fields}, milliseconds=800)

    def url(self, goal):
        return self._url, 500


@dataclass
class RecordingEvents:
    confirm_answer: bool = True
    choose_answer: str | None = "first"
    approve_edits: dict[str, str] | None = None
    approve_answer: bool = True
    url_answer: str | None = "keep"
    recover_answers: list = field(default_factory=lambda: ["stop"])
    ask_answers: list = field(default_factory=lambda: [None])
    cancel_after_proposals: int | None = None
    log: list[str] = field(default_factory=list)
    snapshots: list = field(default_factory=list)
    proposals: int = 0
    result: tuple[bool, str] | None = None

    def cancelled(self) -> bool:
        return self.cancel_after_proposals is not None and self.proposals >= self.cancel_after_proposals

    def status(self, text):
        pass

    def decided(self, step, decision, labels):
        self.log.append(f"decided {decision.choice}")

    def writer_started(self):
        pass

    def writer_used(self, ms):
        self.log.append("writer")

    def observed(self, snapshot):
        self.snapshots.append(snapshot)

    def vision_used(self, ms, found):
        self.log.append(f"vision {found}")

    def propose(self, action, target):
        self.proposals += 1
        self.log.append(f"propose {action.describe()}")

    def hold(self, seconds):
        return not self.cancelled()

    def choose(self, reason, options):
        self.log.append(f"choose {[o[1] for o in options]}")
        if self.choose_answer == "first":
            return options[0][0]
        return self.choose_answer

    def approve_draft(self, note, fields):
        self.log.append(f"draft {[(label, text) for _, label, text in fields]}")
        if not self.approve_answer:
            return None
        values = {fid: text for fid, _, text in fields}
        for fid, label, _ in fields:
            if self.approve_edits and label in self.approve_edits:
                values[fid] = self.approve_edits[label]
        return values

    def approve_url(self, url, fallback):
        self.log.append(f"url {url}")
        if self.url_answer == "keep":
            return url or fallback
        return self.url_answer

    def confirm(self, message):
        self.log.append(f"confirm {message}")
        return self.confirm_answer

    def recover(self, message):
        self.log.append(f"recover {message}")
        return self.recover_answers.pop(0) if self.recover_answers else "stop"

    def ask(self, message):
        self.log.append(f"ask {message}")
        return self.ask_answers.pop(0) if self.ask_answers else None

    def finished(self, ok, message):
        self.result = (ok, message)
