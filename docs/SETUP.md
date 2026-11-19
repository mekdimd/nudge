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

## Check your setup

~~~bash
uv run nudge --version
uv run nudge --doctor
~~~

Both commands exit without starting the UI. Doctor reports Nudge, Python and OS versions, API key presence, accessibility permissions and optional vision dependencies. It uses the same .env lookup as Nudge and never prints key values or makes network calls. Each missing setting or permission includes a suggested fix.

Doctor exits with code 1 when the TypeSafe key is missing, Python or the OS is unsupported, or macOS Accessibility access is missing or cannot be checked. Missing Gemini, voice or vision setup produces warnings. Gemini is required for drafting, and voice and vision are optional.

On macOS, Doctor checks Accessibility and Screen Recording access without requesting permission. Windows has no global accessibility permission toggle. Keep Nudge and the target app at the same privilege level. Doctor checks whether vision dependencies are installed. It does not load or download models, check cached weights or validate API keys.

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

Nudge allows one instance per user across foreground and background modes. Background launches wait for startup to finish. The stop command also reaches a foreground or initializing instance and waits up to five seconds for it to exit.

Closing a background bar hides it. The hotkey brings it back, and the menu bar or tray icon offers Show and Quit. Use --keep-running for the same behavior without detaching from the terminal.

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

Nudge reads one app at a time. It can open apps from the macOS Dock or Windows taskbar and continue in the new foreground app. During screen settling and for 10 seconds after a step, it follows foreground app changes. It cannot tell whether Nudge or you caused the switch. Outside this period, a focus change stops the task. Press Esc or Stop before switching apps yourself during a task.

Controls that appear only on hover may be invisible, and testing so far uses English labels. Linux is not supported.

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
