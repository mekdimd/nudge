# Launch film review

The 83.9-second film follows one window at a time. Three website misses lead to a successful blue-cursor click, then the pointer carries into "Meet Nudge." The reveal holds for three seconds. The closing card and README banner use two lines: "Computer control for" and "limited dexterity."

The wake shot introduces "Hey Nudge" through the actual listening UI. Bank and YouTube begin with the request and Nudge processing, then give the browser the stage for its actions. The YouTube task searches for an Excel pivot table tutorial. Nudge windows are larger than the earlier split view, and their masks follow the recorded bar as it resizes.

Peek has a close-up of its button and enabled state before the browser's control outlines appear. Jev's loading indicator accompanies "Jev is TypeSafe AI's action model." A spotlight isolates Labels, then the outlines fade before the click and navigation. GitHub's header remains visible.

Email shows Compose, Nudge processing, the complete draft, a subject-field close-up and the edited draft before Type it. The person selects "Absent" and types "Missing." Focus moves to the browser while Nudge fills the fields, returns to Nudge for Send approval, then shows the browser's Send click and result. The Send shot keeps the complete header.

## Verification

| Check | Result |
| --- | --- |
| Test suite | 165 tests passed with headless Qt, fake adapters and stubbed providers. |
| Package build | Wheel and source distribution built with uv build. |
| Capture and build scripts | Ruff passes for the five changed Python scripts. Python compilation and the JavaScript capture host's syntax check pass. |
| Recordings | Real Jev and Gemini clients completed the sample PDF download, Excel search, public GitHub Labels navigation and edited local mail workflow. The mail trace records selection, character typing, both approvals and the sent result. |
| Wake model | The repository's Hey Nudge ONNX model loads in a CPU inference session. The capture replays voice callbacks into the actual UI. |
| HyperFrames check | Zero errors across 17 layout samples. Runtime, layout, contrast, motion, craft and audio checks have zero warnings. Five timeline-density authoring warnings remain. |
| Visual review | Storyboard, phone, transition and detail sheets inspected. A fresh agent flagged phone readability, stale outlines and crops. Close-ups, target isolation and complete headers resolved those findings. Its recheck found no remaining P0 or P1 issues in the revised samples. Forty-two exported frames were inspected. |
| Delivery decode | The complete MP4 decodes without FFmpeg errors. H.264 video is 1920 × 1080, 60 fps, 5,034 frames and 83.9 seconds. The container lasts 84.0 seconds due to the AAC tail. Stereo audio uses 48 kHz sampling. The file is 16.2 MiB and carries music and keyboard credits in metadata. |
| Audio | -17.0 LUFS integrated, -2.3 dB true peak and zero clipped samples. Music, keyboard accents, clicks and Nudge tones remain in the mix. Audio was measured, not heard. |
| README media | One 12.91-second GIF, 155 frames at 960 × 540, 2.37 MiB. It begins with the bank request, shows every action and holds the complete result feed. It has no terminal intro. The banner, poster, terminal photo and labelled interface were inspected. Photos contains only the terminal image; the interface callout says Debug mode. |
| Documentation | Local links and anchors checked across ten Markdown files. One GIF and five collapsible sections. Capture JSON and console logs contain no key patterns. Whitespace checks pass. |

## Recording and editing

Decoded page changes and field starts determine the browser intervals in assets/browser/edit-points-v6.json. Shot timing lives in shot-slots.json. The Jev page change follows the reconstructed click, and its outlines disappear before the result. The final 1.2 seconds of the draft and 0.6 seconds of the Send panel freeze before source dismissal, so each approval lands once on a complete control.

Recording-only holds keep the actual processing indicators visible. The bank and YouTube captures hold real Jev results for at least 1.2 seconds, the Jev capture for 1.5 seconds, and the email writer for 2.4 seconds. These holds leave product code and provider latency records unchanged. Browser typing stretches by 1.32×. Cursor flights take 0.24 to 0.30 seconds, with a faint 3 px trail. Music extends through the cut and fades with the closing card.

The GIF skips the request window's entrance and replaces the final exit with a held result. Its first and last frames both contain the actual Nudge bar. The editable music source is tracked so rebuilding the film needs no ignored local download.

## Retained warnings and limits

The five HyperFrames warnings concern dense caption and overlay tracks. Keeping each task's sequential stages in one composition makes its timing easier to edit together. Runtime, layout and decoding pass.

The full email body and literal activity-feed text remain small on a phone. The subject close-up, large stage captions and approval buttons carry the story. A portrait cut would give the remaining fields more space.

Browser sources have 25 fps and Qt sources have 20 fps. Cursor and camera animation render at 60 fps. Waiting is edited, typing is retimed and target movement is reconstructed, so the film does not measure native task speed.

The browser adapter exercises the task loop and Qt app. Native macOS Accessibility permission was unavailable, and no Windows session was tested. Bank and mail use fictitious local data; no email is sent. GitHub and YouTube use signed-out public pages. The Jev capture permits only public Labels navigation.

The wake shot does not test microphone input, inference-triggered wake detection or transcription. It illustrates the custom Hey Nudge model; the app's default configured wake word can differ.

The bank retains its design-taste-frontend audit and grey and green design. See [asset credits](ASSETS.md) for the music, keyboard recording, click effect and source interfaces.
