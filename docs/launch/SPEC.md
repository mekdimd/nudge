# Nudge launch film

Show the missed-click problem before revealing Nudge. Demonstrate a statement download and YouTube search beside Nudge's live feed. Give Jev and Peek their own shot. The email uses one window at a time so viewers can follow drafting, editing, typing and approval.

## Picture and sound

1920 × 1080, 60 fps, 35.4 seconds, 2,124 frames. Scene cuts fall at frames 240, 324, 600, 852, 1,080 and 1,938. The canvas uses #eef2f5 and #222b36. Outfit headings are 64 px, opening copy is 94 px and the closing address is 64 px. Nudge retains its actual blue pointer and closing mark.

Cursor flights take 0.24 to 0.30 seconds. Clicks compress the cursor for 0.07 seconds and rebound over 0.16 seconds. Red rings and crosses persist across the opening misses. The problem sentence fades in after the clicks. Browser camera moves zoom 10% toward the target, then return.

Music uses a 120 bpm excerpt of "Inspired" by Kevin MacLeod. Soft clicks, keyboard sounds and Nudge's start, tick, attention and success tones accompany visible actions. The final mix targets -17 LUFS and a -1.5 dB true-peak ceiling. No voiceover. See [asset credits](ASSETS.md).

## Shots

| Frames | Picture | Copy |
| --- | --- | --- |
| 0 to 239 | Three misses on the bank overview, then the centered problem sentence | Hard to click? |
| 240 to 323 | Blue pointer and wordmark, with one second of stillness after landing | Nudge |
| 324 to 599 | Statements, October detail and PDF download beside Nudge's feed | Download a statement. |
| 600 to 851 | Actual query typing, suggestion click and results scroll beside Nudge | Find a how-to. |
| 852 to 1079 | Actual Peek outlines over VS Code's GitHub issue list, Labels decision and click | Meet Jev, Nudge's action model. |
| 1080 to 1937 | Compose, writer, draft edit, Type it approval, browser typing, Send approval and result | Draft. Edit. Send. |
| 1938 to 2123 | Pointer, wordmark and repository address through the music fade | Fewer precise clicks. |

The email windows slide and crossfade over 0.2 seconds. Its source header and complete review panel form one readable Nudge window, without the long feed. The browser is 1424 × 890 px; the draft is 1320 × 880 px. The subject selection holds for about 0.65 seconds, seven replacement letters appear over about 0.6 seconds, and the edited draft holds before approval. Browser typing stretches by 1.32× and the filled email holds for about one second. The Send decision holds for 1.55 seconds and its result for more than two seconds. Each approval and browser click appears once. The last 0.4 seconds of each review panel holds its pre-approval frame so the visible click lands on the complete control before the window leaves.

## Recorded behavior

The actual Nudge loop, Jev client and Gemini writer operate Chrome through a recording adapter. Bank and mail use working local pages with fictitious data. The bank downloads a sample PDF; mail stores a result without sending email. YouTube uses a public search page. Jev's shot uses the public VS Code issue list, signed out, and permits only a Labels navigation click.

Qt frames and browser actions have timestamped records. Browser video timing can drift from wall-clock events, so decoded page transitions locate the cuts and field starts. The values are in assets/browser/edit-points-v4.json. A caption and thicker border emphasize the recorded Labels target in the Jev shot. Cursor flights reconstruct target positions. Actual Qt Peek captures supply the control outlines. Waiting is trimmed and some typing stretches for readability, so the film is not a performance measurement.

Browser sources have 25 fps and Qt sources have 20 fps. Camera, cursor and delivery render at 60 fps. Repeating source frames does not add detail to recorded interface changes. The captures do not exercise native macOS or Windows adapters.

## Design constraints

No invented Nudge controls, offline corner labels, ornamental status captions, slow opening cursor, drifting headlines, gradient washes, glass cards or feature-card grids. Avoid two active email windows, duplicate clicks and crops through draft or approval controls. Preserve the approved opening and closing pointer.

## Delivery

Editable HyperFrames source, local recordings and license records, a 1080p H.264 MP4 with AAC audio, cursor banner, one complete bank GIF, terminal image and labelled interface image.
