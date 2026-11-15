# Launch film review

Reviewed on macOS with HyperFrames 0.9.47. The 31.2-second film shows missed website clicks before revealing Nudge, then keeps browser actions beside the actual Nudge feed. It demonstrates a bank statement download, a YouTube how-to search with Peek, and an email draft with subject editing and Send approval.

The bank follows the design-taste-frontend audit and typography guidance, with product-interface patterns from frontend-design. Northline uses cool-grey backgrounds, restrained green actions, compact Inter type and reconciled sample balances. Its statement page previews a document and downloads a working PDF. The bank identity and account data are fictitious.

## Verification

| Check | Result |
| --- | --- |
| Full test suite | 165 tests passed with headless Qt, fake adapters and stubbed providers. |
| Capture adapter tests after the script edits | 2 passed. Python capture/build scripts compile and the JavaScript host passes node --check. |
| uv build | Wheel and source distribution built. MIT metadata, LICENSE and THIRD_PARTY_NOTICES.md remain in the package. |
| Browser recordings | The actual Nudge loop and model clients completed the sample tasks. The host verified a downloaded PDF, requested YouTube results and a local mail result after approval. Bank was recaptured through the corrected Qt encoder; mail and YouTube Qt recordings were rebuilt from their timestamped source frames. |
| HyperFrames check, 17 layout samples | Zero errors. Runtime, layout, contrast, reading-time and audio checks have zero warnings. One authoring warning remains, explained below. |
| Visual review | Storyboard, phone and transition sheets inspected. A fresh agent inspected all nine sheets and all three README images. Updated email close-ups and decoded delivery frames were checked after its finding. |
| Delivery decode | The complete MP4 decoded without FFmpeg errors. H.264 video is 1920 × 1080, 60 fps, 1,872 frames and 31.2 seconds. Container duration is 31.21 seconds due to the AAC tail. Stereo audio has 48 kHz sampling. The file is about 7.3 MiB. Music credit is present in metadata. |
| Audio inspection | -16.8 LUFS integrated, -1.7 dB true peak and zero clipped samples. Click onsets appear in the opening; music fades in at the reveal and continues through the final fade. Audio was measured, not heard. |
| README | GitHub-rendered Markdown and artwork inspected. Local links and anchors checked across ten files. One complete 8-second GIF, 120 frames at 960 × 540, about 1.4 MiB. Five collapsible sections. No key patterns found in capture JSON or console logs. |

Browser sources have 25 fps and Qt sources have 20 fps. Cursor and camera animation render at 60 fps. Source frame repetition does not add detail to recorded interface changes. Waiting between model decisions is trimmed.

## Review fixes

- The opening now shows three fast misses before its centered sentence fades in. Shortening it to "Hard to click?" removed a reading-time warning.
- The browser and Nudge feed stay together. Qt video preserves real loading indicators, draft editing and approval controls.
- Decoded browser transitions corrected the video offsets. The mail result now follows the visible approval and click; each approval appears once.
- The email keeps one composition and holds the draft for 4.1 seconds. The reviewer flagged small subject and approval text. Smooth 2.5× subject/Type it and 2.25× Send close-ups now enlarge those actual controls within the right pane. Both subject states and both approval frames were inspected after this fix.
- The blue cursor moves into the recipient field before the form fills, then to Send. Browser camera moves zoom 10% toward targets.
- Peek appears during YouTube search. Nudge performs the recorded scroll to the tutorial results.
- New licensed music, soft clicks and Nudge's actual tones replace the earlier silent actions. Unused derived clips and the old music were removed.
- The banner has a prominent pointer and curved blue trail. A labelled interface image, actual console output and one complete CLI-to-result GIF support the shorter README.

## Retained warning and limits

The root HTML has 346 lines because it declares the scene hosts and every timed sound cue. Keeping the audio tags visible makes timing and source changes editable. HyperFrames reports this as an authoring-size warning; runtime and delivery decoding pass. The right pane clips its enlarged source intentionally during email close-ups.

The email is still the densest shot at phone size. The subject and approval controls carry the decisions; the complete body is context and does not fit within the close-up. A portrait edit could give the message its own frame.

Native macOS Accessibility permission was unavailable for this process, and no Windows session was tested. The browser capture adapter exercises the task loop and actual Qt app. Bank and mail use local sample pages, and the mail result sends no email. Blue cursor flights reconstruct recorded targets; black cursors represent misses and sample approvals.

"Inspired" by Kevin MacLeod uses CC BY 4.0. The soft click has separate Pixabay rights, and Nudge's synthesized tones use MIT. See [asset credits](ASSETS.md). The film has no voiceover and remains understandable when muted.
