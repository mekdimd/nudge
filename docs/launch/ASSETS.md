# Launch film assets

Footage, fonts, audio and runtime are local. Playback needs no remote assets.

| Asset | Source and rights |
| --- | --- |
| Nudge recordings, panels and terminal output | Actual Qt application and CLI output captured by scripts/capture_browser.py. Nudge's MIT license applies. |
| Bank and mail pages and footage | Working local demos in demo/. Northline, its account holder and financial data are fictitious. Mail stores a local result and sends no email. The code uses Nudge's MIT license. |
| YouTube footage | Public search for "Excel pivot tables for beginners," without signing in. Nudge types the query and chooses a suggestion. YouTube's interface, marks and third-party thumbnails retain their owners' rights. Their incidental appearance demonstrates search and does not imply endorsement. No third-party tutorial plays. |
| GitHub footage and Peek capture | Public VS Code issue list at https://github.com/microsoft/vscode/issues, signed out. The actual Peek overlay outlines the controls, and Jev opens Labels. GitHub, Microsoft and contributor marks and content retain their owners' rights. Their appearance demonstrates control selection and does not imply endorsement. |
| Blue pointer | Nudge's actual artwork exported from nudge/ui/overlay.py. Its Lucide silhouette retains the ISC notice in assets/pointer-LICENSE.txt and THIRD_PARTY_NOTICES.md. |
| Ordinary cursor and bank icons | [Lucide](https://lucide.dev), with pinned lucide-static 0.468.0 artwork. The ordinary cursor changes fill and stroke colors. Notice in demo/assets/icons/LICENSE. |
| README artwork and GIF | Composed from the recordings and console output above, with the same underlying rights. The terminal screenshot renders captured console lines; the GIF starts with the command that launched the browser capture. |
| Outfit font | [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/outfit), SIL Open Font License 1.1. Notice in assets/fonts/OFL.txt. |
| Inter font | [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/inter), SIL Open Font License 1.1. Notice in demo/assets/Inter-OFL.txt. |
| GSAP 3.15.0 | [Official distribution](https://www.npmjs.com/package/gsap), assets/vendor/gsap.min.js. Its [Standard License](https://gsap.com/standard-license/) applies separately. |
| Inspired music excerpt | Kevin MacLeod, [official catalog](https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1600022), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). ISRC USUAN1600022, 120 bpm. |
| Nudge tones | start.wav, tick.wav, attention.wav and success.wav exported with nudge.ui.sounds.synth(TONES). Nudge's MIT license applies. |
| Soft click | The bundled HyperFrames media-use SFX asset, assets/sounds/click-soft.mp3. Source: [Pixabay](https://pixabay.com/sound-effects/), under the [Pixabay Content License](https://pixabay.com/service/license-summary/). Its bundled credits name Pixabay but do not give an individual author or item URL. |
| Keyboard typing | "Keyboard Typing Sounds" by crz1990, [Freesound source](https://freesound.org/people/crz1990/sounds/135872/), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/). Retrieved through HyperFrames media-use and shortened into timed accents. |

## Music attribution

"Inspired" Kevin MacLeod (incompetech.com). Licensed under Creative Commons: By Attribution 4.0 License. https://creativecommons.org/licenses/by/4.0/

The excerpt starts at second 16 of the [official MP3](https://incompetech.com/music/royalty-free/mp3-royaltyfree/Inspired.mp3). It lasts 52.9 seconds, with fades and loudness normalization. The delivery MP4 carries the credit in metadata. Include the attribution above when sharing the film outside this repository.

## Keyboard attribution

"Keyboard Typing Sounds" by crz1990. Source: https://freesound.org/people/crz1990/sounds/135872/. Licensed under CC BY 3.0: https://creativecommons.org/licenses/by/3.0/. The film uses shortened excerpts. Include this attribution when sharing the film.

## Sound effect rights

The HyperFrames SFX credits state that Pixabay permits redistribution as part of a derivative work such as a rendered video. The click and keyboard effects are not MIT-licensed. The source files are build inputs for this film. Follow the [full Pixabay license](https://pixabay.com/service/terms/) for the click and CC BY 3.0 for the keyboard recording.

## Capture limits

The recordings use real Jev and Gemini calls through a browser-only adapter. They do not exercise native macOS accessibility or a Windows session. Native Accessibility permission was unavailable for this process. Capture approvals cover the local sample pages, public YouTube search and read-only Labels navigation on VS Code's issue list.

The blue cursor flights and click pulses reconstruct recorded target coordinates. A faint blue trail follows each Nudge flight. The Jev caption and thicker border emphasize its recorded Labels target. Waiting is trimmed and mail typing stretches by 1.32×. The email capture delays returning real Jev and writer results so their loading indicators remain visible. This recording-only hold does not change product code or the reported provider latency. The film is not a benchmark. Browser sources have 25 fps, Qt sources have 20 fps, and the final cursor and camera animation have 60 fps.

The HyperFrames dart-cursor and cursor-glyph-trail components informed the flights, click rebound and SVG trail. The final scenes use Nudge's artwork and shared GSAP helpers.
