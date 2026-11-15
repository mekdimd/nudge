# Nudge launch film

Explain computer control for people with limited dexterity. Show the missed-click problem before introducing Nudge, then demonstrate spoken requests, a statement download, YouTube search, Peek and email editing. Guide attention between Nudge thinking and the browser acting. Each frame has one dominant window.

## Picture and sound

1920 × 1080, 60 fps, 83.9 seconds, 5,034 frames. The canvas uses #eef2f5 and #222b36. Outfit guidance captions are 60 px and centered at y=104. Opening copy is 94 px. The closing tagline is 78 px with an explicit line break after "for." The address is 58 px. Keep Nudge's actual pointer artwork.

Nudge shots are 1372 px wide. Browser shots are 1376 × 765.4 px, centered at y=200. Browser recordings lose only their grey recorder footer. They keep the source aspect ratio. Nudge's video masks follow its encoded frame boundaries, leaving the surrounding canvas transparent as the bar resizes. Static bar images retain their alpha channel.

Cursor flights take 0.24 to 0.30 seconds. Clicks compress the cursor for 0.07 seconds and rebound over 0.16 seconds. Blue flights leave a 3 px trail at 40% opacity, fading over 0.24 seconds. Human cursors have no trail. The hook's final pointer flight lasts 0.86 seconds as it grows into the reveal mark. Browser camera moves zoom 10% toward the target, then return. GitHub navigation and Mail's Send click keep the complete browser header visible.

Music uses a 120 bpm excerpt of "Inspired" by Kevin MacLeod. Soft clicks, typing and Nudge's actual tones accompany visible actions. The mix targets -17 LUFS and -2.3 dB true peak before AAC encoding. No voiceover. See [asset credits](ASSETS.md).

## Shots and focal points

| Frames | Picture | Focal point |
| --- | --- | --- |
| 0 to 323 | Website misses, centered question, blue assistance click and continuous pointer transition | Cursor, then the question, then the blue cursor |
| 324 to 503 | Meet Nudge and the pointer mark | Wordmark and pointer as one lockup |
| 504 to 851 | Hey Nudge and the actual listening UI | Listening bar and its transcript |
| 852 to 1643 | Bank request, Nudge processing, three browser actions and completed feed | One window per phase |
| 1644 to 2501 | Excel tutorial request, Nudge processing, query typing, search and completion | Nudge, then the search field, then results |
| 2502 to 3365 | Peek activation, control outlines, Jev processing, its decision and Labels navigation | Peek button, control outlines, loading feed, then chosen target |
| 3366 to 4757 | Email request, processing, draft edit, typing, approval, Send and result | One window per phase, with a stage subtitle |
| 4758 to 5033 | Pointer, wordmark, two-line tagline and repository | Closing lockup |

The reveal holds for three seconds. Bank and YouTube begin with 1.8 seconds of the request and two seconds of actual processing. Their browser shots reserve about 0.95 seconds before the click or typing starts. The final feed holds for 1.6 seconds.

Peek activation takes 2.4 seconds, including a close-up of the complete button and its enabled state. Its control outlines have 3.4 seconds. Jev's loading indicator has 3.4 seconds with the TypeSafe AI subtitle. Its decision has 1.6 seconds before the browser action and result. A spotlight isolates Labels; the outlines fade before navigation.

Email phases occupy 0–2.6, 2.4–6.3, 6.1–11.3, 11.1–17.3, 17.1–19.5 and 19.3–23.2 seconds within the scene. Each outgoing window fades before the incoming one appears. Stage captions never overlap. Draft review lasts 5.2 seconds, with a 2.7-second subject detail view before returning to the complete draft. The subject selection holds for about 0.65 seconds, seven replacement letters appear over about 0.6 seconds, and the edited draft holds before Type it. Browser typing stretches by 1.32× and the completed message holds before Send approval. The final 1.2 seconds of the draft and 0.6 seconds of the Send panel freeze before their source windows close.

## Recorded behavior

Real Jev and Gemini clients operate Chrome through the recording adapter. The bank downloads a sample PDF. Mail stores a local result without sending email. YouTube searches a public page. The Jev capture uses the signed-out VS Code issue list and permits only public Labels navigation.

The bank and YouTube captures hold real Jev results for at least 1.2 seconds. The Jev shot holds results for 1.5 seconds. The email holds Jev results for 1.2 seconds and writer results for 2.4 seconds. These recording holds leave product code and provider latency records unchanged. Waiting is trimmed and typing is retimed. The film is not a performance measurement.

The wake capture loads models/hey_nudge.onnx and replays the app's voice callbacks into its actual listening UI. It does not validate wake detection, microphone input or transcription. The film's phrase matches that custom model; the default configured wake model can differ.

The builder records scene timing in shot-slots.json and media selections in assets/browser/edit-points-v6.json. Decoded page changes and field starts must agree with visible actions. Browser sources have 25 fps, Qt sources have 20 fps, and camera and cursor movement render at 60 fps. These captures do not exercise native macOS or Windows adapters.

## Design constraints

No simultaneous small split screens, empty dark blocks beneath Nudge, clipped draft controls, duplicate clicks, overlapping captions, offline corner labels, ornamental status text, slow opening cursor, gradient washes, glass cards or feature-card grids. Keep the modern bank and approved pointer artwork.

## Delivery

Editable HyperFrames source, local media and rights records, a 1080p H.264 MP4 with AAC audio, a cursor banner, one complete bank GIF without a terminal intro, a terminal photo and a labelled interface image. The README Photos disclosure contains only the terminal image. The interface callout says "Debug mode."
