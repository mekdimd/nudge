# Launch film assets

Footage, fonts, audio and runtime are local. Playback needs no remote assets.

| Asset | Source and rights |
| --- | --- |
| Nudge recordings, panels and terminal output | Actual Qt application and CLI output captured by scripts/capture_browser.py. Nudge's MIT license applies. |
| Bank and mail pages and footage | Working local demos in demo/. Northline, its account holder and financial data are fictitious. Mail stores a local result and sends no email. The code uses Nudge's MIT license. |
| YouTube footage and Peek capture | Public search for "how to change a tire," without signing in. Nudge types the query, chooses a suggestion and scrolls. YouTube's interface, marks and third-party thumbnails retain their owners' rights. Their incidental appearance demonstrates search and does not imply endorsement. No third-party video plays. |
| Blue pointer | Nudge's actual artwork exported from nudge/ui/overlay.py. Its Lucide silhouette retains the ISC notice in assets/pointer-LICENSE.txt and THIRD_PARTY_NOTICES.md. |
| Ordinary cursor and bank icons | [Lucide](https://lucide.dev), with pinned lucide-static 0.468.0 artwork. The ordinary cursor changes fill and stroke colors. Notice in demo/assets/icons/LICENSE. |
| README artwork and GIF | Composed from the recordings and console output above, with the same underlying rights. The terminal screenshot renders captured console lines; the GIF starts with the command that launched the browser capture. |
| Outfit font | [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/outfit), SIL Open Font License 1.1. Notice in assets/fonts/OFL.txt. |
| Inter font | [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/inter), SIL Open Font License 1.1. Notice in demo/assets/Inter-OFL.txt. |
| GSAP 3.15.0 | [Official distribution](https://www.npmjs.com/package/gsap), assets/vendor/gsap.min.js. Its [Standard License](https://gsap.com/standard-license/) applies separately. |
| Inspired music excerpt | Kevin MacLeod, [official catalog](https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1600022), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). ISRC USUAN1600022, 120 bpm. |
| Nudge tones | start.wav, tick.wav, attention.wav and success.wav exported with nudge.ui.sounds.synth(TONES). Nudge's MIT license applies. |
| Soft click | The bundled HyperFrames media-use SFX asset, assets/sounds/click-soft.mp3. Source: [Pixabay](https://pixabay.com/sound-effects/), under the [Pixabay Content License](https://pixabay.com/service/license-summary/). Its bundled credits name Pixabay but do not give an individual author or item URL. |

## Music attribution

"Inspired" Kevin MacLeod (incompetech.com). Licensed under Creative Commons: By Attribution 4.0 License. https://creativecommons.org/licenses/by/4.0/

The excerpt starts at second 16 of the [official MP3](https://incompetech.com/music/royalty-free/mp3-royaltyfree/Inspired.mp3). It lasts 31.2 seconds, with fades and loudness normalization. The delivery MP4 carries the credit in metadata. Include the attribution above when sharing the film outside this repository.

## Sound effect rights

The HyperFrames SFX credits state that Pixabay permits redistribution as part of a derivative work such as a rendered video. The click effect is not MIT-licensed. Its source file is a build input for this film, not a separate sound download. Follow the [full Pixabay license](https://pixabay.com/service/terms/) for other uses.

## Capture limits

The recordings use real Jev and Gemini calls through a browser-only adapter. They do not exercise native macOS accessibility or a Windows session. Native Accessibility permission was unavailable for this process. Capture approvals apply only to the local sample pages and public YouTube search.

The blue cursor flights and click pulses reconstruct recorded target coordinates. Waiting is trimmed. Recorded timing lines are diagnostic output, not benchmarks. Browser sources have 25 fps, Qt sources have 20 fps, and the final cursor and camera animation have 60 fps.

The HyperFrames dart-cursor component informed the curved flights and click rebound. The final scenes use Nudge's artwork and a shared GSAP helper; no registry component is mounted.
