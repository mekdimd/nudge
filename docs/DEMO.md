# Demo script (about 3 minutes)

## Before going on stage

- `.env` has both keys; `uv run python scripts/smoke.py` passes.
- Chrome open on a new tab, Live Caption **off** (Settings, Accessibility).
- Gmail signed in to the demo account, inbox visible, no draft open.
- Close notifications (Focus mode on). Make the screen font large.
- Start Nudge: `uv run nudge`. The bar sits at the bottom centre.
- Backup: if Wi-Fi fails, `uv run nudge --offline gmail` shows the same UI on a scripted screen. Say that it's a rehearsal.

## 1. The problem (30 s)

"Turning on captions in Chrome is four clicks deep: a three-dot menu, Settings, Accessibility, then a small toggle. For someone with a tremor, every one of those is a small target and a chance to misclick. Nudge lets you type the goal and does the pointing for you."

## 2. Live Caption (60 s)

1. Click into Chrome. The bar shows "in Google Chrome".
2. Type `turn on Live Caption`, press Enter.
3. While it runs, point at:
   - the cursor flying and the hold ring ("you get almost a second to stop it"),
   - the Jev badge in milliseconds ("one decision per step, no screenshots, a few hundred ms"),
   - the probability bars ("Jev scores every control on screen, so we know when it's unsure").
4. Captions appear. "Done after 4 steps."

## 3. Email my professor (60 s)

1. Click into Gmail. Type `email prof.lee@sfu.ca that I'm sick and will miss lecture`.
2. Nudge presses Compose. Gemini's badge lights up: "Gemini only sees the goal and the field names, and only now, because text has to be written."
3. The draft card appears. Edit one word to show it's editable. Press **Type it**.
4. The cursor goes to Send and turns amber. Nudge asks "Press Send?". Say: "Anything that sends, deletes, buys, or submits always asks. The model can't skip this." Press **Yes**.

## 4. Close (30 s)

"Nudge reads the accessibility tree, asks a decision model to choose, and acts through the accessibility API. It's fast because it doesn't screenshot and doesn't run an LLM agent loop. We've tested these two workflows on macOS and Windows; other apps work as far as they label their controls."

## If something goes wrong

- Jev picks the wrong control: the picker or the recovery panel appears. That's the feature; show it and press **Pick something else**.
- Chrome doesn't respond: press Stop, say "it always stops when you ask", and rerun.
