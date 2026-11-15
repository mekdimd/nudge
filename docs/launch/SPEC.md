# Nudge launch film

Show the missed-click problem before revealing Nudge. Demonstrate a statement download and YouTube search beside Nudge's live feed. Give Jev and Peek their own shot. The email uses one window at a time so viewers can follow drafting, editing, typing and approval.

## Picture and sound

1920 × 1080, 60 fps, 52.9 seconds, 3,174 frames. Scene cuts fall at frames 240, 372, 768, 1,230, 1,566 and 2,922. The canvas uses #eef2f5 and #222b36. Outfit headings and the email subtitle are 64 px, opening copy is 94 px and the closing address is 64 px. Nudge retains its actual blue pointer and closing mark.

Cursor flights take 0.24 to 0.30 seconds. Clicks compress the cursor for 0.07 seconds and rebound over 0.16 seconds. Nudge's flights leave a 3 px blue trail at 40% opacity, which fades over 0.24 seconds. Human cursors have no trail. Red rings and crosses persist across the opening misses. The problem sentence fades in after the clicks. Browser camera moves zoom 10% toward the target, then return.

Music uses a 120 bpm excerpt of "Inspired" by Kevin MacLeod. Soft clicks, keyboard sounds and Nudge's start, tick, attention and success tones accompany visible actions. Keyboard audio covers the YouTube query and email typing. The final mix targets -17 LUFS and -2.3 dB true peak before AAC encoding. No voiceover. See [asset credits](ASSETS.md).

## Shots

| Frames | Picture | Copy |
| --- | --- | --- |
| 0 to 239 | Three misses on the bank overview, then the centered problem sentence | Hard to click? |
| 240 to 371 | Blue pointer and wordmark, with about 1.8 seconds of stillness after landing | Meet Nudge |
| 372 to 767 | Statements, October detail and PDF download beside Nudge's feed | Download a statement. |
| 768 to 1229 | Excel query typing, suggestion click and tutorial results beside Nudge | Find an Excel tutorial. |
| 1230 to 1565 | Actual Peek outlines over VS Code's GitHub issue list, Labels decision and click | Meet Jev, Nudge's action model. |
| 1566 to 2921 | Compose, Jev and writer processing, draft edit, Type it approval, browser typing, Send approval and result | Draft. Edit. Send. / Nudge types it for you. |
| 2922 to 3173 | Pointer, wordmark and repository address through the music fade | Assisted computer control. |

The email windows slide and crossfade over 0.2 seconds. Jev and the writer process for 3.9 seconds before the draft appears. Its source header and complete review panel form one readable Nudge window. The browser is 1424 × 890 px; the draft is 1320 × 880 px. The draft stays for 5.2 seconds. Subject selection holds for about 0.65 seconds, seven replacement letters appear over about 0.6 seconds, and the edited draft holds before approval. Browser typing stretches by 1.32×. "Nudge types it for you" replaces the heading while the fields fill, and the complete message holds for about two seconds. The Send decision holds for 2.4 seconds and its result for more than three seconds. Each approval and browser click appears once. The final 1.2 seconds of the draft and 0.6 seconds of the Send panel hold their pre-approval frames so the visible clicks land on complete controls.

## Recorded behavior

The actual Nudge loop, Jev client and Gemini writer operate Chrome through a recording adapter. Bank and mail use working local pages with fictitious data. The bank downloads a sample PDF; mail stores a result without sending email. YouTube uses a public search page. Jev's shot uses the public VS Code issue list, signed out, and permits only a Labels navigation click.

Qt frames and browser actions have timestamped records. Browser video timing can drift from wall-clock events, so decoded page transitions locate the cuts and field starts. The values are in assets/browser/edit-points-v5.json. A caption and thicker border emphasize the recorded Labels target in the Jev shot. Cursor flights reconstruct target positions. Actual Qt Peek captures supply the control outlines. The email recording holds real Jev results until 1.2 seconds and writer results until 2.4 seconds to keep loading visible. Provider latency records exclude those holds. Waiting is trimmed and some typing stretches for readability, so the film is not a performance measurement.

Browser sources have 25 fps and Qt sources have 20 fps. Camera, cursor and delivery render at 60 fps. Repeating source frames does not add detail to recorded interface changes. The captures do not exercise native macOS or Windows adapters.

## Design constraints

No invented Nudge controls, offline corner labels, ornamental status captions, slow opening cursor, drifting headlines, gradient washes, glass cards or feature-card grids. Avoid two active email windows, duplicate clicks and crops through draft or approval controls. Preserve the approved opening and closing pointer.

## Delivery

Editable HyperFrames source, local recordings and license records, a 1080p H.264 MP4 with AAC audio, cursor banner, one complete bank GIF, terminal image and labelled interface image.
