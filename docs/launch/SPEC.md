# Nudge launch film

Show the problem before revealing Nudge, then follow its work on three interfaces. The browser occupies the left pane; the actual Nudge feed, loading indicators and approvals remain on the right.

## Picture and sound

1920 × 1080, 60 fps, 31.2 seconds, 1,872 frames. Cuts fall at frames 240, 288, 648, 1,008 and 1,686. The canvas uses #eef2f5 and #222b36. Outfit task headings are 64 px, opening copy is 94 px and the closing address is 64 px. Nudge retains its actual blue pointer and closing mark.

Cursor flights take 0.24 to 0.30 seconds. Clicks compress the cursor for 0.07 seconds and rebound over 0.16 seconds. Red rings and crosses persist across the three opening misses. The problem sentence fades in after the clicks. The browser camera zooms 10% toward each target and returns after the action.

Music uses a 120 bpm excerpt of "Inspired" by Kevin MacLeod. Clicks and Nudge's start, tick, attention and success tones accompany visible actions. The final mix targets -17 LUFS and a -1.5 dB true-peak ceiling. No voiceover. See [asset credits](ASSETS.md).

## Shots

| Frames | Picture | Copy |
| --- | --- | --- |
| 0 to 239 | Three quick misses on the bank overview, then a centered problem sentence | Hard to click? |
| 240 to 287 | The blue pointer arrives beside the wordmark | Nudge |
| 288 to 647 | Statements, October detail and PDF download beside the live Nudge feed | Download a statement. |
| 648 to 1007 | Peek outlines YouTube controls; Nudge types a tire-changing query, selects a suggestion and scrolls results | Find a how-to. |
| 1008 to 1685 | Compose, held draft and subject edit, form fill, held Send approval and local result | Review an email. |
| 1686 to 1871 | Pointer, wordmark and repository address hold through the music fade | Fewer precise clicks. |

The email keeps one composition across four trims. The draft holds for 4.1 seconds and the Send confirmation holds for about 2 seconds. Each approval appears once. The right pane zooms 2.5× into the subject and Type it, and 2.25× into Send confirmation, then returns to the complete feed.

## Recorded behavior

The real Nudge loop, Jev client and Gemini writer operate Chrome through a recording adapter. Bank and mail use working local pages with fictitious data. The bank downloads a sample PDF; mail stores a result without sending email. YouTube uses a public search page and Nudge performs the scroll.

Qt frames and browser footage share timestamped action records. Decoded page transitions establish the browser trim offsets in assets/browser/edit-points-v3.json. The source browser capture has an empty grey strip below its page; edited clips replace that strip with the page background. Cursor flights reconstruct recorded target positions. Waiting between decisions is trimmed, so this is not a performance measurement.

Browser sources have 25 fps and Qt sources have 20 fps. The camera, cursor and delivery render at 60 fps. Repeating source frames does not create more detail in recorded interface changes. The captures do not exercise native macOS or Windows adapters.

## Design constraints

No invented Nudge controls, offline corner labels, ornamental status captions, slow opening cursor, drifting headlines, gradient washes, glass cards or feature-card grid. Preserve the browser and Nudge framing across each task. Show actions before explanatory copy. Keep the approved closing pointer.

## Delivery

Editable HyperFrames source, local recordings and license records, a 1080p H.264 MP4 with AAC audio, a cursor banner, one complete bank GIF, a terminal image and a labelled interface image.
