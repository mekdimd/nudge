"""Screenshot of the target app's window only, never Nudge's own bar or overlay."""

from __future__ import annotations

import sys
from typing import Callable

from ..core.models import Rect

ToPhysical = Callable[[float, float, float, float], tuple[float, float, float, float]]


def _mac_window_id(pid: int, rect: Rect) -> int | None:
    import Quartz

    best, best_score = None, float("inf")
    for info in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID) or []:
        if info.get("kCGWindowOwnerPID") != pid or info.get("kCGWindowLayer") != 0:
            continue
        b = info["kCGWindowBounds"]
        score = abs(b["X"] - rect.x) + abs(b["Y"] - rect.y) + abs(b["Width"] - rect.w) + abs(b["Height"] - rect.h)
        if score < best_score:
            best, best_score = int(info["kCGWindowNumber"]), score
    return best


def _mac_grab(pid: int, rect: Rect):
    import Quartz
    from PIL import Image

    window_id = _mac_window_id(pid, rect)
    if window_id is None:
        return None, rect
    image = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,
        Quartz.kCGWindowListOptionIncludingWindow,
        window_id,
        Quartz.kCGWindowImageBoundsIgnoreFraming,
    )
    if image is None:
        return None, rect
    width, height = Quartz.CGImageGetWidth(image), Quartz.CGImageGetHeight(image)
    data = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(image))
    stride = Quartz.CGImageGetBytesPerRow(image)
    pil = Image.frombuffer("RGBA", (width, height), bytes(data), "raw", "BGRA", stride, 1).convert("RGB")
    for info in Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionIncludingWindow, window_id) or []:
        b = info["kCGWindowBounds"]
        rect = Rect(b["X"], b["Y"], b["Width"], b["Height"])
    return pil, rect


def _region_grab(rect: Rect, to_physical: ToPhysical | None):
    import mss
    from PIL import Image

    x, y, w, h = to_physical(rect.x, rect.y, rect.w, rect.h) if to_physical else (rect.x, rect.y, rect.w, rect.h)
    with mss.MSS() as screen:
        shot = screen.grab({"left": int(x), "top": int(y), "width": int(w), "height": int(h)})
    return Image.frombytes("RGB", shot.size, shot.rgb), rect


def grab_window(pid: int, rect: Rect, to_physical: ToPhysical | None = None):
    """Returns (image, the window's logical rect). Image pixels may be denser than logical pixels."""
    if sys.platform == "darwin":
        image, actual = _mac_grab(pid, rect)
        if image is not None:
            return image, actual
    return _region_grab(rect, to_physical)


def exclude_from_capture(widget) -> None:
    """Windows: keep Nudge's windows out of screenshots (macOS captures the target window directly)."""
    if sys.platform != "win32":
        return
    import ctypes

    WDA_EXCLUDEFROMCAPTURE = 0x11
    ctypes.windll.user32.SetWindowDisplayAffinity(int(widget.winId()), WDA_EXCLUDEFROMCAPTURE)
