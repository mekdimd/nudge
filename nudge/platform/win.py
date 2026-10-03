from __future__ import annotations

import ctypes
import os
import time
from ctypes import wintypes
from typing import Any, Literal

import uiautomation as auto
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key
from pynput.mouse import Controller as MouseController

from ..core.actions import is_browser
from ..core.models import AppRef, Control, Rect, Snapshot
from .base import AdapterError, ToLogical

PRESSABLE = {
    "ButtonControl": "button",
    "MenuItemControl": "menu item",
    "CheckBoxControl": "checkbox",
    "RadioButtonControl": "radio button",
    "HyperlinkControl": "link",
    "TabItemControl": "tab",
    "ListItemControl": "list item",
    "SplitButtonControl": "split button",
    "TreeItemControl": "tree item",
    "ComboBoxControl": "combo box",
}
TEXT_ROLES = {"EditControl": "text field"}
CONTEXT_ROLES = {"MenuControl", "ToolBarControl", "GroupControl", "DocumentControl", "ListControl", "TabControl", "WindowControl"}

MAX_NODES = 4000
TIME_BUDGET = 2.5

PID = auto.PatternId
KEYS: dict[str, tuple[tuple, Any]] = {
    "enter": ((), Key.enter),
    "escape": ((), Key.esc),
    "tab": ((), Key.tab),
    "back": ((Key.alt,), Key.left),
    "address_bar": ((Key.ctrl,), "l"),
    "find": ((Key.ctrl,), "f"),
    "paste": ((Key.ctrl,), "v"),
}

FRIENDLY_NAMES = {"chrome": "Google Chrome", "msedge": "Microsoft Edge", "firefox": "Firefox"}


