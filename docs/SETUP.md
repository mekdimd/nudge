# Setup and privacy

Start with the [quick start](../README.md#quick-start). This page covers real apps and optional features.

## Configure real apps

Copy the example configuration:

~~~bash
# macOS
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
~~~

| Setting | Purpose |
| --- | --- |
| TYPESAFE_API_KEY | Jev chooses the next control. Required for real tasks. |
| GEMINI_API_KEY | Drafts text and web addresses for review. Required for drafting. |
| ELEVENLABS_API_KEY | Optional voice input and spoken prompts. |
| ELEVENLABS_VOICE_ID | Optional voice for spoken prompts. |
| WAKE_WORD | Bundled wake model name or ONNX path. Defaults to hey_jarvis. |
| WAKE_THRESHOLD | Wake detection threshold. Defaults to 0.5. |

Keep keys in .env. Git ignores that file. After adding the required keys:

~~~bash
uv run nudge
~~~

With both TypeSafe and Gemini configured, this optional check makes real calls to both services:

~~~bash
uv run python scripts/smoke.py
~~~

On macOS, allow the terminal or editor that launches Nudge in System Settings → Privacy & Security → Accessibility, then restart Nudge. On Windows, a normal process cannot control an elevated app. Run both without administrator privileges.

## Optional voice and vision

With voice configured, click the orb or say the wake word to speak. Click the orb again to stop listening. The mic button mutes the microphone; its arrow chooses a microphone and toggles voice and sound effects.

Some apps expose few accessibility controls. Install the optional local vision dependencies:

~~~bash
uv sync --frozen --extra vision
uv run --extra vision nudge
uv run nudge --no-vision
~~~

This adds PyTorch, Ultralytics and Transformers. OmniParser weights download from Hugging Face on first launch. Vision reads the target window locally; its resulting labels go to Jev. Icon names can be wrong, so expect more requests for your help.

For vision on macOS, also grant the launching terminal or editor screen recording access in System Settings → Privacy & Security.

## Background mode and debugging

~~~bash
uv run nudge --background
uv run nudge --stop
~~~

Closing a background bar hides it. The hotkey brings it back, and the menu bar or tray icon offers Show and Quit. Use --persistent for the same behavior without detaching from the terminal.

Logs go to ~/Library/Logs/Nudge on macOS and %LOCALAPPDATA%\Nudge on Windows. Ctrl+C quits a foreground process.

Click Peek, or start with:

~~~bash
uv run nudge --debug
~~~

Blue outlines mark accessibility controls, green marks text fields, orange marks local vision detections, and white marks Jev's choice.

## Privacy

| Component | What leaves your computer |
| --- | --- |
| Jev | Your goal, app and window names, control labels, roles, positions, context, non-text values, and prior step descriptions. |
| Gemini | Your goal, window title and empty field names when drafting; your goal when drafting an address. |
| Local vision | No screenshot. Nudge processes the target window locally and sends the resulting labels to Jev. |
| ElevenLabs, when enabled | Microphone audio for transcription and prompt text for spoken replies. |

Nudge does not read password fields. Provider icons in the step feed explain their data use. Logs contain task and action details; review them before attaching them to an issue.

## Support and limits

Nudge works within one app at a time. It stops when another app takes focus. Controls that appear only on hover may be invisible, and testing so far uses English labels. Linux is not supported.

Confirmation uses control labels. Unfamiliar labels can bypass a confirmation rule. Each run is capped at 12 steps; uncertain choices and unchanged screens require your decision.

The [original demo notes](DEMO.md) report macOS workflows. Windows has an implementation, but end-to-end Windows results are not yet reported. The [launch recordings](launch/ASSETS.md#capture-limits) exercise the task loop through a browser capture adapter and do not repeat native desktop tests.

## Install without uv

Use Python 3.12 or 3.13:

~~~bash
python -m venv .venv
~~~

Activate the environment:

~~~bash
# macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
~~~

~~~bash
pip install -r requirements.txt
python -m nudge
~~~

Copy .env.example to .env for real tasks. For vision, also install requirements-vision.txt.
