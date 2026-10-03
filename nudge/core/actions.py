from __future__ import annotations

from dataclasses import dataclass

from .models import Action, Control, Snapshot

NONE_KEY = "__none__"
FILL_KEY = "fill"
GO_TO_URL_KEY = "go_to_url"
MAX_CONTROLS = 200

KEYS: dict[str, tuple[str, str]] = {
    "enter": ("Enter", "Press Enter to confirm, submit, or open what is focused"),
    "escape": ("Escape", "Press Escape to close a menu, popup, or dialog"),
    "tab": ("Tab", "Press Tab to move focus to the next field"),
    "back": ("Back", "Go back to the previous page or screen"),
    "address_bar": ("the address bar shortcut", "Focus the browser address bar"),
    "find": ("Find", "Open find-in-page to search for text on screen"),
}

BROWSERS = ("chrome", "edge", "firefox", "safari", "brave", "arc")


def is_browser(app_name: str) -> bool:
    name = app_name.lower()
    return any(b in name for b in BROWSERS)


@dataclass
class OptionSet:
    criteria: dict[str, str]
    controls: list[Control]

    @property
    def keys(self) -> list[str]:
        return list(self.criteria)


def _reading_order(control: Control) -> tuple[float, float]:
    if control.bounds is None:
        return (float("inf"), float("inf"))
    return (round(control.bounds.y / 8), control.bounds.x)


def build_options(snapshot: Snapshot, excluded: set[str] | None = None) -> OptionSet:
    """Every choice Jev may make for this screen. Controls first in reading order, then verbs."""
    excluded = excluded or set()
    seen: set[str] = set()
    controls: list[Control] = []
    for control in sorted(snapshot.pressables, key=_reading_order):
        description = control.describe()
        if description in seen or description in excluded:
            continue
        seen.add(description)
        controls.append(control)
        if len(controls) >= MAX_CONTROLS:
            break

    criteria: dict[str, str] = {f"press:{c.id}": f"Press {c.describe()}" for c in controls}

    empty = snapshot.empty_fields
    if empty and FILL_KEY not in excluded:
        names = ", ".join(f.label or "unlabeled field" for f in empty[:8])
        criteria[FILL_KEY] = f"Type text into the empty text fields on screen: {names}"

    for direction in ("down", "up"):
        key = f"scroll:{direction}"
        if key not in excluded:
            criteria[key] = f"Scroll {direction} to reveal more of the window"

    for name, (_, meaning) in KEYS.items():
        if name == "address_bar" and not is_browser(snapshot.app.name):
            continue
        key = f"key:{name}"
        if key not in excluded:
            criteria[key] = meaning

    if is_browser(snapshot.app.name) and GO_TO_URL_KEY not in excluded:
        criteria[GO_TO_URL_KEY] = "Go to a different website or web page by typing its address"

    criteria[NONE_KEY] = "None of these would advance the task; the control needed is not on screen"
    return OptionSet(criteria=criteria, controls=controls)


def option_label(key: str, snapshot: Snapshot) -> str:
    """Short human label for an option, used in the picker and history."""
    if key.startswith("press:"):
        control = snapshot.by_id(key.split(":", 1)[1])
        return control.label or control.role if control else key
    if key == FILL_KEY:
        return "Type into the empty fields"
    if key.startswith("scroll:"):
        return f"Scroll {key.split(':', 1)[1]}"
    if key.startswith("key:"):
        return f"Press {KEYS[key.split(':', 1)[1]][0]}"
    if key == GO_TO_URL_KEY:
        return "Go to a website"
    return "None of these"


def to_action(key: str, snapshot: Snapshot) -> Action:
    if key.startswith("press:"):
        target_id = key.split(":", 1)[1]
        control = snapshot.by_id(target_id)
        if control is None:
            raise ValueError(f"unknown control {target_id}")
        return Action(kind="press", option_key=key, target_id=target_id, label=control.label or control.role)
    if key == FILL_KEY:
        names = ", ".join(f.label or "field" for f in snapshot.empty_fields)
        return Action(kind="fill", option_key=key, label=names)
    if key.startswith("scroll:"):
        direction = key.split(":", 1)[1]
        if direction not in ("up", "down"):
            raise ValueError(key)
        return Action(kind="scroll", option_key=key, direction=direction)  # type: ignore[arg-type]
    if key.startswith("key:"):
        name = key.split(":", 1)[1]
        if name not in KEYS:
            raise ValueError(key)
        return Action(kind="key", option_key=key, key=name, label=KEYS[name][0])
    if key == GO_TO_URL_KEY:
        return Action(kind="go_to_url", option_key=key)
    raise ValueError(f"not an action: {key}")
