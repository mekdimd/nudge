"""Text on screen with pixel boxes: Apple Vision on macOS, RapidOCR on Windows."""

from __future__ import annotations

import sys

Box = tuple[float, float, float, float]  # x1, y1, x2, y2 in image pixels


class MacOCR:
    def __init__(self):
        import Vision

        self.Vision = Vision

    def read(self, image) -> list[tuple[str, Box]]:
        import io

        from Foundation import NSData

        Vision = self.Vision
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        data = NSData.dataWithBytes_length_(buffer.getvalue(), len(buffer.getvalue()))
        request = Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(False)
        handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, None)
        ok, _ = handler.performRequests_error_([request], None)
        if not ok:
            return []
        w, h = image.size
        found = []
        for observation in request.results() or []:
            text = str(observation.topCandidates_(1)[0].string()).strip()
            box = observation.boundingBox()  # normalized, origin bottom-left
            x1 = box.origin.x * w
            y2 = (1 - box.origin.y) * h
            found.append((text, (x1, y2 - box.size.height * h, x1 + box.size.width * w, y2)))
        return [f for f in found if f[0]]


class RapidOCR:
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR as Engine

        self.engine = Engine()

    def read(self, image) -> list[tuple[str, Box]]:
        import numpy as np

        result, _ = self.engine(np.asarray(image))
        found = []
        for points, text, _score in result or []:
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            found.append((text.strip(), (min(xs), min(ys), max(xs), max(ys))))
        return [f for f in found if f[0]]


def load_ocr():
    return MacOCR() if sys.platform == "darwin" else RapidOCR()
