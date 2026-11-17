# Nudge launch film

Explain computer control for people with limited dexterity. Show the missed-click problem before introducing Nudge, then demonstrate spoken requests, a statement download, Excel tutorial playback on YouTube, Peek and email editing. Guide attention between Nudge thinking and the browser acting. Each frame has one dominant window.

## Picture and sound

1920 × 1080, 60 fps, 108.15 seconds, 6,489 frames. The canvas uses #eef2f5 and #222b36. Outfit guidance captions are 72 px, or 84 px for Nudge phases. Opening copy is 94 px. The closing tagline is 84 px with an explicit line break after "for." The address is 64 px. Keep Nudge's actual pointer artwork.

Nudge shots are 1372 px wide. Browser shots are 1376 × 765.4 px, centered at y=200. Browser recordings lose only their grey recorder footer. They keep the source aspect ratio. Nudge's video masks follow its encoded frame boundaries, leaving the surrounding canvas transparent as the bar resizes. Static bar images retain their alpha channel.

The editor uses 0.25 to 0.60-second bank and YouTube cursor flights. Clicks compress the cursor for 0.07 seconds and rebound over 0.16 seconds. Blue flights leave a faint trail that fades after arrival. Human cursors have no trail. The hook's final pointer flight lasts 0.86 seconds as it grows into the reveal mark. Browser camera moves follow the target and then return. Peek close-ups reach 1.8×.

Music uses a 120 bpm excerpt of "Inspired" by Kevin MacLeod. Soft clicks, typing and Nudge's actual tones accompany visible actions. Prerecorded draft and Send prompts occupy 79.85–83.50 and 96.85–100.80 seconds. The mix targets -17 LUFS and -2.3 dB true peak before AAC encoding. See [asset credits](ASSETS.md).

## Shots and focal points

| Frames | Picture | Focal point |
| --- | --- | --- |
| 0 to 323 | Website misses, centered question, blue assistance click and continuous pointer transition | Cursor, then the question, then the blue cursor |
| 324 to 503 | Meet Nudge and the pointer mark | Wordmark and pointer as one lockup |
| 504 to 875 | Hey Nudge and the actual listening UI | Listening bar and its transcript |
| 876 to 1685 | Bank request, Nudge processing, three browser actions and completed feed | One window per phase |
| 1686 to 2828 | Excel tutorial request, Gemini drafting, query typing, search and playback | Nudge, search field, selected tutorial, then playback |
| 2829 to 4349 | Peek activation, control outlines, Jev processing, Labels spotlight, animated ranking and Labels navigation | Peek button, debug boxes, loading feed, probability bars, then the chosen target |
| 4350 to 6212 | Email request, processing, spoken draft prompt, draft edit, typing, spoken Send approval and result | One window per phase, with a stage subtitle |
| 6213 to 6488 | Pointer, wordmark, two-line tagline and repository | Closing lockup |

The reveal lasts three seconds and adds the two-line tagline after the title settles. Bank starts with 2.9 seconds of the request, 2.5 seconds of processing and 6.7 seconds of continuous browser action. A green completion badge accompanies the final 1.4-second feed. YouTube starts with a 2.65-second request and 2.8 seconds of Gemini drafting. Its continuous 13.6-second browser clip includes search, tutorial selection and playback. The playback badge holds for 2.5 seconds.

Peek activation takes 2.5 seconds in one continuous shot. The full Nudge bar appears, the camera zooms 1.55 times toward Peek, and the cursor clicks at 1.6 seconds. The enabled button stays in its original bar before focus moves to the browser. There is no isolated button shot. The dark-mode issue list and control outlines have six seconds, with guided close-ups. Jev's loading indicator has 3.4 seconds under "Jev is TypeSafe AI's decision model." Its decision has 2.6 seconds before the browser action and result. A spotlight isolates Labels before the cursor moves. At local 16.9 seconds, a floating probability card appears over the existing issue tracker. Its goal is "Show the project labels." Candidate rows enter at 17.45 seconds, and bars and counters grow from 17.9 to 19.5 seconds. Labels wins in mint at 55%, with Views at 22%, Projects at 14% and Milestones at 9%. The winner appears at 19.8 seconds. A mint connector draws from 20.2 to 20.8 seconds, linking the card to the outlined Labels target. The completed result holds from 21.05 to 21.55 seconds, then the card exits. The cursor moves at 22.42 seconds and clicks at 22.72 seconds. The recorded action clip starts at 19.45 seconds to retain its original click offset.

The introduction asks "Curious how Nudge works?" The box caption says "Nudge draws debug boxes around UI items." The scoring caption says "Jev ranks options and selects the highest probability." Jev receives labelled control descriptions; the boxes visualize those controls. Scores are labelled "Example probabilities" and do not claim to be a response for the illustrated goal. The card is 540 x 640 px over the browser, with 40 px candidate labels and a 28 px goal. The scoring caption is 64 px. The editor's request captions use blue chips with typed text and a caret.

Email caption phases occupy 0–3.3, 3.3–7.0, 7.0–11.1, 11.1–17.0, 17.0–23.9, 23.9–28.6 and 28.6–31.05 seconds within the scene. The draft first appears with the spoken approval prompt, then a subject close-up shows "Absent" changing to "Missing." The complete edited draft holds before Type it. Browser typing lasts 7.1 seconds. Send approval lasts 4.9 seconds, including the spoken prompt. The sent confirmation and its green check hold for about one second before the outro.

## Recorded behavior

Real Jev and Gemini clients operate Chrome through the recording adapter. The bank downloads a sample PDF. Mail stores a local result without sending email. YouTube searches a public page and plays the selected tutorial. The Jev capture uses the signed-out VS Code issue list and permits only public Labels navigation.

The bank and YouTube captures hold real Jev results for at least 1.2 seconds. The Jev shot holds results for 1.5 seconds. The email holds Jev results for 1.2 seconds and writer results for 2.4 seconds. These recording holds leave product code and provider latency records unchanged. Waiting is trimmed and typing is retimed. The film is not a performance measurement.

The wake capture loads models/hey_nudge.onnx and replays the app's voice callbacks into its actual listening UI. It does not validate wake detection, microphone input or transcription. The film's phrase matches that custom model; the default configured wake model can differ.

The editor HTML defines the current scene timing and media selections. scripts/sync_timeline.py derives shot-slots.json and audio-cues.json from it. assets/browser/edit-points-v6.json belongs to the earlier cut. Decoded page changes and field starts must agree with visible actions. Browser sources have 25 fps, Qt sources have 20 fps, and camera and cursor movement render at 60 fps. These captures do not exercise native macOS or Windows adapters.

The editor's speech clips read actual approval prompt text. The app supports spoken prompts when voice is configured, but this export does not verify live synthesis.

## Design constraints

No simultaneous small split screens, empty dark blocks beneath Nudge, clipped draft controls, duplicate clicks, overlapping captions, offline corner labels, ornamental status text, slow opening cursor, gradient washes, glass cards or feature-card grids. Keep the modern bank and approved pointer artwork.

## Delivery

Editable HyperFrames source, local media and rights records, a 1080p H.264 MP4 with AAC audio, a cursor banner, one complete bank GIF without a terminal intro, a terminal photo and a labelled interface image. The README Photos disclosure contains the Dock mockup, local OCR example and terminal image. The interface callout says "Debug mode" and uses white text on dark blue boxes.
