# Nudge

Type what you want to do. Nudge finds the next control on screen, flies a large cursor to it, and presses it for you, one step at a time, until the task is done.

Nudge is for people who find precise mouse work tiring or painful: tremor, RSI, low vision, or anyone who knows what they want but can't easily find or hit the right button. Built at StormHacks 2026.

## How it works

1. Nudge reads the app's accessibility tree (AX on macOS, UI Automation on Windows) and gets a list of named controls with their positions, usually in 20 to 150 ms.
2. It sends Jev, TypeSafe's decision model, the goal, what's already been done, and those control labels as numbered options. Jev answers with a choice, a probability for every option, and whether the task is finished. One call per step, typically 80 to 200 ms. The bar's feed shows each step in order, with who did it (you, Jev, Gemini, the app) and how long it took. The terminal prints the same log.
3. The cursor flies to the chosen control and holds for half a second so you can see what's about to happen and press Stop. Then Nudge presses it through the accessibility API, or clicks it if the control was found by vision.
4. It waits for the screen to change and, in a browser, for the page to finish loading, then repeats.

**Vision, only when needed.** Some apps (Spotify, many Electron and canvas apps) expose almost nothing to accessibility APIs. When the tree is nearly empty, or Jev is unsure or says the control isn't there, Nudge captures just the target app's window and runs [OmniParser v2](https://huggingface.co/microsoft/OmniParser-v2.0) on your computer: a YOLO detector finds icons, Apple Vision (macOS) or RapidOCR (Windows) reads text, and Florence-2 names unlabeled icons. Those boxes are added as extra options and Jev decides again. One look takes about a second. When Jev is confident on a normal app, vision never runs.

Gemini is only called when text has to be written: an email body, a form value, or a web address. It receives the goal and the names of the empty fields, never the screen. You always see and can edit the draft before anything is typed.

## You stay in control

- **Stop** is always next to the input, and **Esc** stops from anywhere. The bar glows blue while Nudge works and amber when it needs you.
- When Jev is unsure (top choice under 60%, or within 15 points of the runner-up), Nudge shows the top three options and you pick.
- Anything labelled send, delete, remove, buy, purchase, pay, submit, clear, and similar asks for confirmation first. The cursor and ring turn amber.
- If a step doesn't change anything, Nudge never retries on its own. You choose Retry, Click it instead, or Pick another. After a failed run, Go becomes Retry.
- If a different app comes to the front, Nudge stops.
- A run is capped at 12 steps.
- Gemini never invents email addresses, phone numbers, or names. Any address in a draft that wasn't in your goal is blanked.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12 or 3.13 (uv installs it).

```bash
uv sync
cp .env.example .env   # add TYPESAFE_API_KEY, and GEMINI_API_KEY if you want drafting
uv run python scripts/smoke.py   # checks both keys with real calls
uv run nudge
```

Without uv (Python 3.12 or 3.13):

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; on macOS: source .venv/bin/activate
pip install -r requirements.txt  # also installs Nudge itself, so scripts/ can import it
python scripts/smoke.py
python -m nudge
```

`requirements.txt` is generated with `uv export --no-hashes --no-dev -o requirements.txt`; regenerate it after changing dependencies.

### Vision fallback (optional)

Needed for apps like Spotify. Adds PyTorch, Ultralytics, and Transformers (a few GB on disk, about 3 GB of RAM while running). The OmniParser weights download from Hugging Face on first launch, and the models warm up in the background for about 15 seconds.

```bash
uv sync --extra vision                 # or: pip install -r requirements-vision.txt
uv run nudge                           # vision loads automatically when installed
uv run nudge --no-vision               # skip it even if installed
```

### macOS

Grant Accessibility permission to the app you launch Nudge from (Terminal, iTerm, Cursor, or VS Code): System Settings, Privacy & Security, Accessibility. Restart Nudge afterwards. Nudge prompts for this on first launch.

Summon the bar with **⌘⇧Space** from the app you want help in.

### Windows

No permission prompt is needed. Run Nudge from a normal (non-admin) terminal; UI Automation can't control apps running as administrator from a non-admin process.

Summon the bar with **Ctrl+Shift+Space**.

## Use

1. Click into the app you want help with. The bar shows it as "in Google Chrome".
2. Press the hotkey, type a goal, and press Enter.
3. With an ElevenLabs key, say the wake word or click the mic button next to the input to talk. The button lights up whenever Nudge is listening, however listening started, and clicking it again stops. Its arrow picks a microphone and holds the mutes: mic, Nudge's voice, and sound effects.
4. Watch the cursor. Press Stop or Esc at any point. Ctrl+C in the terminal quits.

To keep Nudge running like an installed app, start it in the background:

```bash
uv run nudge --background   # detaches from the terminal; logs go to nudge.log
uv run nudge --stop         # quits the background copy
```

In the background, the × button hides the bar instead of quitting, the hotkey brings it back, and a menu bar (or tray) icon offers Show and Quit. `--persistent` gives the same close-to-hide behavior while staying attached to the terminal. The log lives in `~/Library/Logs/Nudge` on macOS.

**Peek** (the button on the bar, or `uv run nudge --debug`) draws a box around everything Nudge can see in the app: blue for accessibility controls, green for text fields, orange for things only vision found, and a white outline on Jev's pick.

Offline rehearsal, no keys needed, nothing on your computer is touched:

```bash
uv run nudge --offline live_caption
uv run nudge --offline gmail
```

## What we tested

These are the only workflows we have tested end to end. Nudge's action vocabulary is general (press any named control, type into fields, scroll, a few keys, go to a URL), but other apps and tasks are untested and will fail where the app doesn't expose its controls to accessibility APIs.

| Workflow | macOS | Windows |
| --- | --- | --- |
| Chrome: "turn on Live Caption" | works: 2 steps, about 4 s | pending teammate run |
| Gmail in Chrome: "email … that I'm sick and will miss lecture" | works: Compose, draft, confirm Send; 3 steps, about 8 s | pending teammate run |
| Chrome, from a new tab: "open a youtube video on how to change a tire" | works: search results URL, video, 2 to 3 steps, about 10 s | pending teammate run |
| Spotify: "play Olivia Rodrigo" (vision) | works: search, artist, Play; 3 steps, about 11 s | pending teammate run |

Jev took 80 to 230 ms per decision across these runs, averaging about 130 ms.

## Limitations

- Apps that draw their own UI without accessibility labels need the vision fallback. Vision's icon names are guesses ("Play button", "Home icon"), so Jev is less sure there and the picker appears more often. Without vision, Nudge says it can't see the control and asks you for help.
- Controls that only appear on hover (Spotify's per-song play buttons) can't be seen; Nudge double-clicks the song instead.
- One app at a time. Tasks that need switching apps stop when the app changes.
- English labels only in testing.

## Privacy

Hover the Jev, Gemini, or vision icon in the feed to see what leaves your computer. Jev receives your goal, the app and window name, and the labels of on-screen controls. Gemini receives your goal, the window title, and the names of empty text fields, only when drafting. When vision runs, the screenshot of the target window is processed on your computer and never sent anywhere; only the resulting labels go to Jev. Password fields are never read.

## For developers

```bash
uv run pytest                                   # 151 tests, headless Qt, fake adapter, no network
uv run python scripts/check_platform.py --show  # dump what Nudge can see in the frontmost app
uv run python scripts/check_platform.py --press "Settings"
```

Layout: `nudge/core` (action set, Jev client, Gemini writer, safety rules, change detection, the loop), `nudge/platform` (macOS AX, Windows UIA, fake), `nudge/vision` (window capture, OCR, OmniParser detector and captioner), `nudge/ui` (bar, overlay cursor, Qt bridge).
