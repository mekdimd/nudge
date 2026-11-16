# Nudge launch film

[Watch the launch video](../assets/nudge-launch.mp4). The editable HyperFrames project renders a 110.35-second film at 1920 × 1080 and 60 fps. It introduces the Hey Nudge wake word, downloads a bank statement, plays an Excel tutorial on YouTube, explains Jev through Peek and reviews an email draft. Large Nudge shots show processing before focus moves to the browser. The Jev demo pauses to animate candidate probabilities and connect the winning control to its debug box.

Bank and mail use fictitious local data. Mail stores a local result without sending email. Real model clients and the task loop run through a browser capture adapter, which does not test native desktop backends. Read [capture limits and media credits](ASSETS.md).

## Edit and render

Use Node.js 22 or later, uv, FFmpeg and Google Chrome. From this directory:

~~~bash
npm ci
npm run dev
uv run python scripts/sync_timeline.py
npm run check
npm run render
~~~

The preview opens the HyperFrames timeline editor. Edit there or open the project in the HyperFrames desktop app. The current index.html and compositions define the film. The sync script refreshes shot-slots.json and audio-cues.json from that HTML. Rendering writes ../assets/nudge-launch.mp4, then normalizes the audio and adds the music credit.

The check command also verifies score growth, the reading hold, reverse seeking and the cursor handoff.

For visual review:

~~~bash
npx --yes hyperframes@0.9.47 snapshot --review
npx --yes hyperframes@0.9.47 snapshot --range 4,6 --frames 8
~~~

## Record the workflows

From the repository root, run uv sync --frozen and npm ci --prefix docs/launch. Configure TYPESAFE_API_KEY and GEMINI_API_KEY in .env. Recording makes real provider calls.

Build the PDFs and serve the local demos in one terminal:

~~~bash
python3 docs/launch/scripts/build_demo.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory docs/launch/demo
~~~

Run these in another terminal:

~~~bash
NUDGE_CAPTURE_PROCESSING_HOLD=1.2 node docs/launch/scripts/capture_host.mjs bank 'http://127.0.0.1:8765/?app=bank&theme=light' 'download my October bank statement'
NUDGE_CAPTURE_PROCESSING_HOLD=1.2 node docs/launch/scripts/capture_host.mjs youtube 'https://www.youtube.com/' 'play a tutorial on Excel pivot tables for beginners'
NUDGE_CAPTURE_PROCESSING_HOLD=1.5 node docs/launch/scripts/capture_host.mjs jev 'https://github.com/microsoft/vscode/issues' 'open Labels in the left sidebar'
NUDGE_CAPTURE_PROCESSING_HOLD=1.2 node docs/launch/scripts/capture_host.mjs mail 'http://127.0.0.1:8765/?app=mail' "email prof.lee@sfu.ca that I'm sick and will miss today's lecture. Use the subject Absent from lecture today"
~~~

An optional final argument selects an .env file outside this checkout. The host starts isolated Chrome and the actual Qt app offscreen. A file RPC connection carries browser controls and actions. The capture script edits the email subject and approves the sample panels. The host checks the downloaded PDF, YouTube results and approved local mail result.

The recordings include browser video at 25 fps, timestamped Qt frames encoded at 20 fps, console output, screenshots and action traces. Peek is active over VS Code's public GitHub issue list in dark mode. The blue cursor reconstructs target positions at 60 fps, and the black cursor marks misses and approvals. NUDGE_CAPTURE_PROCESSING_HOLD holds real Jev results for at least the specified seconds and writer results for twice that time. It keeps processing indicators visible during recording and leaves product code and reported provider latency unchanged.

The wake script loads the Hey Nudge model and replays voice callbacks into the actual listening UI. It uses no microphone or transcription service.

Capture and network timing vary. After recapturing, check page transitions and update media selections and offsets in the current compositions. The editor cut uses continuous bank and YouTube action clips, longer Peek close-ups and prerecorded approval prompts.

Refresh the wake recording and README artwork from the repository root when their inputs change:

~~~bash
uv run python docs/launch/scripts/capture_wake.py
uv run python docs/launch/scripts/build_artwork.py
~~~

Build the README's Dock, accessibility, local vision and Jev graphics from saved inputs:

~~~bash
uv run python docs/launch/scripts/build_desktop_artwork.py
~~~

To refresh the Dock inputs on macOS, add `--refresh-sources`. This reads local app icons and renders Nudge's bar offscreen. It does not open an app or make provider calls.

~~~bash
QT_SCALE_FACTOR=2 uv run python docs/launch/scripts/build_desktop_artwork.py --refresh-sources
~~~

To rebuild only the three control recognition graphics, run `uv run python docs/launch/scripts/build_recognition_artwork.py`. The Figma mockup preserves saved local OCR and OmniParser icon detections. Its blue toolbar outlines and the Jev probability scores are illustrative. See [image sources](ASSETS.md#readme-image-sources).

scripts/build_film.py reconstructs the earlier v6 cut. Running it replaces the editor's HTML, media trims and timing. Use it only to reconstruct that earlier cut.

After rendering, build the poster and the README's single complete bank GIF:

~~~bash
uv run python docs/launch/scripts/build_preview.py
~~~

The GIF reads the bank interval from the current HTML. It begins with the request, shows Nudge processing and every browser action, then holds its completed feed. It has no terminal intro and must stay below 2.5 MiB.

## Music and effects

"Inspired" Kevin MacLeod (incompetech.com). Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The film uses a 110.35-second excerpt, Nudge's actual tones, a soft click effect, keyboard typing and user-added recordings of the draft and Send prompts. Their speech provider is not recorded. Include the [music attribution](ASSETS.md#music-attribution) and [keyboard attribution](ASSETS.md#keyboard-attribution) when sharing the video. The click effect has separate Pixabay rights.

## Project files

| File | Purpose |
| --- | --- |
| index.html | Eight scene slots, music and action sounds |
| compositions/ | Editable HTML scenes |
| assets/ | Local recordings, fonts and runtime |
| demo/ | Working sample bank and mail pages |
| scripts/ | Capture, trim, artwork and audio tools |
| SPEC.md | Timing and design constraints |
| STORYBOARD.md | Shot sequence |
| REVIEW.md | Verification and review findings |
| ASSETS.md | Sources, rights and capture limits |
