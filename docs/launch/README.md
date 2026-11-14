# Nudge launch film

[Watch the 30-second video](../assets/nudge-launch.mp4). The editable HyperFrames project renders at 1920 × 1080 and 60 fps, with a licensed music excerpt. The README uses static images.

The film shows recorded bank, YouTube search and email actions. Nudge's real task loop and model clients run through a recording-only browser adapter. Bank and mail use fictitious data. Mail stores a local result without sending email. These captures do not test native desktop adapters. Read [asset rights and capture limits](ASSETS.md) before sharing.

## Edit and render

Use Node.js 22 or later, FFmpeg and Google Chrome. From this directory:

~~~bash
npm ci
npm run dev
npm run check
npm run render
~~~

The preview opens the HyperFrames timeline editor. Edit the HTML and CSS scenes there or open the project in the HyperFrames desktop app. The delivery MP4 goes to ../assets/nudge-launch.mp4.

For visual review:

~~~bash
npx --yes hyperframes@0.9.47 snapshot --review
npx --yes hyperframes@0.9.47 snapshot --range 23.1,24.8 --frames 8
~~~

## Record the sample workflows

From the repository root, run uv sync --frozen, then install the launch dependencies with npm ci --prefix docs/launch. Configure TYPESAFE_API_KEY and GEMINI_API_KEY in the root .env file. Recording makes real provider calls. Keep the keys out of Git.

Build the PDFs and serve the local demos in one terminal:

~~~bash
python3 docs/launch/scripts/build_demo.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory docs/launch/demo
~~~

Run these commands in another terminal:

~~~bash
node docs/launch/scripts/capture_host.mjs bank \
  'http://127.0.0.1:8765/?app=bank&theme=light' \
  'download my October bank statement'

node docs/launch/scripts/capture_host.mjs youtube \
  'https://www.youtube.com/' \
  'find a video on how to change a tire'

node docs/launch/scripts/capture_host.mjs mail \
  'http://127.0.0.1:8765/?app=mail' \
  "email prof.lee@sfu.ca that I'm sick and will miss today's lecture"
~~~

An optional final argument selects an .env file outside this checkout. The host starts an isolated Chrome context and the actual Qt app offscreen. It reads browser controls and returns actions through a file RPC connection. The Qt capture script approves sample draft and confirmation panels, edits the email subject, and asserts successful outcomes. The host verifies a valid downloaded PDF, search results, and the local mail result after confirmation.

Raw browser video has 25 fps sources. Browser and Qt PNGs, action records and edited clips are in assets/browser/. The blue film cursor reconstructs recorded target positions at 60 fps. The black cursor represents the opening misses and sample approvals.

For the editorial tutorial close-up, run node docs/launch/scripts/record_results.mjs after a successful search. It scrolls the same public query for framing; Nudge does not perform that final scroll.

After recapturing, inspect the raw recordings and update assets/browser/edit-points.json with the decoded state-change times. Capture and network timings vary. Do not reuse old trim points for a new recording. Then rebuild the scene sources and artwork:

~~~bash
python3 docs/launch/scripts/build_film.py
uv run python docs/launch/scripts/build_artwork.py
~~~

The earlier offline capture script, scripts/capture_ui.py, remains available for the project's existing fixtures. The v2 film uses browser recordings.

## Poster and music credit

After rendering, run from the repository root:

~~~bash
uv run python docs/launch/scripts/build_preview.py
~~~

The poster shows the statement download. No GIF is generated.

"Cloud Dancer" Kevin MacLeod (incompetech.com). Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The film uses an edited 30-second excerpt. Include the full [attribution in ASSETS.md](ASSETS.md#music-attribution) when sharing it.

## Project files

| File | Purpose |
| --- | --- |
| index.html | Six scene slots, music and editable closing text |
| compositions/ | One editable HTML file per scene |
| assets/ | Local footage, captures, fonts and runtime |
| demo/ | Functional sample bank and mail pages |
| scripts/ | Recording, trim and artwork tools |
| SPEC.md | Timing, copy and design constraints |
| STORYBOARD.md | Shot sequence |
| REVIEW.md | Verification and visual findings |
| ASSETS.md | Sources, rights, music credit and capture limits |
