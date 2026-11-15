# Launch film review

The film keeps the approved website misses, pointer reveal and closing card. The reveal now holds for a full second after the pointer lands. Bank and YouTube demonstrations remain beside Nudge's actual activity feed. Jev and Peek have a dedicated shot over VS Code's real GitHub issue list.

The email uses one active window at a time. Nudge generates a draft, the black cursor selects "Absent" and types "Missing," then approves the edited text. The browser shows each field filling and holds the completed message. Focus returns to Nudge for Send approval, then to the browser for its Send click and result. Whole review panels replace the previous cropped close-ups.

## Verification

| Check | Result |
| --- | --- |
| Test suite | 165 tests passed with headless Qt, fake adapters and stubbed providers. |
| Package build | Wheel and source distribution built with uv build. |
| Capture and build scripts | Python scripts compile. The JavaScript capture host passes node --check. |
| Actual recordings | Real Jev and Gemini clients completed the YouTube and mail tasks. The mail trace verifies a generated draft, subject selection, replacement typing, approval and local sent result. Jev chose Labels on the public GitHub issue list. The bank capture verifies a downloaded sample PDF. |
| HyperFrames check | Zero errors across 21 layout samples. Runtime, layout, contrast, reading-time and audio checks have zero warnings. Two source-file size warnings remain, explained below. |
| Visual review | Storyboard, phone and all six transition sheets inspected. A fresh agent found no P0 issues and one P1 in the Jev choice at phone width. The fix and final exported decision frames were inspected. Email selection, editing, typing, both approvals and the result were checked in the exported MP4. |
| Delivery decode | The complete MP4 decodes without FFmpeg errors. H.264 video is 1920 × 1080, 60 fps, 2,124 frames and 35.4 seconds. The container lasts 35.586 seconds due to the AAC tail. Stereo audio uses 48 kHz sampling. The file is 8.8 MiB. Music and keyboard credits are in metadata. |
| Audio | -17.0 LUFS integrated, -2.2 dB true peak and zero clipped samples. Keyboard onsets appear during subject editing and form typing. Clicks and Nudge tones remain in the mix. Audio was measured, not heard. |
| README media | One complete 8-second GIF, 120 frames at 960 × 540, 1.3 MiB. CLI start, every bank action and the download result were inspected. The cursor banner, terminal screenshot and labelled interface remain in place. |
| Documentation | Local links and anchors checked across ten Markdown files. One GIF and five collapsible sections. Capture JSON and console logs contain no key patterns. Whitespace checks pass. |

## Review fixes

- The reveal grows from 0.8 to 1.4 seconds.
- Email focus slides between the browser and complete Nudge panels over 0.2 seconds. Inactive cursors stay hidden.
- Actual subject selection and character typing replace the abrupt edit. Keyboard audio has its leading silence trimmed and plays during visible typing.
- Browser field starts and page changes come from decoded frames. This removes misleading click timing from the recorder's wall-clock drift.
- The final 0.4 seconds of both Nudge panels holds their complete pre-approval frame. Each approval lands once before the pan.
- Browser typing stretches by 1.32×. The complete form holds before Send approval; the sent result holds for more than two seconds.
- Jev's shot reveals the actual Peek outlines over a dense public interface. A 64 px caption and stronger border identify its chosen Labels control at phone size.
- Licensed music extends through the longer cut. Nudge tones, click effects and keyboard audio accompany their visible actions. Audio normalization leaves AAC headroom.
- The README GIF and video poster use the revised bank interval. Obsolete split-screen email clips and the incidental YouTube Peek image are removed.

## Retained warnings and limits

HyperFrames warns that the root HTML and email composition exceed its suggested source-file length. The root declares editable sound cues. The email composition keeps its sequential windows and transitions together. These are authoring warnings; runtime and decoding pass.

The email is the densest shot at phone size. Its subject change and approval buttons carry the story; the full body is supporting context. A portrait edit could give the fields more space.

Browser sources have 25 fps and Qt sources have 20 fps. Cursor and camera animation render at 60 fps. Waiting is trimmed, typing is retimed and target movement is reconstructed, so the film does not measure native task speed.

The browser adapter exercises the actual task loop and Qt app. Native macOS Accessibility permission was unavailable, and no Windows session was tested. Bank and mail use fictitious local data. No email is sent. GitHub and YouTube captures use signed-out public pages. The Jev host permits only the public Labels click.

The bank retains its previous design-taste-frontend audit and modern grey and green design. See [asset credits](ASSETS.md) for the music, keyboard recording, click effect and source interfaces.
