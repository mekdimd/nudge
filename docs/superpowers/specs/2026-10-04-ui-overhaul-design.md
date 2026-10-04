# Nudge UI/UX overhaul

Date: 2026-10-04. Status: approved in brainstorming, ready for an implementation plan.

## Goal

Make it obvious, at a glance, whether Nudge is idle, working, or waiting for you, and who did each step (you, Jev, Gemini, the target app, Nudge). Fewer buttons, clearer copy, a speaking orb, soft sound effects, mic controls, and a readable terminal log.

Priority order (demo is soon): 1. bar layout, states, and timeline with icons; 2. orb; 3. prompts with one Stop and Retry; 4. sounds; 5. mic menu; 6. CLI log.

## Bar layout: activity feed

The bar keeps its current window behaviour (frameless, on top, excluded from capture, bottom-anchored, grows upward, draggable).

Top to bottom:

1. **Header row**: "Nudge" title, the target app chip (real app icon + "in Google Chrome", amber "no app selected" when none), stretch, Peek toggle, quit ✕. The Jev and Gemini privacy badges are removed from the header; their privacy text moves into tooltips on the Jev and Gemini icons in the feed, and into the idle hint.
2. **Feed** (hidden when empty): timeline entries in order, newest at the bottom. Max height about 260 px, then it scrolls and auto-follows the bottom.
3. **Question card** (only while Nudge is waiting for you): sits as the last item of the feed.
4. **Input row**: orb, input field, mic button with ▾, and one action button.

A single muted **hint line** under the input carries messages that aren't part of a run. By default it reads "in {app} · ⌘⇧Space" (Ctrl+Shift+Space on Windows). It's replaced by setup problems (permissions, missing keys), voice state ("Listening…" followed by the live partial transcript, "Didn't hear anything", "Mic is muted"), and Peek counts. Problems are amber; the rest is muted. During a run the hint line is hidden, except for the live transcript when you answer by voice.

### States

| State | Border | Action button | Input |
| --- | --- | --- | --- |
| Idle | none | Go (primary) | editable |
| Working | blue glow, softly pulsing | Stop (outlined red) | read-only, shows "step N of 12" placeholder |
| Needs you | amber glow | Stop | read-only, placeholder tells you what to say ("Say a number, or click") |
| Ended, failed or stopped | none | ↻ Retry (primary) | editable, keeps the goal; editing the text turns the button back into Go |
| Ended, success | none, brief green flash | Go | editable |

There is exactly one Stop button. Question cards never contain Stop. Esc keeps its current behaviour.

The feed clears when the next run starts.

## Timeline

### Entry model

`TimelineEntry(actor, text, detail, state, ms)`:

- `actor`: `you | jev | gemini | app | nudge | vision`
- `text`: one short sentence, bold for the control name (rendered with simple rich text)
- `detail`: muted suffix, e.g. "92% · 130 ms"
- `state`: `running | done | failed | waiting`
- `ms`: optional timing

`running` entries show a spinner and shimmering text (the Cursor/Codex "thinking" look). When the next event for the same step arrives, the running entry is updated in place to `done` or `failed` rather than appending a duplicate.

### Event mapping

A `Timeline` QObject in `nudge/ui/timeline.py` owns the entries and emits `changed(index)` / `added(entry)`. `Nudge` feeds it from existing bridge signals:

