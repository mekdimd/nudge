# Launch film review

The 52.9-second film keeps the approved website misses and pointer artwork. Each demo has more time around its actions. Cursor flights still take 0.24 to 0.30 seconds. The reveal says "Meet Nudge" and holds for about 1.8 seconds after arrival. The closing card says "Assisted computer control." The README banner uses the same description.

Bank and YouTube remain beside Nudge's activity feed. The YouTube task finds an Excel pivot table tutorial, with typing audio during the query. Jev and Peek retain their own shot over VS Code's public GitHub issue list. A 3 px blue trail follows Nudge's flights and fades over 0.24 seconds. Human cursors have no trail.

The email uses one active window at a time. Jev and the writer process for almost four seconds before the draft appears. The person selects "Absent," types "Missing" and approves the edited draft. "Nudge types it for you" appears above the browser while its fields fill. The complete email holds for about two seconds, then focus returns to Nudge for Send approval and to the browser for the Send click and result.

## Verification

| Check | Result |
| --- | --- |
| Test suite | 165 tests passed with headless Qt, fake adapters and stubbed providers. |
| Package build | Wheel and source distribution built with uv build. |
| Capture and build scripts | Changed Python scripts compile. The JavaScript capture host passes node --check. |
| Actual recordings | Real Jev and Gemini clients completed the Excel search and the edited local email. The mail trace records selection, character typing, both approvals and the sent result. The existing bank recording verifies a sample PDF download; the Jev recording verifies public Labels navigation. |
| HyperFrames check | Zero errors across 21 layout samples. Runtime, layout, contrast, reading-time and audio checks have zero warnings. Two source-file size warnings remain, explained below. |
| Visual review | Storyboard, phone and all six transition sheets inspected. A fresh agent found no P0 or P1 issues. Additional frames show Jev processing, the writer, subject selection and editing. Exported frames verify the trail, query typing, field filling, both approvals and result holds. |
| Delivery decode | The complete MP4 decodes without FFmpeg errors. H.264 video is 1920 × 1080, 60 fps, 3,174 frames and 52.9 seconds. The container lasts 53.0 seconds due to the AAC tail. Stereo audio uses 48 kHz sampling. The file is 9.8 MiB. Music and keyboard credits are in metadata. |
| Audio | -17.0 LUFS integrated, -2.3 dB true peak and zero clipped samples. Keyboard onsets appear during YouTube search, subject editing and form typing. Clicks and Nudge tones remain in the mix. Audio was measured, not heard. |
| README media | One complete 8-second GIF, 120 frames at 960 × 540, 1.45 MiB. It starts with the capture command and actual startup output, shows every bank action and holds the download result. The revised banner and poster were inspected. The terminal and labelled interface remain in place. |
| Documentation | Local links and anchors checked across ten Markdown files. One GIF and five collapsible sections. Capture JSON and console logs contain no key patterns. Whitespace checks pass. |

## Recording and editing

Browser page changes and field starts were located in decoded frames. They do not rely solely on the recorder's wall-clock offset. The chosen intervals are in assets/browser/edit-points-v5.json. The final 1.2 seconds of the draft and 0.6 seconds of the Send panel freeze before capture dismissal, so each reconstructed approval lands once on a complete control.

The email recording waits at least 1.2 seconds before returning real Jev results and 2.4 seconds before returning writer results. This keeps the actual processing indicators animating and does not change product code or reported provider latency. Browser typing stretches by 1.32×. Music extends through the longer cut and fades with the closing card. The GIF keeps its original eight-second length by using the extended bank shot without an extra result pad. Obsolete tire-search clips and timing records were removed.

## Retained warnings and limits

HyperFrames warns that the root HTML and email composition exceed its suggested source-file length. The root declares editable sound cues. The email keeps its sequential windows and transitions together. These are authoring warnings; runtime and decoding pass.

The email is the densest shot at phone size. Its subject change, large typing caption and approval buttons carry the story. The full body provides context. A portrait edit could give the fields more space.

Browser sources have 25 fps and Qt sources have 20 fps. Cursor and camera animation render at 60 fps. Waiting is edited, typing is retimed and target movement is reconstructed, so the film does not measure native task speed.

The browser adapter exercises the actual task loop and Qt app. Native macOS Accessibility permission was unavailable, and no Windows session was tested. Bank and mail use fictitious local data. No email is sent. GitHub and YouTube captures use signed-out public pages. The Jev host permits only public Labels navigation.

The bank retains its design-taste-frontend audit and grey and green design. See [asset credits](ASSETS.md) for the music, keyboard recording, click effect and source interfaces.
