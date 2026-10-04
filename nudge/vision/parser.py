"""OmniParser-style screen parsing, used only when the accessibility tree isn't enough.

YOLO finds interactive regions, OCR reads text, and Florence names icons that have no text.
Everything runs locally; screenshots never leave the computer.
"""

from __future__ import annotations

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from ..core.models import Control, Rect, Snapshot
from .ocr import Box
from .screen import grab_window

ToPhysical = Callable[[float, float, float, float], tuple[float, float, float, float]]

BOX_THRESHOLD = 0.05
IOU_THRESHOLD = 0.1
MAX_CAPTIONS = 32
SEARCH_HINT = re.compile(r"\bsearch\b|what do you want|type here|^find\b", re.IGNORECASE)
WORDY = re.compile(r"[^\W\d_]")
FILLER = re.compile(r"\s+for (playing )?(a )?(video|audio|media)( or (video|audio))?\b", re.IGNORECASE)


def _iou(a: Box, b: Box) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _center_inside(inner: Box, outer: Box) -> bool:
    cx, cy = (inner[0] + inner[2]) / 2, (inner[1] + inner[3]) / 2
    return outer[0] <= cx <= outer[2] and outer[1] <= cy <= outer[3]


def merge(icons: list[Box], texts: list[tuple[str, Box]]) -> tuple[list[tuple[str, Box]], list[Box]]:
    """Pair detections with the text inside them. Returns (labelled boxes, boxes that still need a caption)."""
    labelled: list[tuple[str, Box]] = []
    unnamed: list[Box] = []
    used: set[int] = set()
    for icon in icons:
        inside = [i for i, (_, t) in enumerate(texts) if _center_inside(t, icon)]
        if inside:
            used.update(inside)
            ordered = sorted(inside, key=lambda i: (round(texts[i][1][1] / 8), texts[i][1][0]))
            labelled.append((" ".join(texts[i][0] for i in ordered), icon))
        else:
            unnamed.append(icon)
    labelled += [(text, box) for i, (text, box) in enumerate(texts) if i not in used]
    return labelled, unnamed


class ScreenParser:
    def __init__(self, to_physical: ToPhysical | None = None):
        self.to_physical = to_physical
        self.error: str | None = None
        self._ready = threading.Event()
        self._pool = ThreadPoolExecutor(1, thread_name_prefix="ocr")
        self._lock = threading.Lock()
        threading.Thread(target=self._load, name="vision-warmup", daemon=True).start()

    @property
    def ready(self) -> bool:
        return self._ready.is_set()

    def _load(self) -> None:
        try:
            from PIL import Image
            from ultralytics import YOLO

            from .caption import Captioner
            from .ocr import load_ocr
            from .weights import best_device, omniparser_file

            self.device = best_device()
            self.detector = YOLO(omniparser_file("icon_detect/model.pt"))
            self.ocr = load_ocr()
            self.captioner = Captioner(self.device)
            warm = Image.new("RGB", (640, 400), "white")
            self.detector.predict(warm, conf=BOX_THRESHOLD, imgsz=640, verbose=False, device=self.device)
            self.ocr.read(warm)
            self.captioner.caption([warm.crop((0, 0, 64, 64))])
        except Exception as exc:  # vision is optional; Nudge works without it
            self.error = f"{type(exc).__name__}: {exc}"
        finally:
            self._ready.set()

    def find(self, snapshot: Snapshot) -> tuple[list[Control], int]:
        """Controls visible in the window that the accessibility tree didn't report."""
        with self._lock:  # Peek and a run may both ask; the models aren't thread-safe
            return self._find(snapshot)

    def _find(self, snapshot: Snapshot) -> tuple[list[Control], int]:
        started = time.perf_counter()
        self._ready.wait(30)
        rect = snapshot.window_bounds
        if self.error or rect is None or rect.is_empty:
            return [], 0
        image, rect = grab_window(snapshot.app.pid, rect, self.to_physical)
        scale = image.size[0] / rect.w

        reading = self._pool.submit(self.ocr.read, image)  # OCR runs beside YOLO and captions
        result = self.detector.predict(image, conf=BOX_THRESHOLD, iou=IOU_THRESHOLD, imgsz=1280, verbose=False, device=self.device)[0]
        icons = [tuple(b) for b in result.boxes.xyxy.tolist()]
        small = sorted(icons, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))[:MAX_CAPTIONS]
        captioned = dict(zip(small, self.captioner.caption([image.crop(tuple(int(v) for v in b)) for b in small])))
        labelled, unnamed = merge(icons, reading.result())
        unnamed = [b for b in unnamed if b in captioned]
        captions = [captioned[b] for b in unnamed]

        tree = [c.bounds for c in snapshot.controls if c.bounds is not None]
        controls: list[Control] = []
        items = [(t, b, "text") for t, b in labelled] + [
            (f"{FILLER.sub('', c).rstrip('. ')} icon", b, "icon") for c, b in zip(captions, unnamed) if c
        ]
        for label, box, role in items:
            bounds = Rect(rect.x + box[0] / scale, rect.y + box[1] / scale, (box[2] - box[0]) / scale, (box[3] - box[1]) / scale)
            if bounds.w < 4 or bounds.h < 4:
                continue
            as_box = (bounds.x, bounds.y, bounds.x + bounds.w, bounds.y + bounds.h)
            if any(_iou(as_box, (t.x, t.y, t.x + t.w, t.y + t.h)) > 0.5 for t in tree):
                continue
            searchy = role == "text" and bool(SEARCH_HINT.search(label))
            controls.append(
                Control(
                    id=f"v{len(controls) + 1}",
                    label=label[:80],
                    role="search field" if searchy else ("button" if role == "icon" else "text"),
                    bounds=bounds,
                    is_text_field=searchy,
                    source="vision",
                    context=_where(box, image.size, labelled, scale) if role == "icon" else _region(box, image.size),
                )
            )
        return controls, int((time.perf_counter() - started) * 1000)


def _region(box, size) -> str:
    w, h = size
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    if cy < h * 0.1:
        return "the top bar"
    if cy > h * 0.88:
        return "the bottom bar"
    if cx < w * 0.22:
        return "the left sidebar"
    if cx > w * 0.78:
        return "the right panel"
    return "the main area"


def _where(box, size, texts, scale: float) -> str:
    """Where an icon sits and what text is beside it, since captions alone ("play button") repeat."""
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    parts = [_region(box, size)]
    if (box[2] - box[0]) / scale >= 48:
        parts.append("large")
    reach = max(box[2] - box[0], box[3] - box[1]) * 2.5
    near = [
        (abs((b[0] + b[2]) / 2 - cx) + abs((b[1] + b[3]) / 2 - cy), t)
        for t, b in texts
        if len(WORDY.findall(t)) >= 3 and b[0] - reach < cx < b[2] + reach and b[1] - reach < cy < b[3] + reach
    ]
    if near:
        parts.append(f"next to “{min(near)[1][:40]}”")
    return ", ".join(parts)