| Source | Entry |
| --- | --- |
| run start | `you`: the goal |
| `status("Jev is choosing…")` | `jev` running: "Choosing the next step…" |
| `decided` | that entry becomes done: "Picked **Settings**", detail "92% · 130 ms" |
| `status("Looking at the screen")` / `vision_used` | `vision` running, then done: "Looked at the screen, found 14 controls", detail ms |
| `writer_started` / `writer_used` | `gemini` running "Drafting the text…", then done "Drafted the text", detail seconds |
| `propose` | `app` running: "Pressing **Settings**" (uses the action's `describe()`) |
| new `acted(action, changed)` | that entry becomes done ("Pressed **Settings**") or failed ("nothing changed") |
| `choose` / `confirm` / `recover` / `ask` / `approve_draft` / `approve_url` | `jev` or `nudge` waiting entry, plus the question card |
| `finished` | `nudge` done ("Done in 3 steps · 4.2 s") or failed (the message) |

Other `status` strings that don't map to an entry are ignored by the feed (the feed replaces the old status line).

### Core change

Add one method to `Events` in `nudge/core/loop.py`:

```python
def acted(self, action: Action, changed: bool) -> None: ...
```

The loop calls it after `wait_for_change` returns. `Bridge` forwards it as `sig_acted`. Test doubles in `tests/helpers.py` get a no-op implementation.

### Icons

`nudge/ui/icons.py` returns a cached `QPixmap` per actor, rendered at device pixel ratio, 18 px:

- `jev`: bundled `assets/typesafe.svg` (TypeSafe logo, fetched from their site)
- `gemini`: bundled `assets/gemini.svg` (from svgl.app)
- `app`: the target app's real icon. macOS: `NSRunningApplication.runningApplicationWithProcessIdentifier_(pid).icon()` to PNG to `QPixmap`. Windows: `QFileIconProvider` on the process executable. Fallback: a rounded letter avatar.
- `you`: letter avatar "You"; `nudge`: a tiny static orb; `vision`: an eye glyph SVG.

SVGs render through `QSvgRenderer` (QtSvg ships with PySide6). Tooltips on the Jev and Gemini icons carry the privacy text currently in the badges.

## Orb

`nudge/ui/orb.py`, a 32 px custom-painted `QWidget` driven by a 60 fps `QTimer` only while animating (stops when idle and settled).

- **Idle**: radial blue gradient, 75% opacity, slow 4 s breathe.
- **Listening**: breathe scaled by mic level, plus an expanding ripple ring.
- **Thinking** (working, not speaking): conic gradient rotating once every 2 s.
- **Speaking**: blob outline wobbles and scales by output level (four control points on a closed spline with phase-offset sines).

Levels:

- Mic: `Voice` emits `level(float)` (RMS of each chunk it already reads, 0..1).
- Speaker: `Speaker` precomputes an RMS envelope of the PCM in 30 ms windows when audio arrives and emits `level(float)` from a timer indexed by `QAudioSink.processedUSecs()`.

Levels are smoothed (attack 0.5, release 0.15) before drawing.

## Prompts

All question cards share one layout: a heading sentence, an optional muted explanation, then answer controls. Enter triggers the primary answer, and voice works as it does today (`bar.spoken`).

- **Choose**: "Which one should I press?" Numbered rows "1  Search  41%". Number keys 1 to 3 select.
- **Confirm (risky)**: amber heading "Press "Send"?", muted "This sends the email and can't be undone." Buttons: the action verb ("Send it", amber, Enter) and "Not yet".
- **Recover**: "Pressing "Play" didn't change anything." Buttons: "↻ Retry" (primary, Enter), "Click it instead", and a text-style "Pick another…".
- **Draft**: "Check what I'll type" with editable fields, button "Type it" (primary).
- **URL**: "Open this address?" with editable field, button "Open" (primary).
- **Ask**: the question, optional detail field, button "Continue".

No card has Stop; replying "stop" by voice still works.

## Copy cleanup

- The old status line is gone: the feed carries run progress, and the hint line carries everything else.
- Sentence case, no trailing "…" except on running entries.
- Replace jargon: "Peek" stays (it's a feature name) but its tooltip becomes "Show everything Nudge can see on screen". Timings move into entry details instead of a separate timing row.
- Error copy says what happened and what to do: "Jev isn't set up. Add TYPESAFE_API_KEY to .env and restart Nudge."

## Animations

- Bar height changes animate over 160 ms (ease-out) instead of jumping. Implemented by animating a fixed height on the content container; `_keep_anchored` runs each frame so the bottom edge stays put.
- New feed entries fade and slide up 6 px over 180 ms.
- Border glow pulses (alpha 140 to 220, 1.6 s) while working; fades in/out over 200 ms on state change.
- Remove the overlay's completion flash text duplication: the overlay keeps its cursor and ring; the result message lives only in the feed.

## Sound effects

`nudge/ui/sounds.py`. On startup, synthesize five short WAVs with numpy into the user cache dir (`QStandardPaths.CacheLocation`), regenerate only if missing, and play with `QSoundEffect` at volume 0.35:

| Event | Sound |
| --- | --- |
| run start | soft rising two-note (C6 to E6, 60 ms each, sine with fast decay) |
| each press or click lands | short tick (2 kHz click, 15 ms) |
| needs you | two gentle notes, same pitch (A5, A5) |
| success | three-note rising chime (C6, E6, G6) |
| failure or stop | low soft two-note falling (E4 to C4) |

Muted by the "Sound effects" toggle in the mic menu.

## Mic controls

`nudge/ui/audio_settings.py`: `AudioSettings` QObject persisted with `QSettings`:

- `input_id: bytes | None` (a `QAudioDevice.id()`; `None` means system default; falls back to default if the saved device is gone)
- `mic_muted: bool`, `voice_muted: bool`, `sounds_muted: bool`
- `changed` signal

`Voice` and `WakeWord` call `settings.input_device()` instead of `QMediaDevices.defaultAudioInput()`. Changing the device restarts the wake-word source. `QMediaDevices.audioInputsChanged` refreshes the menu.

Mic button in the input row: click toggles mute (icon crossed out, wake word paused, hotkey shows "Mic is muted" in the feed instead of listening). The ▾ opens a `QMenu`: input devices (checkable, exclusive), separator, "Mute mic" (⌘M / Ctrl+M), "Mute Nudge's voice", "Sound effects" (checkable). When Nudge's voice is muted, prompts are not read aloud and the mic opens immediately for the answer, as it does today without a speaker.

## CLI log

`nudge/ui/console.py` subscribes to `Timeline` and prints one line per entry when it settles (done, failed, waiting), plus the run header and footer. Colors via ANSI, disabled when stdout is not a TTY or `NO_COLOR` is set.

```
▶ turn on Live Caption  · Google Chrome
  Jev     picked "⋮ Menu"            92%  130 ms
  Chrome  pressed "⋮ Menu"           ✓
  Jev     picked "Settings"          88%  110 ms
  Chrome  pressed "Settings"         ✓
  Gemini  drafted the text                1.4 s
  ?       Press "Send"? waiting for you
✓ Done in 3 steps · 4.2 s
```

Actor names are colored (Jev violet, Gemini blue, app green, Nudge white), failures red, waits amber. Startup prints which features are on (Jev, Gemini, voice, wake word, vision) on one line.

## Files

New: `nudge/ui/timeline.py`, `nudge/ui/feed.py` (feed and entry widgets), `nudge/ui/orb.py`, `nudge/ui/icons.py`, `nudge/ui/sounds.py`, `nudge/ui/audio_settings.py`, `nudge/ui/console.py`, `nudge/ui/assets/{typesafe,gemini,eye}.svg`.

Changed: `nudge/ui/bar.py` (layout, states, prompts), `nudge/ui/theme.py` (styles), `nudge/ui/bridge.py` (`acted`), `nudge/ui/voice.py`, `nudge/ui/speaker.py`, `nudge/ui/wake.py` (levels and device), `nudge/ui/overlay.py` (drop result flash text), `nudge/core/loop.py` (`acted`), `nudge/__main__.py` (wiring), `pyproject.toml` (include assets in the wheel), `tests/helpers.py`.

## Error handling

- Icon lookup failures fall back to letter avatars; never raise into the UI.
- Sound generation or playback failure disables sounds silently and logs one line to the CLI.
- A saved mic device that no longer exists falls back to the default and shows "Using the default microphone" in the menu.

## Testing

- Unit: `Timeline` mapping from a scripted event sequence (entry count, actors, in-place updates, failure state); `acted` is called once per press in `test_loop.py`; `AudioSettings` round-trips through `QSettings` with a temp scope; console formatting with color off.
- Manual: offline rehearsal (`--offline live_caption`, `--offline gmail`) to see every state, the confirm card, and sounds; a live Chrome run for real icons; switch mic input mid-session.

## Out of scope

QML rewrite, theming/light mode, a full-screen terminal UI, localisation.
