from __future__ import annotations

import sys

from PySide6.QtCore import QObject, Signal


class Hotkeys(QObject):
    """System-wide keys: summon the bar, and Esc to stop a run while another app has focus."""

    summon = Signal()
    escape = Signal()

    def __init__(self):
        super().__init__()
        self._handle = None
        if sys.platform == "darwin":
            self._start_mac()
        elif sys.platform == "win32":
            self._start_windows()

    def _start_mac(self) -> None:
        from AppKit import NSEvent, NSEventMaskKeyDown, NSEventModifierFlagCommand, NSEventModifierFlagShift

        def handler(event):
            code = event.keyCode()
            flags = event.modifierFlags()
            if code == 49 and flags & NSEventModifierFlagCommand and flags & NSEventModifierFlagShift:
                self.summon.emit()
            elif code == 53:
                self.escape.emit()

        self._handle = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSEventMaskKeyDown, handler)

    def _start_windows(self) -> None:
        from pynput import keyboard

        hotkeys = keyboard.GlobalHotKeys({"<ctrl>+<shift>+<space>": self.summon.emit})
        hotkeys.start()

        def on_press(key):
            if key == keyboard.Key.esc:
                self.escape.emit()

        listener = keyboard.Listener(on_press=on_press)
        listener.start()
        self._handle = (hotkeys, listener)
