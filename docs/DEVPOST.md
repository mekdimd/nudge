# Nudge — Devpost draft

## Tagline

Type what you want to do. Nudge points to each step and presses it for you.

## Inspiration

Many everyday computer tasks are a chain of small targets: a three-dot menu, a submenu, a toggle. For people with tremor, RSI, or low vision, each target is effort and a chance to misclick. We liked how TipTour guides you with an animated cursor, and wanted that cursor to also do the pressing, with the person always able to stop it.

## What it does

You type a goal, like "turn on Live Caption" or "email prof.lee@sfu.ca that I'm sick and will miss lecture". Nudge finds the next control, flies an enlarged cursor to it, holds for 0.8 seconds so you can see what's about to happen, then presses it. It checks that the screen changed and repeats until the task is done.

When text has to be written, Gemini drafts it and you approve or edit it before anything is typed. Anything that sends, deletes, buys, or submits asks first. If Nudge is unsure, it shows its top three guesses and you pick.

## How we built it

- **Python + PySide6** for the floating bar and the click-through overlay, which draws the cursor's curved flight, trail, target ring, and hold timer.
- **Accessibility APIs** instead of screenshots: macOS AX through pyobjc, Windows UI Automation through `uiautomation`. Each step reads named controls with their positions and presses them through the API.
- **Jev** (TypeSafe) makes each decision. We send the goal, history, and on-screen control labels as up to 255 options. One call returns a choice, a probability for every option, and "is the task done?". The probabilities drive our safety rules: low confidence or a narrow margin shows the picker instead of acting.
- **Gemini** (`gemini-3.8-flash`, structured JSON output) is used only to write text: email drafts, form values, and URLs. A validator blanks any email address the model invents.

## Challenges

- Chrome only builds its accessibility tree once asked, so the first read can come back empty. We retry the window lookup.
- Chrome's own menus appear inside the main window's tree, while Settings uses a web menu. We had to tell the two apart so the open-menu filter didn't hide the Live Caption toggle.
- Gmail's Compose can take over two seconds to react to an accessibility press. An early fallback clicked it again and opened two compose windows. Now Nudge never retries on its own; the person chooses.
- Making overlay windows float above full-screen apps and every Space on macOS without taking focus.

## Accomplishments

- No screenshots and no agent loop: one Jev call per step, typically a few hundred milliseconds.
- Safety rules that sit outside the model: Stop and Esc, a hold before each press, a confirm on consequential actions, and no automatic retries.
- The same core loop runs on macOS and Windows behind a small adapter interface, with 43 tests on a scripted fake app.

## What we learned

Accessibility trees are rich in some apps and nearly empty in others. Being honest about that, and asking the person for help when the control isn't visible, works better than guessing.

## What's next

- Spoken status with ElevenLabs.
- A vision fallback (YOLO + OCR) for apps that don't expose accessibility labels.
- Voice input.

## Tested scope

We tested two workflows: Chrome Live Caption and sending an email in Gmail, on macOS and Windows. The action vocabulary is general, but other apps are untested.

<!-- Before submitting: keep "and Windows" only if the teammate's Windows runs pass; same for the demo close line. -->


## Built with

python, pyside6, jev, typesafe, gemini, google-genai, pyobjc, uiautomation, macos-accessibility, windows-ui-automation

## Tracks

- SSSS: Best Use of Python
- IATSU: Best Design
- MLH: Best Use of Gemini API
- Enactus: UN SDG (Goal 10, Reduced Inequalities; accessibility)
- MLH: Best Use of ElevenLabs, only if spoken status ships
