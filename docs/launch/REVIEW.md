# Launch film review

The 110.35-second cut preserves the editor's faster bank clicks and shorter email ending. It keeps one window in focus through the task, processing, review and action phases. The opening pointer, three-second reveal, wake word and two-line closing tagline retain their approved style.

## Jev and Peek

Peek takes 2.5 seconds in one continuous shot. The camera zooms toward Peek within the full Nudge bar, the cursor clicks it, and the enabled state holds briefly. The film then shows the browser's debug boxes. The isolated button shot is removed.

After the Labels spotlight, the film pauses before the click. The goal and candidate rows appear, then the probability bars grow together. Labels wins in mint at 55%; Views, Projects and Milestones dim. A blue connector draws from the winning row to its debug box. The completed result holds for about three seconds before the cursor resumes and clicks Labels.

The caption and README graphic say "Jev ranks options and selects the highest probability." Peek's caption says "Peek draws debug boxes around UI items." Jev receives labelled control descriptions. Peek visualizes those controls. The diagram labels its varied scores "Example probabilities"; they are not a recorded response for the illustrated goal.

Two fresh subagent reviews signed off with no P0 or P1 blockers. The second review covered the shortened Peek shot, all 18 Jev review sheets, phone readability and the scoring-to-click handoff. Motion review used sampled frames. Audio was not assessed by the reviewers.

## Verification

| Check | Result |
| --- | --- |
| Application tests | 165 tests passed with headless Qt, fake adapters and stubbed providers. |
| Package build | uv build produced the wheel and source distribution. |
| HyperFrames | The full check and focused transition checks passed. Runtime, layout, contrast, craft and audio have no errors. Five timeline-density authoring warnings remain. |
| Motion | scripts/verify_jev_motion.mjs passes. It verifies the continuous Peek zoom and click, growing scores, mint selection, dimmed alternatives, connector completion, reading hold, delayed cursor and click, audio timing, reference data and reverse seeking. npm run check includes this verification. |
| Visuals | Full-film storyboard, phone and transition sheets inspected. Updated Jev sheets and exact scoring frames inspected after shortening Peek. The README graphic was inspected at full size and 832 pixels wide. |
| Delivery | The complete MP4 decodes without FFmpeg errors. H.264 video is 1920 x 1080 at 60 fps, with 6,621 frames and a 110.35-second picture. The container lasts 110.40 seconds due to the AAC tail. The file is 29.91 MiB. Decoded frames confirm the Peek click, scoring hold and Labels navigation. |
| Audio | Stereo AAC at 48 kHz. The final mix measures -17.02 LUFS integrated and -2.17 dB true peak. Signal analysis reports no warnings. Music and keyboard credits remain in metadata. Audio was measured, not heard. |
| README media | Updated Jev subtitle, regenerated poster and one 12.2-second bank GIF, 2,122 KiB. The GIF begins with the bank request, shows processing and browser actions, and ends on the completed feed. It has no terminal intro. README media links pass. |
| Source integrity | Reviewed scene, timeline and music hashes match the delivery render inputs. Python compilation and Git whitespace checks pass. |

Automatic HyperFrames motion sampling is disabled in the pinned CLI. The dedicated timeline assertions and sampled motion frames cover the changed sequence. Timeline-density warnings describe the number of editable clips in a lane; the coherent scenes remain separate compositions.

## Recording limits

The recordings use real Jev and Gemini clients through a browser capture adapter. Native macOS Accessibility permission was unavailable, and no Windows session was tested. Live provider calls were not repeated for this edit. Bank and mail use fictitious local data; no email is sent. GitHub and YouTube use signed-out public pages.

The wake shot loads the repository's Hey Nudge model and replays voice callbacks into the actual UI. It does not verify microphone input, wake detection or transcription. The approval speech uses user-added recordings, whose provider and voice license are not recorded.

Browser sources have 25 fps and Qt sources have 20 fps. Cursor and camera motion render at 60 fps. Waiting is trimmed, typing is retimed and target movement is reconstructed. The film does not measure native task speed.

The email remains the weakest shot at phone width because its fields contain small text. A portrait cut would give those fields more room. The large captions and single-window framing explain the task in this landscape cut.

The current editor HTML defines the film. scripts/sync_timeline.py derives shot-slots.json and audio-cues.json from it. scripts/build_film.py reconstructs an earlier cut and must not replace the editor changes during routine exports. The HyperFrames desktop app retains its editing history.

See [asset sources, rights and capture details](ASSETS.md). The Figma graphic combines a real interface reference and credited travel artwork with saved local detections. The README's example Jev scores explain ranking rather than report a live result.
