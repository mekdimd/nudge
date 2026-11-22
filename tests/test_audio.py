import numpy as np
import pytest
from PySide6.QtCore import QSettings


@pytest.fixture
def settings(qapp, tmp_path):
    from nudge.ui.audio_settings import AudioSettings

    return AudioSettings(QSettings(str(tmp_path / "nudge.ini"), QSettings.Format.IniFormat))


def tone(amplitude, samples=1600):
    return (np.sin(np.linspace(0, 40 * np.pi, samples)) * amplitude * 32767).astype("<i2").tobytes()


def test_rms_level_is_zero_for_silence_and_rises_with_volume():
    from nudge.ui.levels import rms_level

    assert rms_level(b"") == 0.0
    assert rms_level(tone(0.0)) == 0.0
    assert 0 < rms_level(tone(0.05)) < rms_level(tone(0.2)) <= 1.0


def sine(rate, freq=440.0, seconds=1.0):
    t = np.arange(int(rate * seconds)) / rate
    return np.sin(2 * np.pi * freq * t).astype(np.float32)


def peak_hz(pcm, rate=16000):
    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32)
    spec = np.abs(np.fft.rfft(samples * np.hanning(len(samples))))
    return spec.argmax() * rate / len(samples)


def test_native_rate_audio_stays_at_the_spoken_pitch():
    """48 kHz in must come out as 16 kHz at the same pitch, not sped up."""
    from nudge.ui.pcm import PcmStream

    raw = sine(48000).tobytes()
    whole = PcmStream(48000, 1, "float32").push(raw)
    streamed = b""
    stream = PcmStream(48000, 1, "float32")
    streamed += stream.push(raw[:2])  # a read that ends in the middle of a float sample
    for i in range(2, len(raw), 2048):
        streamed += stream.push(raw[i : i + 2048])
    assert streamed == whole
    assert abs(len(whole) // 2 - 16000) <= 2
    assert abs(peak_hz(whole) - 440) < 15


def test_odd_rate_and_stereo_keep_pitch():
    from nudge.ui.pcm import PcmStream

    mono = sine(44100, seconds=0.5)
    stereo = np.column_stack((mono, mono)).astype(np.float32).reshape(-1).tobytes()
    pcm = PcmStream(44100, 2, "float32").push(stereo)
    assert abs(len(pcm) // 2 - 8000) < 20
    assert abs(peak_hz(pcm) - 440) < 20


@pytest.mark.parametrize("rate", [44100, 48000])
def test_conversion_does_not_depend_on_read_boundaries(rate):
    from nudge.ui.pcm import PcmStream

    raw = sine(rate, freq=3000).tobytes()
    whole = PcmStream(rate, 1, "float32").push(raw)
    stream = PcmStream(rate, 1, "float32")
    pieces = [stream.push(raw[:1])]
    pieces.extend(stream.push(raw[i:i + 4096]) for i in range(1, len(raw), 4096))
    assert b"".join(pieces) == whole
    assert abs(len(whole) // 2 - 16000) <= 2


@pytest.mark.parametrize("rate", [44100, 48000])
def test_downsampling_removes_sound_above_the_speech_sample_band(rate):
    from nudge.ui.pcm import PcmStream

    speech = PcmStream(rate, 1, "float32").push(sine(rate, freq=3000).tobytes())
    high = PcmStream(rate, 1, "float32").push(sine(rate, freq=10000).tobytes())
    speech_samples = np.frombuffer(speech, dtype="<i2")[1600:].astype(np.float64)
    high_samples = np.frombuffer(high, dtype="<i2")[1600:].astype(np.float64)
    assert np.sqrt(np.mean(speech_samples ** 2)) > 20000
    assert np.sqrt(np.mean(high_samples ** 2)) < 200


def test_sixteen_khz_int16_passes_through():
    from nudge.ui.pcm import PcmStream

    raw = (sine(16000, seconds=0.1) * 16000).astype("<i2").tobytes()
    assert PcmStream(16000, 1, "int16").push(raw) == raw
    assert PcmStream(16000, 1, "int16").push(b"") == b""
    split = PcmStream(16000, 1, "int16")
    assert split.push(raw[:1]) + split.push(raw[1:]) == raw


@pytest.mark.parametrize("platform,expected_rate,expected_kind", [
    ("darwin", 48000, "Float"),
    ("win32", 16000, "Int16"),
])
def test_capture_preserves_windows_format_and_uses_native_rate_on_mac(monkeypatch, platform, expected_rate, expected_kind):
    import sys
    from types import SimpleNamespace

    from PySide6.QtMultimedia import QAudioFormat

    from nudge.ui import pcm

    preferred = QAudioFormat()
    preferred.setSampleRate(48000)
    preferred.setChannelCount(1)
    preferred.setSampleFormat(QAudioFormat.SampleFormat.Float)
    device = SimpleNamespace(isNull=lambda: False, preferredFormat=lambda: preferred, isFormatSupported=lambda fmt: True)
    class Source:
        def __init__(self, device, fmt, parent):
            self.fmt = fmt
            self.buffers = []

        def setBufferSize(self, size):
            self.buffers.append(size)

        def start(self):
            return object()

        def error(self):
            return SimpleNamespace(name="NoError")

    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(pcm, "QAudioSource", Source)
    source, io, converter = pcm.open_mic(device, None)
    assert source.fmt.sampleRate() == expected_rate
    assert source.fmt.sampleFormat().name == expected_kind
    assert source.fmt.channelCount() == 1
    if platform == "win32":
        assert source.buffers == []
        raw = tone(0.2)
        assert converter.push(raw) == raw


def test_envelope_has_one_value_per_window():
    from nudge.ui.levels import envelope

    pcm = tone(0.2, samples=24000)  # one second at 24 kHz
    assert len(envelope(pcm, 24000, 30)) == 34


def test_settings_round_trip(settings, tmp_path):
    from nudge.ui.audio_settings import AudioSettings

    changes = []
    settings.changed.connect(lambda: changes.append(True))
    settings.set_mic_muted(True)
    settings.set_voice_muted(True)
    settings.set_sounds_muted(True)
    again = AudioSettings(QSettings(str(tmp_path / "nudge.ini"), QSettings.Format.IniFormat))
    assert again.mic_muted and again.voice_muted and again.sounds_muted
    assert len(changes) == 3


def test_setting_the_same_value_twice_emits_once(settings):
    changes = []
    settings.changed.connect(lambda: changes.append(True))
    settings.set_mic_muted(True)
    settings.set_mic_muted(True)
    assert len(changes) == 1


def test_missing_saved_input_falls_back_to_default(settings):
    from PySide6.QtMultimedia import QMediaDevices

    settings._store.setValue("audio/input", "deadbeef")
    device = settings.input_device()
    assert device.id() == QMediaDevices.defaultAudioInput().id()
    assert settings.missing_saved_input is True
    settings.set_input(None)
    settings.input_device()
    assert settings.missing_saved_input is False


def test_muted_voice_never_opens_the_mic(settings):
    from nudge.ui.voice import Voice

    voice = Voice("key", settings)
    states = []
    voice.state.connect(states.append)
    settings.set_mic_muted(True)
    voice.listen()
    assert states == ["muted"] and not voice.active


def test_synth_writes_a_short_mono_wav():
    import io
    import wave

    from nudge.ui.sounds import RATE, synth

    with wave.open(io.BytesIO(synth([(880.0, 0.08), (880.0, 0.08)]))) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, RATE)
        assert 0.18 <= w.getnframes() / RATE <= 0.22


def test_sounds_are_generated_once_into_the_folder(settings, tmp_path):
    from nudge.ui.sounds import TONES, Sounds

    folder = tmp_path / "sounds"
    Sounds(settings, folder)
    files = sorted(p.name for p in folder.iterdir())
    assert files == sorted(f"{name}-v1.wav" for name in TONES)
    stamp = (folder / "tick-v1.wav").stat().st_mtime_ns
    Sounds(settings, folder)
    assert (folder / "tick-v1.wav").stat().st_mtime_ns == stamp


def test_muted_sounds_do_not_play(settings, tmp_path):
    from nudge.ui.sounds import Sounds

    played = []

    class Effect:
        def play(self):
            played.append(True)

    sounds = Sounds(settings, tmp_path / "sounds")
    sounds.effects = {"tick": Effect()}
    sounds.play("tick")
    settings.set_sounds_muted(True)
    sounds.play("tick")
    sounds.play("unknown")
    assert played == [True]


def test_mic_button_toggles_mute_and_lists_toggles(settings):
    from nudge.ui.mic import MicButton

    button = MicButton(settings)
    button.mute.click()
    assert settings.mic_muted and button.mute.toolTip() == "Unmute the mic"
    button.mute.click()
    assert not settings.mic_muted
    button._rebuild()
    texts = [a.text() for a in button.menu_.actions() if not a.isSeparator()]
    assert {"Mute mic", "Mute Nudge's voice", "Sound effects"} <= set(texts)
    next(a for a in button.menu_.actions() if a.text() == "Sound effects").trigger()
    assert settings.sounds_muted
