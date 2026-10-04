# Demo script (about 3 minutes)

## Before going on stage

- `.env` has both keys; `uv run python scripts/smoke.py` passes.
- Chrome open on a new tab, Live Caption **off** (Settings, Accessibility).
- Gmail signed in to the demo account, inbox visible, no draft open.
- Spotify open on Home, paused, window visible (not minimised).
- Close notifications (Focus mode on). Make the screen font large.
- Start Nudge: `uv run nudge`, then wait about 15 seconds for the vision models to warm up. The bar sits at the bottom centre.
- Backup: if Wi-Fi fails, `uv run nudge --offline gmail` shows the same UI on a scripted screen. Say that it's a rehearsal.

## 1. The problem (20 s)

"Turning on captions in Chrome is four clicks deep: a three-dot menu, Settings, Accessibility, then a small toggle. For someone with a tremor, every one of those is a small target and a chance to misclick. Nudge lets you type the goal and does the pointing for you."

## 2. Live Caption (40 s)

1. Click into Chrome. The bar shows "in Google Chrome".
2. Type `turn on Live Caption`, press Enter.
3. While it runs, point at:
   - the cursor flying and the hold ring ("half a second to stop it"),
   - the timing line ("Jev took about 130 milliseconds to choose; reading the screen took 30"),
   - the probability bars ("Jev scores every control on screen, so we know when it's unsure").
4. Captions appear in about 4 seconds. "Done in 2 steps."

## 3. Email my professor (40 s)

1. Click into Gmail. Type `email prof.lee@sfu.ca that I'm sick and will miss lecture`.
2. Nudge presses Compose. Gemini's badge lights up: "Gemini only sees the goal and the field names, and only now, because text has to be written."
3. The draft card appears. Edit one word to show it's editable. Press **Type it**.
4. The cursor goes to Send and turns amber. Nudge asks "Press Send?". Say: "Anything that sends, deletes, buys, or submits always asks. The model can't skip this." Press **Yes**.

## 4. Spotify, with Peek on (50 s)

1. Click into Spotify. Press **Peek** on the bar. "Spotify exposes almost nothing to accessibility tools, so Nudge looks at the window instead: these orange boxes are what OmniParser found, running on this laptop."
2. Type `play Olivia Rodrigo`. Approve the search text.
3. Nudge double-clicks the artist, then presses the big Play button. Point at the white outline: "that's Jev's pick." Point at the timing line: "vision takes about a second, and only runs when the accessibility tree isn't enough."
4. Music plays. Turn Peek off.

## 5. Close (30 s)

"Nudge reads the accessibility tree, asks a decision model to choose, and acts through the accessibility API, falling back to on-device vision only when an app hides its controls. Each decision is a fraction of a second. We've tested these workflows on macOS; other apps work as far as they label their controls or show them clearly."

## If something goes wrong

- Jev picks the wrong control: the picker or the recovery panel appears. That's the feature; show it and press **Pick something else**.
- Chrome or Spotify doesn't respond: press Stop, say "it always stops when you ask", and rerun.
- Spotify run starts before vision has warmed up: the first step waits for it. Mention it's loading the model.
