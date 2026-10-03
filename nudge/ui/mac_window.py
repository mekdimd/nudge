from __future__ import annotations

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
)


def _ns_window(widget):
    view = objc.objc_object(c_void_p=int(widget.winId()))
    return view.window()


def float_over_everything(widget, level: int, ignore_mouse: bool = False) -> None:
    """Keep a Qt window visible across Spaces and above other apps, even when Nudge is not active."""
    window = _ns_window(widget)
    if window is None:
        return
    window.setLevel_(level)
    window.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorFullScreenAuxiliary
        | NSWindowCollectionBehaviorStationary
    )
    window.setHidesOnDeactivate_(False)
    if ignore_mouse:
        window.setIgnoresMouseEvents_(True)
        window.setHasShadow_(False)


def run_as_accessory() -> None:
    """No Dock icon; Nudge lives in its floating bar."""
    NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
