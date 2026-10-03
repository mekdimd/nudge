from __future__ import annotations

import hashlib
import time
from typing import Callable

from .models import Snapshot

SETTLE_TIMEOUT = 1.5
POLL_INTERVAL = 0.15


def fingerprint(snapshot: Snapshot) -> str:
    focused = snapshot.by_id(snapshot.focused_id) if snapshot.focused_id else None
    parts = sorted(
        f"{c.role}|{c.label}|{c.value or ''}|{int(c.enabled)}" for c in snapshot.controls
    )
    focus_key = f"{focused.role}|{focused.label}" if focused else ""
    payload = "\n".join([snapshot.window_title, focus_key, *parts])
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def wait_for_change(
    read: Callable[[], Snapshot],
    before: str,
    timeout: float = SETTLE_TIMEOUT,
    interval: float = POLL_INTERVAL,
    cancelled: Callable[[], bool] = lambda: False,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[Snapshot, bool]:
    """Poll until the UI differs from `before` and holds still for one poll, or time runs out."""
    deadline = time.monotonic() + timeout
    latest = read()
    latest_fp = fingerprint(latest)
    changed = latest_fp != before
    while time.monotonic() < deadline and not cancelled():
        sleep(interval)
        current = read()
        current_fp = fingerprint(current)
        if changed and current_fp == latest_fp:
            return current, True
        changed = changed or current_fp != before
        latest, latest_fp = current, current_fp
    return latest, latest_fp != before