def _process_name(pid: int) -> str:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buffer = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            stem = os.path.splitext(os.path.basename(buffer.value))[0]
            return FRIENDLY_NAMES.get(stem.lower(), stem)
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _system_scale(x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
    try:
        scale = ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        scale = 1.0
    return (x / scale, y / scale, w / scale, h / scale)


def _short(text: str, limit: int = 80) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class WinControl(Control):
    raw_rect: tuple[int, int, int, int] = (0, 0, 0, 0)
    uia_role: str = ""
    is_web: bool = False


class WinAdapter:
    name = "Windows UI Automation"

    def __init__(self, to_logical: ToLogical | None = None):
        self.to_logical = to_logical or _system_scale
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        auto.SetGlobalSearchTimeout(1)

    def thread_context(self):
        return auto.UIAutomationInitializerInThread()

    def permission_problem(self) -> str | None:
        return None

    def frontmost_app(self) -> AppRef | None:
        handle = auto.GetForegroundWindow()
        if not handle:
            return None
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        return AppRef(name=_process_name(pid.value), pid=pid.value, handle=handle)

    def activate_app(self, app: AppRef) -> None:
        front = self.frontmost_app()
        if front and front.pid == app.pid:
            return
        if not app.handle:
            return
        if auto.IsIconic(app.handle):
            ctypes.windll.user32.ShowWindow(app.handle, 9)
        user32 = ctypes.windll.user32
        user32.keybd_event(0x12, 0, 0, 0)
        auto.SetForegroundWindow(app.handle)
        user32.keybd_event(0x12, 0, 2, 0)
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            front = self.frontmost_app()
            if front and front.pid == app.pid:
                return
            time.sleep(0.05)
        auto.SwitchToThisWindow(app.handle)

    def _rect(self, raw) -> tuple[Rect | None, tuple[int, int, int, int]]:
        r = (raw.left, raw.top, raw.right, raw.bottom)
        if raw.right <= raw.left or raw.bottom <= raw.top:
            return None, r
        x, y, w, h = self.to_logical(raw.left, raw.top, raw.right - raw.left, raw.bottom - raw.top)
        return Rect(x, y, w, h), r

    def snapshot(self, app: AppRef) -> Snapshot:
        started = time.perf_counter()
        window = auto.ControlFromHandle(app.handle) if app.handle else None
        if window is None:
            front = self.frontmost_app()
            if front and front.pid == app.pid:
                window = auto.ControlFromHandle(front.handle)
        if window is None:
            raise AdapterError(f"{app.name} has no window to read")

        window_rect, window_raw = self._rect(window.BoundingRectangle)
        focused = auto.GetFocusedControl()
        focus_key = None
        if focused is not None:
            try:
                fr = focused.BoundingRectangle
                focus_key = (focused.Name, focused.ControlTypeName, fr.left, fr.top)
            except Exception:
                focus_key = None

        walker = _Walker(self, window_raw, focus_key, started, is_browser(app.name))
        popups = self._popups(app, window)
        for popup in popups:
            walker.walk(popup, "open menu")
        if not any(c.role == "menu item" for c in walker.controls):
            walker.controls.clear()
            walker.walk(window, "")

        return Snapshot(
            app=app,
            window_title=_short(window.Name, 120),
            controls=walker.controls,
            focused_id=walker.focused_id,
            window_bounds=window_rect,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    def _popups(self, app: AppRef, window) -> list:
        popups = []
        for top in auto.GetRootControl().GetChildren():
            try:
                if top.ProcessId != app.pid or top.NativeWindowHandle == app.handle or top.IsOffscreen:
                    continue
                if top.ControlTypeName in ("MenuControl", "PaneControl", "WindowControl"):
                    rect = top.BoundingRectangle
                    if rect.right > rect.left and rect.bottom > rect.top:
                        popups.append(top)
            except Exception:
                continue
        return popups

    def press(self, control: Control) -> None:
        element = control.ref
        if element is None:
            raise AdapterError("control has no UI Automation element")
        order = [PID.InvokePattern, PID.TogglePattern, PID.SelectionItemPattern, PID.ExpandCollapsePattern]
        if control.role in ("checkbox", "switch"):
            order = [PID.TogglePattern, PID.InvokePattern, PID.SelectionItemPattern]
        for pattern_id in order:
            pattern = element.GetPattern(pattern_id)
            if pattern is None:
                continue
            try:
                if pattern_id == PID.InvokePattern:
                    pattern.Invoke(waitTime=0)
                elif pattern_id == PID.TogglePattern:
                    pattern.Toggle(waitTime=0)
                elif pattern_id == PID.SelectionItemPattern:
                    pattern.Select(waitTime=0)
                elif pattern_id == PID.ExpandCollapsePattern:
                    pattern.Expand(waitTime=0)
                return
            except Exception:
                continue
        legacy = element.GetPattern(PID.LegacyIAccessiblePattern)
        if legacy is not None:
            try:
                legacy.DoDefaultAction(waitTime=0)
                return
            except Exception:
                pass
        raise AdapterError(f"could not press {control.label!r}")

    def click(self, control: Control) -> None:
        left, top, right, bottom = getattr(control, "raw_rect", (0, 0, 0, 0))
        if right <= left or bottom <= top:
            raise AdapterError(f"{control.label!r} has no position to click")
        auto.Click((left + right) // 2, (top + bottom) // 2, waitTime=0)

    def set_text(self, control: Control, text: str) -> None:
        element = control.ref
        try:
            element.SetFocus()
        except Exception:
            pass
        time.sleep(0.1)
        if not getattr(control, "is_web", False):
            pattern = element.GetPattern(PID.ValuePattern)
            if pattern is not None:
                try:
                    pattern.SetValue(text, waitTime=0)
                    if " ".join((pattern.Value or "").split()) == " ".join(text.split()):
                        return
                except Exception:
                    pass
        if not element.HasKeyboardFocus:
            self.click(control)
            time.sleep(0.15)
        self.type_text(text)

    def type_text(self, text: str) -> None:
        try:
            previous = auto.GetClipboardText()
        except Exception:
            previous = None
        auto.SetClipboardText(text)
        self.key("paste")
        time.sleep(0.25)
        if previous:
            auto.SetClipboardText(previous)

    def scroll(self, direction: Literal["up", "down"], near: Control | None, window: Snapshot) -> None:
        target = near if near is not None and getattr(near, "raw_rect", None) else None
        if target is not None:
            left, top, right, bottom = target.raw_rect
        else:
            rect = auto.ControlFromHandle(window.app.handle).BoundingRectangle if window.app.handle else None
            if rect is None:
                raise AdapterError("no window to scroll")
            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        original = self.mouse.position
        self.mouse.position = ((left + right) // 2, (top + bottom) // 2)
        time.sleep(0.03)
        self.mouse.scroll(0, -5 if direction == "down" else 5)
        time.sleep(0.05)
        self.mouse.position = original

    def key(self, name: str) -> None:
        if name not in KEYS:
            raise AdapterError(f"unknown key {name}")
        modifiers, key = KEYS[name]
        for m in modifiers:
            self.keyboard.press(m)
        self.keyboard.press(key)
        self.keyboard.release(key)
        for m in reversed(modifiers):
            self.keyboard.release(m)


class _Walker:
    def __init__(self, adapter: WinAdapter, window_raw, focus_key, started: float, web: bool):
        self.adapter = adapter
        self.window_raw = window_raw
        self.focus_key = focus_key
        self.started = started
        self.web = web
        self.nodes = 0
        self.controls: list[Control] = []
        self.focused_id: str | None = None

    def _outside(self, raw) -> bool:
        left, top, right, bottom = self.window_raw
        return raw.right <= left or raw.left >= right or raw.bottom <= top or raw.top >= bottom

    def walk(self, root, context: str) -> None:
        stack: list[tuple[Any, str, bool]] = [(root, context, False)]
        while stack:
            if self.nodes >= MAX_NODES or time.perf_counter() - self.started > TIME_BUDGET:
                return
            element, ctx, in_web = stack.pop()
            self.nodes += 1
            try:
                role = element.ControlTypeName
                name = element.Name or ""
                raw = element.BoundingRectangle
                offscreen = element.IsOffscreen
            except Exception:
                continue
            has_area = raw.right > raw.left and raw.bottom > raw.top
            if offscreen and has_area and self._outside(raw) and context != "open menu":
                continue
            in_web = in_web or role == "DocumentControl"
            self._maybe_add(element, role, name, raw, ctx, in_web)

            child_ctx = ctx
            if role == "ToolBarControl":
                child_ctx = name or "toolbar"
            elif role in CONTEXT_ROLES and name and len(name) < 60 and element is not root:
                child_ctx = _short(name, 40)
            try:
                children = element.GetChildren()
            except Exception:
                children = []
            for child in reversed(children):
                stack.append((child, child_ctx, in_web))

    def _maybe_add(self, element, role, name, raw, ctx, in_web) -> None:
        if role in TEXT_ROLES or (role == "ComboBoxControl" and element.GetPattern(PID.ValuePattern) is not None and in_web):
            try:
                if element.IsPassword:
                    return
            except Exception:
                pass
            value = ""
            pattern = element.GetPattern(PID.ValuePattern)
            if pattern is not None:
                try:
                    value = pattern.Value or ""
                except Exception:
                    value = ""
            self._add(element, name, "text field" if role == "EditControl" else "combo box", raw, ctx, value, True, role, in_web)
            return
        if role not in PRESSABLE:
            return
        if not name and role not in ("CheckBoxControl",):
            return
        kind = PRESSABLE[role]
        value = None
        toggle = element.GetPattern(PID.TogglePattern) if role in ("ButtonControl", "CheckBoxControl") else None
        if toggle is not None:
            try:
                value = "on" if toggle.ToggleState == auto.ToggleState.On else "off"
                if role == "ButtonControl":
                    kind = "switch"
            except Exception:
                value = None
        self._add(element, name, kind, raw, ctx, value, False, role, in_web)

    def _add(self, element, name, kind, raw, ctx, value, is_text, role, in_web) -> None:
        rect, raw_tuple = self.adapter._rect(raw)
        if rect is None:
            return
        try:
            enabled = bool(element.IsEnabled)
        except Exception:
            enabled = True
        control = WinControl(
            id=f"e{len(self.controls) + 1}",
            label=_short(name),
            role=kind,
            enabled=enabled,
            bounds=rect,
            context=ctx,
            value=value,
            is_text_field=is_text,
            ref=element,
        )
        control.raw_rect = raw_tuple
        control.uia_role = role
        control.is_web = in_web and self.web
        if self.focus_key is not None and self.focused_id is None:
            if (name, role, raw.left, raw.top) == self.focus_key:
                self.focused_id = control.id
        self.controls.append(control)
