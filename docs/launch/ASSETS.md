# Launch film assets

Footage, fonts, audio and runtime are local. Playback needs no remote assets.

| Asset | Source and rights |
| --- | --- |
| Nudge recordings, panels and terminal output | Actual Qt application and CLI output captured by scripts/capture_browser.py. Nudge's MIT license applies. |
| Bank and mail pages and footage | Working local demos in demo/. Northline, its account holder and financial data are fictitious. Mail stores a local result and sends no email. The code uses Nudge's MIT license. |
| YouTube footage | Public search and playback for "Excel pivot tables for beginners," without signing in. Nudge types the query, chooses a suggestion and opens a tutorial. YouTube's interface, marks, thumbnails and tutorial footage retain their owners' rights. Their appearance demonstrates browser control and does not imply endorsement. The browser clip is muted; the tutorial's audio is not in the film. |
| GitHub footage and Peek capture | Public VS Code issue list at https://github.com/microsoft/vscode/issues, signed out. The actual Peek overlay outlines the controls, and Jev opens Labels. GitHub, Microsoft and contributor marks and content retain their owners' rights. Their appearance demonstrates control selection and does not imply endorsement. |
| Blue pointer | Nudge's actual artwork exported from nudge/ui/overlay.py. Its Lucide silhouette retains the ISC notice in assets/pointer-LICENSE.txt and THIRD_PARTY_NOTICES.md. |
| Ordinary cursor and bank icons | [Lucide](https://lucide.dev), with pinned lucide-static 0.468.0 artwork. The ordinary cursor changes fill and stroke colors. Notice in demo/assets/icons/LICENSE. |
| README artwork and GIF | Composed from the recordings and console output above, with the same underlying rights. The terminal screenshot renders captured console lines; the GIF begins with the bank request and has no terminal intro. |
| README app icons | Nudge reads the recording browser's actual process icon through its normal UI code. macOS supplied Chrome's dark icon for the November 16, 2026 capture. It is part of the saved screenshots in assets/readme, with no separate icon asset. [Google Chrome](https://www.google.com/chrome/) retains its icon and trademark rights. |
| Dock illustration | Nudge's actual bar rendered offscreen with an example goal. Finder, Safari, Mail, Notes and Calendar icons read from local macOS app bundles with NSWorkspace and resized. Apple retains its icon and trademark rights. The desktop and Dock arrangement are a mockup, with a reconstructed pointer path. No app was opened for this image. |
| Accessibility image | The recorded VS Code issue tracker above, with all 71 recorded controls outlined. The graphic gives text fields the same blue as other accessibility controls. The recording uses the browser capture adapter. |
| Figma canvas and local vision image | [Travel app UI design](https://www.figma.com/community/file/1502285519770933220/travel-app-ui-design-explore-the-world-with-ease) by Samiul Reshad, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), captured from Figma's public community viewer. The graphic enlarges three app designs and places them inside an editor mockup. Toolbar and layers come from Figma's [theme comparison](https://help.figma.com/hc/en-us/articles/5576781786647-Change-themes-in-Figma), [source image](https://help.figma.com/hc/article_attachments/5905110452247). Figma retains its interface and trademark rights. The mockup adds a project title and illustrative blue outlines. Orange regions come from local OCR and OmniParser icon detection. |
| Jev decision image | The recorded VS Code controls with Nudge's actual pointer. The goal and probability distribution illustrate selection. Scores are marked as examples, not a returned Jev response for that goal. |
| Outfit font | [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/outfit), SIL Open Font License 1.1. Notice in assets/fonts/OFL.txt. |
| Inter font | [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/inter), SIL Open Font License 1.1. Notice in demo/assets/Inter-OFL.txt. |
| GSAP 3.15.0 | [Official distribution](https://www.npmjs.com/package/gsap), assets/vendor/gsap.min.js. Its [Standard License](https://gsap.com/standard-license/) applies separately. |
| Inspired music source and excerpt | Kevin MacLeod, [official catalog](https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1600022), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). ISRC USUAN1600022, 120 bpm. |
| Nudge tones | start.wav, tick.wav, attention.wav, success.wav and listen.wav exported with nudge.ui.sounds.synth(TONES). Nudge's MIT license applies. |
| Gemini icon | Google Gemini mark supplied through the editor as assets/gemini-icon.svg. [Google Gemini](https://gemini.google.com/) is the brand source. Google's trademark rights apply separately from Nudge's MIT license; its appearance identifies the drafting provider and does not imply endorsement. |
| Spoken approval prompts | User-added voice-draft.mp3 and voice-send.mp3 with matching transcript JSON. They read Nudge's draft and Send approval text. The generation provider and voice license are not recorded in the supplied files. Nudge's MIT license covers the prompt text, not a third-party voice or synthesis service. |
| Soft click | The bundled HyperFrames media-use SFX asset, assets/sounds/click-soft.mp3. Source: [Pixabay](https://pixabay.com/sound-effects/), under the [Pixabay Content License](https://pixabay.com/service/license-summary/). Its bundled credits name Pixabay but do not give an individual author or item URL. |
| Keyboard typing | "Keyboard Typing Sounds" by crz1990, [Freesound source](https://freesound.org/people/crz1990/sounds/135872/), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Retrieved through HyperFrames media-use and shortened into timed accents. |

## README image sources

scripts/build_desktop_artwork.py builds the Dock mockup and three control recognition graphics from saved inputs. Its --refresh-sources option reads local app icons and renders Nudge's bar offscreen. It uses no provider keys and does not operate the desktop. scripts/build_recognition_artwork.py can rebuild the accessibility, vision and Jev graphics on their own.

The Figma graphic preserves 38 saved detections from Apple Vision OCR and Microsoft's OmniParser v2 icon detector, including the back arrow and heart. Detection uses Nudge's 0.05 confidence and 0.1 overlap thresholds. The build translates those detections into the mockup and labels blue as Accessibility and orange as Local vision. Florence icon captioning was not run for this illustration. The blue toolbar outlines are illustrative; the image is not a native desktop verification or a live Figma run.

The travel artwork was cropped and resized from the public community viewer on November 15, 2026. Samiul Reshad's design retains its CC BY 4.0 license in both the saved input and composed README image. The Figma interface reference retains Figma's rights. These assets are not covered by Nudge's MIT license.

The interface diagram uses white text on #245eb7 label boxes. The label contrast is 6.3:1. Connector lines use the same blue. The README banner and diagram use a fresh bank capture in assets/readme. The browser host passes Chrome's process ID to Nudge, which draws the app icon in the target badge and action rows. scripts/build_artwork.py places those complete screenshots into the artwork. The capture's log, actions and trace preserve its results and widget geometry.

Rebuild the graphics with `uv run python docs/launch/scripts/build_artwork.py --only banner interface` from the repository root. To capture new stills, serve demo on 127.0.0.1:8765 and run `node scripts/capture_host.mjs bank http://127.0.0.1:8765/ 'download my October bank statement' /path/to/private.env /tmp/nudge-readme-capture` from docs/launch. Copy bank-idle.png, bank-done.png, bank-trace.json, bank-console.log and bank-actions.json into assets/readme, then rebuild. The output directory keeps README captures separate from the film's recordings.

## Music attribution

"Inspired" Kevin MacLeod (incompetech.com). Licensed under Creative Commons: By Attribution 4.0 License. https://creativecommons.org/licenses/by/4.0/

The excerpt uses the [official MP3](https://incompetech.com/music/royalty-free/mp3-royaltyfree/Inspired.mp3). The delivery excerpt lasts 108.15 seconds, with fades and delivery loudness normalization. The delivery MP4 carries the credit in metadata. Include the attribution above when sharing the film outside this repository.

## Keyboard attribution

"Keyboard Typing Sounds" by crz1990. Source: https://freesound.org/people/crz1990/sounds/135872/. Licensed under CC BY 3.0: https://creativecommons.org/licenses/by/3.0/. The film uses shortened excerpts. Include this attribution when sharing the film.

## Sound effect rights

The HyperFrames SFX credits state that Pixabay permits redistribution as part of a derivative work such as a rendered video. The click and keyboard effects are not MIT-licensed. The source files are build inputs for this film. Follow the [full Pixabay license](https://pixabay.com/service/terms/) for the click and CC BY 3.0 for the keyboard recording.

## Capture limits

The recordings use real Jev and Gemini calls through a browser-only adapter. They do not exercise native macOS accessibility or a Windows session. Native Accessibility permission was unavailable for this process. Capture approvals cover the local sample pages, public YouTube search and playback, and read-only Labels navigation on VS Code's issue list.

The blue cursor flights and click pulses reconstruct recorded target coordinates. A faint blue trail follows each Nudge flight. The Jev caption and thicker border emphasize its recorded Labels target. The editor adds dark-mode footage, control close-ups, continuous bank and YouTube clips and longer email review. Waiting is trimmed and mail typing is retimed. The email capture delays returning real Jev and writer results so their loading indicators remain visible. This recording-only hold does not change product code or the reported provider latency. The film is not a benchmark. Browser sources have 25 fps, Qt sources have 20 fps, and the final cursor and camera animation have 60 fps.

The app can speak draft and confirmation prompts when voice is configured. The film uses prerecorded prompt audio added in the editor. This sync and render do not verify a live text-to-speech service. Audio is measured, not heard.

The HyperFrames dart-cursor, cursor-glyph-trail and yt-feather-highlight components informed the flights, click rebound, SVG trail and Peek spotlight. The final scenes use Nudge's artwork and shared GSAP helpers.

The wake shot loads the repository's models/hey_nudge.onnx and replays voice callbacks into Nudge's actual UI. It does not exercise a microphone, wake detection or transcription. The custom model supports the illustrated phrase; the app's default configuration can use another wake word.

## Animated Jev ranking

The video overlays an editable probability card on its recorded VS Code issue tracker. It shares the README's varied example probabilities in assets/desktop/jev-example.json. Those scores illustrate ranking; they are not the recorded Jev response for the shown goal. The browser clip performs the recorded Labels click, and a decoded final frame holds the resulting page through the transition to mail.

The animated-bar-chart registry component informed the deterministic growth tween. The current scene uses editable rows, mint probability bars and a connector in compositions/jev.html. Jev ranks labelled actions, and Nudge's debug boxes outline the corresponding UI items.

The model caption says "Jev is TypeSafe AI's decision model." [TypeSafe's documentation](https://docs.typesafe.ai/introduction) describes Jev as making structured decisions. Nudge uses those decisions to choose its next action.
