from __future__ import annotations

import time
from contextlib import nullcontext
from typing import Any, Literal

import ApplicationServices as AS
import Quartz
from AppKit import NSPasteboard, NSPasteboardTypeString, NSRunningApplication, NSWorkspace
from CoreFoundation import CFEqual, CFGetTypeID

from ..core.actions import is_browser
from ..core.models import AppRef, Control, Rect, Snapshot
from .base import AdapterError, clean_text

ATTRS = [
    "AXRole",
    "AXSubrole",
    "AXTitle",
    "AXDescription",
    "AXValue",
    "AXEnabled",
    "AXPosition",
    "AXSize",
    "AXChildren",
    "AXPlaceholderValue",
    "AXHelp",
]

PRESSABLE = {
    "AXButton": "button",
    "AXMenuItem": "menu item",
    "AXCheckBox": "checkbox",
    "AXRadioButton": "radio button",
    "AXLink": "link",
    "AXPopUpButton": "pop-up button",
    "AXMenuButton": "menu button",
    "AXDisclosureTriangle": "disclosure triangle",
    "AXTab": "tab",
}
TEXT_ROLES = {"AXTextField": "text field", "AXTextArea": "text area", "AXComboBox": "combo box"}
CONTEXT_ROLES = {"AXMenu", "AXToolbar", "AXWebArea", "AXSheet", "AXGroup", "AXList", "AXTabGroup", "AXDialog"}
MENU_OPENERS = {"AXMenuButton", "AXPopUpButton"}
SKIPPED_SUBROLES = {
    "AXSecureTextField",
    "AXCloseButton",
    "AXMinimizeButton",
    "AXZoomButton",
    "AXFullScreenButton",
}

OPEN_MENU = "open menu"
MAX_NODES = 6000
TIME_BUDGET = 2.5
AX_ERROR_CANNOT_COMPLETE = -25204

KEYCODES = {"enter": 36, "escape": 53, "tab": 48, "v": 9, "l": 37, "f": 3, "[": 33}
KEY_COMBOS: dict[str, tuple[int, int]] = {
    "enter": (KEYCODES["enter"], 0),
    "escape": (KEYCODES["escape"], 0),
    "tab": (KEYCODES["tab"], 0),
    "back": (KEYCODES["["], Quartz.kCGEventFlagMaskCommand),
    "address_bar": (KEYCODES["l"], Quartz.kCGEventFlagMaskCommand),
    "find": (KEYCODES["f"], Quartz.kCGEventFlagMaskCommand),
    "paste": (KEYCODES["v"], Quartz.kCGEventFlagMaskCommand),
}

_ELEMENT_TYPE = AS.AXUIElementGetTypeID()
_VALUE_TYPE = AS.AXValueGetTypeID()
_POINT = getattr(AS, "kAXValueCGPointType", getattr(AS, "kAXValueTypeCGPoint", 1))
_SIZE = getattr(AS, "kAXValueCGSizeType", getattr(AS, "kAXValueTypeCGSize", 2))
_ERROR = getattr(AS, "kAXValueAXErrorType", getattr(AS, "kAXValueTypeAXError", 5))


def _is_element(obj: Any) -> bool:
    return obj is not None and CFGetTypeID(obj) == _ELEMENT_TYPE


def _clean(value: Any) -> Any:
    """Turn AX error placeholders into None."""
    if value is None:
        return None
    try:
        if CFGetTypeID(value) == _VALUE_TYPE and AS.AXValueGetType(value) == _ERROR:
            return None
    except Exception:
        pass
    return value


def _attr(element, name: str) -> Any:
    err, value = AS.AXUIElementCopyAttributeValue(element, name, None)
    return _clean(value) if err == 0 else None


def _attrs(element) -> dict[str, Any]:
    err, values = AS.AXUIElementCopyMultipleAttributeValues(element, ATTRS, 0, None)
    if err != 0 or values is None:
        return {}
    return {name: _clean(v) for name, v in zip(ATTRS, values)}


def _point(value) -> tuple[float, float] | None:
    if value is None:
        return None
    ok, point = AS.AXValueGetValue(value, _POINT, None)
    return (point.x, point.y) if ok else None


def _size(value) -> tuple[float, float] | None:
    if value is None:
        return None
    ok, size = AS.AXValueGetValue(value, _SIZE, None)
    return (size.width, size.height) if ok else None


def _rect(info: dict) -> Rect | None:
    p, s = _point(info.get("AXPosition")), _size(info.get("AXSize"))
    if p is None or s is None:
        return None
    return Rect(p[0], p[1], s[0], s[1])


def _text(value: Any) -> str:
    if value is None or _is_element(value):
        return ""
    if isinstance(value, str):
        return clean_text(value)
    return ""


