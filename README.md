# Nudge

Type what you want to do. Nudge finds the next control on screen, flies a large cursor to it, and presses it for you, one step at a time, until the task is done.

Nudge is for people who find precise mouse work tiring or painful: tremor, RSI, low vision, or anyone who knows what they want but can't easily find or hit the right button. Built at StormHacks 2026.

## How it works

1. Nudge reads the app's accessibility tree (AX on macOS, UI Automation on Windows) and gets a list of named controls with their positions. No screenshots.
2. It sends Jev, TypeSafe's decision model, the goal, what's already been done, and those control labels as numbered options. Jev answers with a choice, a probability for every option, and whether the task is finished. One call per step, usually a few hundred milliseconds.
3. The cursor flies to the chosen control and holds for 0.8 seconds so you can see what's about to happen and press Stop. Then Nudge presses it through the accessibility API, not a simulated click.
4. It waits for the screen to change, then repeats.

Gemini is only called when text has to be written: an email body, a form value, or a web address. It receives the goal and the names of the empty fields, never the screen. You always see and can edit the draft before anything is typed.

## You stay in control

- **Stop** is always on the bar, and **Esc** stops from anywhere.
- When Jev is unsure (top choice under 60%, or within 15 points of the runner-up), Nudge shows the top three options and you pick.
- Anything labelled send, delete, remove, buy, purchase, pay, submit, clear, and similar asks for confirmation first. The cursor and ring turn amber.
- If a step doesn't change anything, Nudge never retries on its own. You choose: try again, click it instead, pick something else, or stop.
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

### macOS

Grant Accessibility permission to the app you launch Nudge from (Terminal, iTerm, Cursor, or VS Code): System Settings, Privacy & Security, Accessibility. Restart Nudge afterwards. Nudge prompts for this on first launch.

Summon the bar with **⌘⇧Space** from the app you want help in.

### Windows

No permission prompt is needed. Run Nudge from a normal (non-admin) terminal; UI Automation can't control apps running as administrator from a non-admin process.

Summon the bar with **Ctrl+Shift+Space**.

## Use

1. Click into the app you want help with. The bar shows it as "in Google Chrome".
2. Press the hotkey, type a goal, and press Enter.
3. Watch the cursor. Press Stop or Esc at any point.

Offline rehearsal, no keys needed, nothing on your computer is touched:

```bash
uv run nudge --offline live_caption
uv run nudge --offline gmail
```

## What we tested

These are the only workflows we have tested end to end. Nudge's action vocabulary is general (press any named control, type into fields, scroll, a few keys, go to a URL), but other apps and tasks are untested and will fail where the app doesn't expose its controls to accessibility APIs.

| Workflow | macOS | Windows |
| --- | --- | --- |
| Chrome: "turn on Live Caption" | works: 4 steps, about 11 s | pending teammate run |
| Gmail in Chrome: "email … that I'm sick and will miss lecture" | works: Compose, draft, confirm Send; 3 steps, about 15 s | pending teammate run |

## Limitations

- Apps that draw their own UI without accessibility labels (many games, some Electron and canvas-based apps) show few or no controls. Nudge says it can't see the control and asks you for help.
- Jev sees control labels, not pixels. Icon-only buttons with no label are invisible to it.
- Typed input only. No voice.
- One app at a time. Tasks that need switching apps stop when the app changes.
- English labels only in testing.

## Privacy

The bar shows what leaves your computer. Jev receives your goal, the app and window name, and the labels of on-screen controls. Gemini receives your goal and the names of empty text fields, only when drafting. No screenshots are taken or sent. Password fields are never read.

## For developers

```bash
uv run pytest                                   # 43 tests, fake adapter, no network
uv run python scripts/check_platform.py --show  # dump what Nudge can see in the frontmost app
uv run python scripts/check_platform.py --press "Settings"
```

Layout: `nudge/core` (action set, Jev client, Gemini writer, safety rules, change detection, the loop), `nudge/platform` (macOS AX, Windows UIA, fake), `nudge/ui` (bar, overlay cursor, Qt bridge).
