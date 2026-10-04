from __future__ import annotations

import base64
import json
import queue
import threading
from urllib.parse import urlencode

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtMultimedia import QAudioFormat, QAudioSource, QMediaDevices

from .levels import rms_level

URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?" + urlencode(
    {
        "model_id": "scribe_v2_realtime",
        "audio_format": "pcm_16000",
        "commit_strategy": "vad",
        "vad_silence_threshold_secs": "0.8",
        "language_code": "en",
    }
)
LISTEN_WINDOW_MS = 10000


class Voice(QObject):
    """One spoken request at a time with ElevenLabs realtime speech-to-text. The mic is only open while listening."""

    state = Signal(str)  # listening | idle | muted | no_mic | error: <detail>
    heard = Signal(str)  # live partial transcript
    request = Signal(str)  # the finished request
    level = Signal(float)  # mic loudness while listening, 0..1

    _transcript = Signal(str, bool)  # text, committed (crosses from the socket thread)
    _failed = Signal(str)

    def __init__(self, api_key: str, settings=None):
        super().__init__()
        self.api_key = api_key
        self.settings = settings
        self.active = False
        self._source: QAudioSource | None = None
        self._io = None
        self._audio: queue.Queue[bytes | None] = queue.Queue()
        self._done = threading.Event()
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(lambda: self.cancel(timed_out=True))
        self._transcript.connect(self._on_transcript)
        self._failed.connect(self._on_failed)

    def listen(self) -> None:
        if self.active:
            return
        if self.settings is not None and self.settings.mic_muted:
            self.state.emit("muted")
            return
        device = self.settings.input_device() if self.settings is not None else QMediaDevices.defaultAudioInput()
        if device.isNull():
            self.state.emit("no_mic")
            return
        fmt = QAudioFormat()
        fmt.setSampleRate(16000)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
        if not device.isFormatSupported(fmt):
            self.state.emit("error: microphone doesn't support 16 kHz mono audio")
            return
        self.active = True
        self._audio = queue.Queue()
        self._done = threading.Event()
        self._source = QAudioSource(device, fmt, self)
        self._io = self._source.start()
        self._io.readyRead.connect(self._read_mic)
        threading.Thread(target=self._session, args=(self._audio, self._done), name="scribe", daemon=True).start()
        self._timeout.start(LISTEN_WINDOW_MS)
        self.state.emit("listening")

    def cancel(self, timed_out: bool = False) -> None:
        if not self.active:
            return
        self._close()
        self.state.emit("timeout" if timed_out else "idle")

    def _close(self) -> None:
        self.active = False
        self._timeout.stop()
        if self._source is not None:
            self._source.stop()
            self._source = None
        self._done.set()
        self._audio.put(None)
        self.level.emit(0.0)

    # main thread

    def _read_mic(self) -> None:
        data = bytes(self._io.readAll())
        if data and self.active:
            self._audio.put(data)
            self.level.emit(rms_level(data))

    def _on_transcript(self, text: str, committed: bool) -> None:
        if not self.active:
            return
        if not committed:
            self.heard.emit(text)
        elif text.strip():
            self._close()
            self.state.emit("idle")
            self.request.emit(" ".join(text.split()))

    def _on_failed(self, detail: str) -> None:
        if self.active:
            self._close()
            self.state.emit(f"error: {detail}")

    # socket thread

    def _session(self, audio: queue.Queue, done: threading.Event) -> None:
        from websockets.exceptions import InvalidStatus, WebSocketException
        from websockets.sync.client import connect

        try:
            with connect(URL, additional_headers={"xi-api-key": self.api_key}, open_timeout=10) as ws:
                threading.Thread(target=self._send, args=(ws, audio), daemon=True).start()
                for raw in ws:
                    if done.is_set():
                        return
                    message = json.loads(raw)
                    kind = message.get("message_type", "")
                    if kind == "partial_transcript":
                        self._transcript.emit(message.get("text", ""), False)
                    elif kind in ("committed_transcript", "committed_transcript_with_timestamps"):
                        self._transcript.emit(message.get("text", ""), True)
                    elif kind.endswith("error") or kind.endswith("_exceeded") or kind == "unaccepted_terms":
                        self._failed.emit(message.get("error") or kind)
                        return
        except InvalidStatus as exc:
            if not done.is_set():
                rejected = exc.response.status_code in (401, 403)
                self._failed.emit("ElevenLabs rejected the API key" if rejected else f"ElevenLabs returned {exc.response.status_code}")
        except (OSError, WebSocketException) as exc:
            if not done.is_set():
                self._failed.emit(str(exc) or type(exc).__name__)

    @staticmethod
    def _send(ws, audio: queue.Queue) -> None:
        try:
            while (chunk := audio.get()) is not None:
                ws.send(json.dumps({"message_type": "input_audio_chunk", "audio_base_64": base64.b64encode(chunk).decode(), "sample_rate": 16000}))
        except Exception:
            pass  # the receive loop reports the closed socket
