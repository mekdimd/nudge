# Launch film review

The 108.15-second cut includes the latest HyperFrames editor changes. Blue request chips type the person's goal, captions use the updated wording, and the email confirmation holds longer. It keeps one window in focus through the task, processing, review and action phases. The opening pointer, three-second reveal, wake word and two-line closing tagline retain their approved style.

## Jev and Peek

Peek takes 2.5 seconds in one continuous shot. The camera zooms toward Peek within the full Nudge bar, the cursor clicks it, and the enabled state holds briefly. The film then shows the browser's debug boxes. The isolated button shot is removed.

After the Labels spotlight, a floating card appears over the existing browser. The goal and candidate rows appear, then the probability bars grow together. Labels wins in mint at 55%; Views, Projects and Milestones dim. A mint connector reaches its screen target. The completed result holds for half a second before the card exits and the cursor resumes. The goal text is 28 px to keep it readable.

The caption and README graphic say "Jev ranks options and selects the highest probability." The box caption says "Nudge draws debug boxes around UI items." The section opens with "Curious how Nudge works?" Jev receives labelled control descriptions. Peek visualizes those controls. The diagram labels its varied scores "Example probabilities"; they are not a recorded response for the illustrated goal.

A fresh subagent signed off on the latest editor cut with no P0 or P1 findings. It inspected beat, phone, seam and exact frames, including the request chips, floating scoring card and sent confirmation. Audio and continuous playback sync were outside that review.

## Verification

| Check | Result |
| --- | --- |
| Application tests | 165 tests passed in the earlier application review. This sync changes video assets and export checks; application tests were not repeated. |
| Package build | The wheel and source distribution built in the earlier application review. The package code is unchanged by this sync. |
| HyperFrames | The full check and focused transition checks passed. Runtime, layout, contrast, craft and audio have no errors. Four timeline-density authoring warnings remain. Runtime, layout, contrast, craft and audio have no warnings. |
| Motion | scripts/verify_jev_motion.mjs passes. It verifies the continuous Peek zoom and click, growing scores, mint selection, dimmed alternatives, connector completion, reading hold, delayed cursor and click, audio timing, reference data and reverse seeking. npm run check includes this verification. |
| Visuals | Full-film storyboard, phone and transition sheets inspected. Exact frames confirm the typed request chips, scoring connector and sent confirmation. The README still graphics retain the earlier review; the GIF and poster are regenerated from this export. |
| Delivery | The complete MP4 decodes without FFmpeg errors. H.264 video is 1920 x 1080 at 60 fps, with 6,489 frames and a 108.15-second picture. The container lasts 108.20 seconds due to the AAC tail. The file is 28.86 MiB. Decoded frames confirm the Peek click, scoring hold and Labels navigation. |
| Audio | Stereo AAC at 48 kHz. The final mix measures -17.02 LUFS integrated and -2.20 dB true peak. Signal analysis reports no warnings. Music and keyboard credits remain in metadata. Audio was measured, not heard. |
| README media | Regenerated the poster and one 13.2-second bank GIF, 2,044 KiB. The GIF begins with the bank request, shows processing and browser actions, and ends on the completed feed. It has no terminal intro. README media links pass. |
| Source integrity | Reviewed scene, timeline, CSS, motion helper, music and bank recording hashes match the delivery render inputs. Python compilation and Git whitespace checks pass. |

Automatic HyperFrames motion sampling is disabled in the pinned CLI. The dedicated timeline assertions and sampled motion frames cover the changed sequence. Timeline-density warnings describe the number of editable clips in a lane; the coherent scenes remain separate compositions.

## Recording limits

The recordings use real Jev and Gemini clients through a browser capture adapter. Native macOS Accessibility permission was unavailable, and no Windows session was tested. Live provider calls were not repeated for this edit. Bank and mail use fictitious local data; no email is sent. GitHub and YouTube use signed-out public pages.

The wake shot loads the repository's Hey Nudge model and replays voice callbacks into the actual UI. It does not verify microphone input, wake detection or transcription. The approval speech uses user-added recordings, whose provider and voice license are not recorded.

Browser sources have 25 fps and Qt sources have 20 fps. Cursor and camera motion render at 60 fps. Waiting is trimmed, typing is retimed and target movement is reconstructed. The film does not measure native task speed.

The email remains the weakest shot at phone width because its fields contain small text. A portrait cut would give those fields more room. The large captions and single-window framing explain the task in this landscape cut.

The current editor HTML defines the film. scripts/sync_timeline.py derives shot-slots.json and audio-cues.json from it. scripts/build_film.py reconstructs an earlier cut and must not replace the editor changes during routine exports. The HyperFrames desktop app retains its editing history.

See [asset sources, rights and capture details](ASSETS.md). The Figma graphic combines a real interface reference and credited travel artwork with saved local detections. The README's example Jev scores explain ranking rather than report a live result.
