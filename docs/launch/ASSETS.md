# Launch film assets

The film's fonts, footage, music and runtime are local. Playback needs no remote assets. CLI installation and font discovery may access the network.

| Asset | Source and rights |
| --- | --- |
| Nudge bar and draft/confirmation PNGs | Actual Qt controls captured by scripts/capture_browser.py. Nudge's MIT license applies. Transparent panels sit on the app's dark background. |
| Bank and mail pages | Local working demos in demo/. Northline, its account holder and all financial data are fictitious. Mail records a local result and sends no email. Nudge's MIT license applies to this code. |
| Bank and mail browser recordings | Real task-loop runs through the recording adapter. Action and outcome records are in assets/browser/. Approval automation is confined to sample pages. |
| YouTube recording | Public search for "how to change a tire," recorded without signing in. YouTube's interface, marks and third-party thumbnails retain their owners' rights. Their incidental appearance demonstrates search and does not imply endorsement. No third-party video is played. The final tutorial close-up uses a separate recording of the same query, scrolled manually for framing. |
| Blue pointer | Nudge's actual artwork, exported from nudge/ui/overlay.py. Its Lucide silhouette retains the ISC license in assets/pointer-LICENSE.txt and THIRD_PARTY_NOTICES.md. |
| Ordinary cursor and bank icons | [Lucide](https://lucide.dev), including pinned lucide-static 0.468.0 artwork. The ordinary cursor changes fill and stroke colours. The original notice is in demo/assets/icons/LICENSE. |
| README banner and poster | Composed from these captures, subject to the underlying asset rights. |
| Outfit variable font | [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/outfit), SIL Open Font License 1.1. Original notice in assets/fonts/OFL.txt. |
| Inter variable font | [Google Fonts source](https://github.com/google/fonts/tree/main/ofl/inter), SIL Open Font License 1.1. Original notice in demo/assets/Inter-OFL.txt. |
| GSAP 3.15.0 | [Official distribution](https://www.npmjs.com/package/gsap), stored in assets/vendor/gsap.min.js. Its [Standard License](https://gsap.com/standard-license/) applies separately. |
| Cloud Dancer excerpt | Kevin MacLeod, [official source](https://incompetech.com/music/royalty-free/index.html?isrc=USUAN2300007&Search=Search), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). An edited 30-second excerpt with fades and loudness normalization. |

## Music attribution

"Cloud Dancer" Kevin MacLeod (incompetech.com). Licensed under Creative Commons: By Attribution 4.0 License. https://creativecommons.org/licenses/by/4.0/

The excerpt begins eight seconds into the original track. Its source is the [official MP3](https://incompetech.com/music/royalty-free/mp3-royaltyfree/Cloud%20Dancer.mp3). The delivery MP4 carries the same credit in metadata. Include the attribution above when sharing the film outside this repository.

## Capture limits

The recording uses real Jev and Gemini calls with a browser-only adapter. It does not exercise a native macOS accessibility backend or a Windows session. Native Accessibility permission was unavailable for this process. The cursor flights and click pulses are reconstructed from recorded target coordinates, with waiting trimmed. The recorded timing text is diagnostic output, not a benchmark.

The HyperFrames dart-cursor component informed the curved flights and click rebound. The final scenes use Nudge's artwork and a small shared GSAP helper. No registry component is mounted.
