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