def _short(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


class MacAdapter:
    name = "macOS Accessibility"

    def __init__(self):
        self._enabled_pids: set[int] = set()

    def thread_context(self):
        return nullcontext()

    def permission_problem(self) -> str | None:
        if AS.AXIsProcessTrusted():
            return None
        AS.AXIsProcessTrustedWithOptions({AS.kAXTrustedCheckOptionPrompt: True})
        return (
            "Nudge needs Accessibility permission. Open System Settings > Privacy & Security > "
            "Accessibility, turn on the app running Nudge (Terminal, Cursor, or Python), then restart Nudge."
        )

    def frontmost_app(self) -> AppRef | None:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return None
        return AppRef(name=str(app.localizedName() or ""), pid=int(app.processIdentifier()))

    def activate_app(self, app: AppRef) -> None:
        front = self.frontmost_app()
        if front and front.pid == app.pid:
            return
        running = NSRunningApplication.runningApplicationWithProcessIdentifier_(app.pid)
        if running is not None:
            running.activateWithOptions_(1 << 1)
        AS.AXUIElementSetAttributeValue(AS.AXUIElementCreateApplication(app.pid), "AXFrontmost", True)
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            front = self.frontmost_app()
            if front and front.pid == app.pid:
                return
            time.sleep(0.05)

    def _enable_web_accessibility(self, app_el, app: AppRef) -> None:
        if app.pid in self._enabled_pids:
            return
        AS.AXUIElementSetAttributeValue(app_el, "AXManualAccessibility", True)
        if is_browser(app.name):
            AS.AXUIElementSetAttributeValue(app_el, "AXEnhancedUserInterface", True)
            time.sleep(0.4)
        self._enabled_pids.add(app.pid)

    def snapshot(self, app: AppRef) -> Snapshot:
        started = time.perf_counter()
        app_el = AS.AXUIElementCreateApplication(app.pid)
        AS.AXUIElementSetMessagingTimeout(app_el, 1.0)
        self._enable_web_accessibility(app_el, app)

        window = None
        for _ in range(4):
            window = _attr(app_el, "AXFocusedWindow") or _attr(app_el, "AXMainWindow")
            if window is not None:
                break
            time.sleep(0.25)
        focused = _attr(app_el, "AXFocusedUIElement")
        window_title = _text(_attr(window, "AXTitle")) if window is not None else ""
        window_rect = _rect(_attrs(window)) if window is not None else None

        roots: list[tuple[Any, str]] = []
        for child in _attr(app_el, "AXChildren") or []:
            if _text(_attr(child, "AXRole")) == "AXMenu":
                roots.append((child, OPEN_MENU))
        if window is not None:
            roots.append((window, ""))

        walker = _Walker(window_rect, focused, started)
        for root, context in roots:
            walker.walk(root, context)

        controls = walker.controls
        menu = [c for c in controls if c.context == OPEN_MENU]
        if menu:
            controls = menu

        return Snapshot(
            app=app,
            window_title=window_title,
            controls=controls,
            focused_id=walker.focused_id,
            window_bounds=window_rect,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    def press(self, control: Control) -> None:
        element = control.ref
        if element is None:
            raise AdapterError("control has no accessibility element")
        role = control.ref_role if hasattr(control, "ref_role") else ""
        AS.AXUIElementSetMessagingTimeout(element, 0.5 if role in MENU_OPENERS else 1.5)
        names = _action_names(element)
        for action in ("AXPress", "AXShowMenu", "AXConfirm", "AXPick"):
            if names and action not in names:
                continue
            err = AS.AXUIElementPerformAction(element, action)
            if err in (0, AX_ERROR_CANNOT_COMPLETE):
                return
        raise AdapterError(f"could not press {control.label!r}")

    def click(self, control: Control) -> None:
        if control.bounds is None:
            raise AdapterError(f"{control.label!r} has no position to click")
        x, y = control.bounds.center
        for kind in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp):
            event = Quartz.CGEventCreateMouseEvent(None, kind, (x, y), Quartz.kCGMouseButtonLeft)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
            time.sleep(0.03)

    def set_text(self, control: Control, text: str) -> None:
        element = control.ref
        AS.AXUIElementSetAttributeValue(element, "AXFocused", True)
        time.sleep(0.1)
        if not control.ref_is_web:
            if AS.AXUIElementSetAttributeValue(element, "AXValue", text) == 0 and _text(_attr(element, "AXValue")) == " ".join(text.split()):
                return
        if not _attr(element, "AXFocused"):
            self.click(control)
            time.sleep(0.15)
        self.type_text(text)

    def type_text(self, text: str) -> None:
        board = NSPasteboard.generalPasteboard()
        previous = board.stringForType_(NSPasteboardTypeString)
        board.clearContents()
        board.setString_forType_(text, NSPasteboardTypeString)
        self.key("paste")
        time.sleep(0.25)
        if previous is not None:
            board.clearContents()
            board.setString_forType_(previous, NSPasteboardTypeString)

    def scroll(self, direction: Literal["up", "down"], near: Control | None, window: Snapshot) -> None:
        area = near.bounds if near and near.bounds else window.window_bounds
        if area is None:
            raise AdapterError("no window to scroll")
        original = Quartz.CGEventGetLocation(Quartz.CGEventCreate(None))
        Quartz.CGWarpMouseCursorPosition(area.center)
        time.sleep(0.03)
        amount = -10 if direction == "down" else 10
        event = Quartz.CGEventCreateScrollWheelEvent(None, Quartz.kCGScrollEventUnitLine, 1, amount)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
        time.sleep(0.05)
        Quartz.CGWarpMouseCursorPosition(original)

    def key(self, name: str) -> None:
        if name not in KEY_COMBOS:
            raise AdapterError(f"unknown key {name}")
        code, flags = KEY_COMBOS[name]
        for down in (True, False):
            event = Quartz.CGEventCreateKeyboardEvent(None, code, down)
            Quartz.CGEventSetFlags(event, flags)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
            time.sleep(0.02)


def _action_names(element) -> list[str]:
    err, names = AS.AXUIElementCopyActionNames(element, None)
    return list(names) if err == 0 and names else []


class MacControl(Control):
    ref_role: str = ""
    ref_is_web: bool = False


class _Walker:
    def __init__(self, window_rect: Rect | None, focused, started: float):
        self.window_rect = window_rect
        self.focused = focused
        self.started = started
        self.nodes = 0
        self.controls: list[Control] = []
        self.focused_id: str | None = None

    def _out_of_view(self, rect: Rect | None) -> bool:
        if rect is None or rect.is_empty or self.window_rect is None:
            return False
        return not rect.intersects(self.window_rect)

    def walk(self, root, context: str) -> None:
        stack: list[tuple[Any, str, bool]] = [(root, context, False)]
        while stack:
            if self.nodes >= MAX_NODES or time.perf_counter() - self.started > TIME_BUDGET:
                return
            element, ctx, in_web = stack.pop()
            self.nodes += 1
            info = _attrs(element)
            if not info:
                continue
            role = _text(info.get("AXRole"))
            rect = _rect(info)
            if self._out_of_view(rect) and role not in ("AXMenu",):
                continue
            in_web = in_web or role == "AXWebArea"
            label = (
                _text(info.get("AXTitle"))
                or _text(info.get("AXDescription"))
                or _text(info.get("AXPlaceholderValue"))
                or _text(info.get("AXHelp"))
            )
            self._maybe_add(element, info, role, label, rect, ctx, in_web)

            child_ctx = ctx
            if role == "AXMenu" and not in_web:
                child_ctx = OPEN_MENU
            elif role == "AXToolbar":
                child_ctx = label or "toolbar"
            elif ctx != OPEN_MENU and role in CONTEXT_ROLES and label and len(label) < 60:
                child_ctx = _short(label, 40)
            children = info.get("AXChildren") or []
            for child in reversed(list(children)):
                if _is_element(child):
                    stack.append((child, child_ctx, in_web))

    def _maybe_add(self, element, info, role, label, rect, ctx, in_web) -> None:
        subrole = _text(info.get("AXSubrole"))
        if subrole in SKIPPED_SUBROLES:
            return
        if role in TEXT_ROLES:
            kind = "search field" if subrole == "AXSearchField" else TEXT_ROLES[role]
            value = _text(info.get("AXValue"))
            self._add(element, label, kind, info, rect, ctx, value, True, role, in_web)
        elif role in PRESSABLE:
            if not label:
                label = _child_text(element)
            if not label and role not in ("AXCheckBox", "AXMenuButton"):
                return
            kind = "switch" if subrole == "AXSwitch" else PRESSABLE[role]
            if role == "AXRadioButton" and subrole == "AXTabButton":
                kind = "tab"
            raw = info.get("AXValue")
            value = None
            if role in ("AXCheckBox", "AXRadioButton") and isinstance(raw, (int, bool)):
                value = "on" if raw else "off"
            elif role == "AXPopUpButton":
                value = _text(raw) or None
            self._add(element, label, kind, info, rect, ctx, value, False, role, in_web)

    def _add(self, element, label, kind, info, rect, ctx, value, is_text, role, in_web) -> None:
        if rect is None or rect.is_empty:
            return
        enabled = info.get("AXEnabled")
        control = MacControl(
            id=f"e{len(self.controls) + 1}",
            label=_short(label),
            role=kind,
            enabled=bool(enabled) if enabled is not None else True,
            bounds=rect,
            context=ctx,
            value=value,
            is_text_field=is_text,
            ref=element,
        )
        control.ref_role = role
        control.ref_is_web = in_web
        if self.focused is not None and self.focused_id is None:
            try:
                if CFEqual(self.focused, element):
                    self.focused_id = control.id
            except Exception:
                pass
        self.controls.append(control)


def _child_text(element, depth: int = 2) -> str:
    texts: list[str] = []
    frontier = [element]
    for _ in range(depth):
        next_frontier = []
        for node in frontier:
            for child in (_attr(node, "AXChildren") or [])[:6]:
                if not _is_element(child):
                    continue
                text = _text(_attr(child, "AXValue")) or _text(_attr(child, "AXTitle")) or _text(_attr(child, "AXDescription"))
                if text:
                    texts.append(text)
                next_frontier.append(child)
        if texts:
            break
        frontier = next_frontier
    return " ".join(texts[:3])
