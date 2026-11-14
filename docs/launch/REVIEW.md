# Launch film review

Reviewed on macOS with HyperFrames 0.9.47. The 30-second cut opens with three missed clicks on a banking website, reveals Nudge, then shows a statement download, a YouTube how-to search and an email draft with Send approval. Short cursor flights and camera moves lead the eye to each action. An architecture explainer would hide those controls. The earlier 42-second fixture story left too much time on the Nudge bar.

The bank redesign follows the design-taste-frontend audit and typography guidance, with product-interface patterns from frontend-design. Northline uses white and cool-grey backgrounds, restrained green actions, compact Inter type, account balances and transaction rows. Its statement page has a document preview and a working PDF download. The bank identity and account data are fictitious. The film uses Outfit headlines and Nudge's actual blue pointer.

## Verification

| Check | Result |
| --- | --- |
| `QT_QPA_PLATFORM=offscreen uv run pytest -q` | 165 tests passed. Tests use headless Qt, fake adapters and stubbed providers. |
| `uv build` | Wheel and source distribution built. The wheel includes MIT metadata, LICENSE and THIRD_PARTY_NOTICES.md. |
| Browser recording | The actual task loop, Jev client and Gemini writer completed the sample workflows. The host verified a valid downloaded PDF, the requested YouTube results and the local mail result after approval. |
| Bank design | Desktop, narrow and dark layouts checked for overflow, loaded fonts and icons, focus states and control contrast. All three opening miss positions fall outside controls. |
| HyperFrames check, 17 layout samples | Zero errors. Runtime, layout, contrast, craft and audio checks have zero warnings. Two authoring lint warnings remain, explained below. |
| Visual review | Storyboard, phone and transition sheets inspected. The revised tutorial result and both subject states were inspected separately. Decoded delivery frames checked at the hook, approval and outro. |
| FFmpeg full decode | The complete delivery MP4 decoded without errors. |
| FFprobe | 30.000 seconds, 1920 × 1080, H.264 at constant 60 fps, 1,800 frames, stereo AAC at 48 kHz. About 3.7 MiB. Music credit verified in metadata. |
| HyperFrames audio inspection | About -19 LUFS integrated, -2.9 dB true peak and zero clipped samples. Sound was measured, not heard. |
| README | Static banner and poster regenerated. Zero GIFs and ten collapsible sections. Rendered README inspected, local links and anchors checked, issue forms parsed and whitespace checked. |

Browser recordings have 25 fps sources. The cursor and camera animation render at 60 fps, and the delivery file has a constant 60 fps rate. Repeated source frames do not add detail to browser state changes. Waiting between model decisions is trimmed, so the film's timing is not a performance measurement.

## Review fixes

- The opening now uses three fast misses on the bank overview before revealing Nudge. Red rings and persistent crosses identify each failed click.
- The bank uses a compact banking layout, consistent green actions and reconciled sample balances. The recording shows navigation, statement selection and the downloaded result.
- The YouTube ending originally emphasized a sponsored result. A separate capture of the same query now shows the Cars.com tire-changing tutorial. Manual scrolling frames that result; Nudge did not perform that final scroll.
- The original email subject was too small to compare with the edit. Large close-ups now hold the original subject for 0.6 seconds before showing the revised subject.
- Actual Type it and Yes, send controls have larger crops for phone readability. Approval cursors enter near their controls instead of appearing at the top-left.
- Offline corner labels and redundant captions were removed. Licensed music fills the cut, with opening and closing fades.
- The README uses static artwork and collapsible secondary sections. Quick start, use, contribution and license information stay visible.

## Retained warnings and limits

HyperFrames flags two cursor images with matching source and timing in the mail scene. They are separate actors for the Type it and Send approvals, with independently timed child animation. They do not create duplicate audio or video tracks. The checker also flags seven elements on the mail overlay track. That scene keeps draft review, the subject edit and Send approval together so their sequence remains editable in one file. Runtime and decoded frames show the intended actors and transitions.

The email form remains the densest shot at phone size. Its body text provides context; the enlarged subject and approval controls carry the decisions. A portrait version could give the message body its own close-up.

Native macOS Accessibility permission was unavailable for this process. The capture adapter exercises browser controls and the actual Qt task loop, not a native desktop backend. No Windows session was tested. Bank and mail use local sample pages; the mail result sends no email. Blue cursor flights reconstruct recorded target positions, and black cursors represent the opening misses and sample approvals.

The music is an edited excerpt of "Cloud Dancer" by Kevin MacLeod under CC BY 4.0. Attribution and source links are in [ASSETS.md](ASSETS.md). The film has no voiceover and remains understandable when muted.
