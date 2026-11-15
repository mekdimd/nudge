# Nudge launch film

[Watch the launch video](../assets/nudge-launch.mp4). The editable HyperFrames project renders at 1920 × 1080 and 60 fps. It introduces the Hey Nudge wake word and follows one window at a time through bank, YouTube, Peek and email tasks. Large Nudge shots show processing before focus moves to the browser.

Bank and mail use fictitious local data. Mail stores a local result without sending email. Real model clients and the task loop run through a browser capture adapter, which does not test native desktop backends. Read [capture limits and media credits](ASSETS.md).

## Edit and render

Use Node.js 22 or later, uv, FFmpeg and Google Chrome. From this directory:

~~~bash
npm ci
npm run dev
npm run check
npm run render
~~~

The preview opens the HyperFrames timeline editor. Edit the HTML and CSS there or open the project in the HyperFrames desktop app. Rendering writes ../assets/nudge-launch.mp4, then normalizes the audio and adds the music credit.

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
NUDGE_CAPTURE_PROCESSING_HOLD=1.2 node docs/launch/scripts/capture_host.mjs youtube 'https://www.youtube.com/' 'find a tutorial on Excel pivot tables for beginners'
NUDGE_CAPTURE_PROCESSING_HOLD=1.5 node docs/launch/scripts/capture_host.mjs jev 'https://github.com/microsoft/vscode/issues' 'open Labels in the left sidebar'
NUDGE_CAPTURE_PROCESSING_HOLD=1.2 node docs/launch/scripts/capture_host.mjs mail 'http://127.0.0.1:8765/?app=mail' "email prof.lee@sfu.ca that I'm sick and will miss today's lecture. Use the subject Absent from lecture today"
~~~

An optional final argument selects an .env file outside this checkout. The host starts isolated Chrome and the actual Qt app offscreen. A file RPC connection carries browser controls and actions. The capture script edits the email subject and approves the sample panels. The host checks the downloaded PDF, YouTube results and approved local mail result.

The recordings include browser video at 25 fps, timestamped Qt frames encoded at 20 fps, console output, screenshots and action traces. Peek is active in the Jev capture over VS Code's public GitHub issue list. The blue cursor reconstructs target positions at 60 fps, and the black cursor marks misses and approvals. NUDGE_CAPTURE_PROCESSING_HOLD holds real Jev results for at least the specified seconds and writer results for twice that time. It keeps processing indicators visible during recording and leaves product code and reported provider latency unchanged.

The wake script loads the Hey Nudge model and replays voice callbacks into the actual listening UI. It uses no microphone or transcription service.

Capture and network timing vary. After recapturing, decode the page transitions and update the segment selections and video offsets in scripts/build_film.py. Do not reuse old trim points without checking them. The builder writes the chosen values to assets/browser/edit-points-v6.json.

Rebuild the film source and artwork from the repository root:

~~~bash
uv run python docs/launch/scripts/capture_wake.py
uv run python docs/launch/scripts/build_film.py
uv run python docs/launch/scripts/build_artwork.py
~~~

After rendering, build the poster and the README's single complete bank GIF:

~~~bash
uv run python docs/launch/scripts/build_preview.py
~~~

The GIF begins with the bank request, shows Nudge processing and every browser action, then holds its completed feed. It has no terminal intro and must stay below 2.5 MiB.

## Music and effects

"Inspired" Kevin MacLeod (incompetech.com). Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The film uses an 83.9-second excerpt, Nudge's actual tones, a soft click effect and keyboard typing. Include the [music attribution](ASSETS.md#music-attribution) and [keyboard attribution](ASSETS.md#keyboard-attribution) when sharing the video. The click effect has separate Pixabay rights.

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
