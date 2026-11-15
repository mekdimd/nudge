# Launch film review

The 108.7-second editor cut follows one window at a time. Three website misses lead to a successful blue-cursor click, then the pointer carries into "Meet Nudge." The three-second reveal adds the two-line tagline after the title settles. The closing card and README banner also use "Computer control for" above "limited dexterity."

The wake shot introduces "Hey Nudge" through the actual listening UI. Bank and YouTube begin with the request and Nudge processing, then give the browser the stage for continuous actions. The bank ends with a green completion badge. YouTube identifies Gemini during query drafting, then searches for and plays an Excel pivot table tutorial. Nudge windows are larger than the earlier split view, and their masks follow the recorded bar as it resizes.

Peek has a close-up of its button and enabled state before the dark-mode browser's control outlines appear. Guided zooms show the controls. Jev's loading indicator accompanies "Jev is TypeSafe AI's action model" and a blue row highlight. A spotlight isolates Labels, then the outlines fade before the click and navigation.

Email shows Compose, Nudge processing, the spoken draft prompt, a subject-field close-up and the edited draft before Type it. The person selects "Absent" and types "Missing." Focus moves to the browser while Nudge fills the fields, returns to Nudge for a spoken Send approval, then shows the browser's Send click and result. The sync corrected "Nudge reads each step aloud" to "Nudge reads approval prompts aloud" to match the app.

## Verification

The latest export includes the longer wake shot, highlighted phrase and animated voice bars. HyperFrames, visual review, delivery decode and audio measurements below cover this export. Application tests, the package build and recording checks describe the earlier review and were not repeated for this media update.

| Check | Result |
| --- | --- |
| Test suite | 165 tests passed with headless Qt, fake adapters and stubbed providers. |
| Package build | Wheel and source distribution built with uv build. |
| Export scripts | Ruff and Python compilation pass for build_preview.py and sync_timeline.py. Executed exports read eight scene slots and 34 effects and speech cues from the editor HTML. Smoke checks reject scene gaps and missing audio. |
| Recordings | Existing traces and supplied recordings cover the sample PDF download, tutorial playback, public GitHub Labels navigation and edited local mail workflow. Live provider calls were not repeated during this sync. |
| Wake model | The existing capture loads the repository's Hey Nudge ONNX model and replays voice callbacks into the actual UI. Model loading was checked for the earlier cut, not repeated during this sync. |
| HyperFrames check | Zero errors across 17 layout samples. Runtime, layout, contrast, craft and audio checks have zero warnings. Automatic motion sampling is disabled. Five timeline-density authoring warnings remain. |
| Visual review | Storyboard, phone and transition sheets inspected for the updated cut. Extra snapshots at 9.5 and 10.5 seconds show the highlighted wake phrase after its entrance. A decoded delivery frame confirms that phrase appears in the MP4. Existing phone readability limits remain. |
| Delivery decode | The complete MP4 decodes without FFmpeg errors. H.264 video is 1920 × 1080, 60 fps, 6,522 frames and 108.7 seconds. The container lasts 108.8 seconds due to the AAC tail. Stereo audio uses 48 kHz sampling. The file is 27.84 MiB and carries music and keyboard credits in metadata. |
| Audio | -17.0 LUFS integrated and -2.0 dB true peak after AAC encoding. Music, keyboard accents, clicks, Nudge tones and the two prerecorded approval prompts remain in the timeline. The signal analysis reports no warnings. Audio was measured, not heard. |
| README media | Regenerated the poster and one 14.25-second bank GIF, 171 frames at 960 × 540, 2.20 MiB. It begins with the bank request, shows every action and holds the completed feed and badge. It has no terminal intro. Other README artwork belongs to the earlier review. |
| Documentation | Local links and anchors checked across 20 Markdown files. One GIF and six collapsible sections. Fourteen capture JSON and console logs contain no key patterns. Whitespace checks pass. |

## Recording and editing

The saved index.html, compositions, CSS, motion helpers and supplied media define this cut. They were already in the PR worktree. No transfer from another checkout was needed. The HyperFrames desktop app owns its editing history, which this sync leaves intact. File hashes before and after export guard against missing concurrent editor changes.

scripts/sync_timeline.py derives shot-slots.json and audio-cues.json from the current HTML. The preview builder uses that bank interval, skips its first 0.3 seconds and holds its final frame. It chooses the completed feed for the poster. scripts/build_film.py and assets/browser/edit-points-v6.json reconstruct the earlier cut and must not replace these editor changes during routine exports.

Recording-only holds keep the actual processing indicators visible. These holds leave product code and provider latency records unchanged. Waiting and typing are edited. Cursor flights leave a faint blue trail. The 108.7-second music excerpt covers the cut. User-added speech clips read the draft and Send approval text, but their synthesis provider and voice license are not recorded. This export does not verify live text-to-speech.

## Retained warnings and limits

The five HyperFrames warnings concern dense caption and overlay tracks. Keeping each task's sequential stages in one composition makes its timing easier to edit together. Runtime, layout and decoding pass.

The full email body and literal activity-feed text remain small on a phone. The subject close-up, large stage captions and approval buttons carry the story. Some browser and draft zooms crop panel edges to focus on the current target. Those are editor choices retained during this sync. The email is the weakest shot at phone width; a portrait cut would give the fields more space.

Browser sources have 25 fps and Qt sources have 20 fps. Cursor and camera animation render at 60 fps. Waiting is edited, typing is retimed and target movement is reconstructed, so the film does not measure native task speed.

The browser adapter exercises the task loop and Qt app. Native macOS Accessibility permission was unavailable, and no Windows session was tested. Bank and mail use fictitious local data; no email is sent. GitHub and YouTube use signed-out public pages. The Jev capture permits only public Labels navigation.

The wake shot does not test microphone input, inference-triggered wake detection or transcription. It illustrates the custom Hey Nudge model; the app's default configured wake word can differ.

The bank retains its design-taste-frontend audit and grey and green design. See [asset credits](ASSETS.md) for the music, keyboard recording, click effect and source interfaces.
