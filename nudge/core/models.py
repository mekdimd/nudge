from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class Rect:
    """Global screen rectangle in Qt logical pixels, origin at the top-left of the primary screen."""

    x: float
    y: float
    w: float
    h: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h / 2)

    def intersects(self, other: Rect) -> bool:
        return not (
            self.x + self.w <= other.x
            or other.x + other.w <= self.x
            or self.y + self.h <= other.y
            or other.y + other.h <= self.y
        )

    @property
    def is_empty(self) -> bool:
        return self.w <= 0 or self.h <= 0


@dataclass(frozen=True)
class AppRef:
    name: str
    pid: int
    handle: int | None = None


@dataclass
class Control:
    id: str
    label: str
    role: str
    enabled: bool = True
    bounds: Rect | None = None
    actions: tuple[str, ...] = ()
    context: str = ""
    value: str | None = None
    is_text_field: bool = False
    ref: Any = field(default=None, compare=False, repr=False)
    source: Literal["tree", "vision"] = "tree"
    shell: bool = False  # belongs to the OS shell (taskbar, Dock), not the target app

    def describe(self) -> str:
        label = self.label or "unlabeled"
        text = f"{label} ({self.role})"
        if self.value and not self.is_text_field:
            text += f" currently {self.value}"
        if self.context:
            text += f" in {self.context}"
        if self.bounds is not None:
            cx, cy = self.bounds.center
            text += f" at ({int(cx)},{int(cy)})"
        return text


@dataclass
class Snapshot:
    app: AppRef
    window_title: str
    controls: list[Control]
    focused_id: str | None = None
    window_bounds: Rect | None = None
    loading: bool = False
    elapsed_ms: int = 0

    def by_id(self, control_id: str) -> Control | None:
        for control in self.controls:
            if control.id == control_id:
                return control
        return None

    @property
    def empty_fields(self) -> list[Control]:
        return [c for c in self.controls if c.is_text_field and c.enabled and not (c.value or "").strip()]

    @property
    def pressables(self) -> list[Control]:
        return [c for c in self.controls if not c.is_text_field and c.enabled]


ActionKind = Literal["press", "fill", "scroll", "key", "go_to_url"]


@dataclass
class Action:
    kind: ActionKind
    option_key: str
    target_id: str | None = None
    key: str | None = None
    direction: Literal["up", "down"] | None = None
    text_by_field: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    label: str = ""
    double: bool = False

    def describe(self) -> str:
        if self.kind == "press":
            return f"{'Double-click' if self.double else 'Press'} “{self.label}”"
        if self.kind == "fill":
            return "Type into " + (self.label or "the empty fields")
        if self.kind == "scroll":
            return f"Scroll {self.direction}"
        if self.kind == "key":
            return f"Press {self.label}"
        if self.kind == "go_to_url":
            return f"Go to {self.url}" if self.url else "Go to a website"
        return self.kind
