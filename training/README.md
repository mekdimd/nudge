# Train the "hey nudge" wake word

The training code only runs on Linux, so use Google Colab (free GPU).

1. Open https://colab.research.google.com, then File > Upload notebook, and pick `train_hey_nudge.ipynb`.
2. Runtime > Change runtime type > T4 GPU.
3. Run every cell in order (about an hour; most of it is downloading data and generating clips).
4. When it finishes, download `hey_nudge.onnx` from the Colab file browser (it is in `my_custom_model/`).
5. Save it as `models/hey_nudge.onnx` here and set in `.env`:
   `WAKE_WORD=<full path to>\models\hey_nudge.onnx`
6. Restart Nudge. Tune `WAKE_THRESHOLD` (0.3 to 0.7) if it misses you or fires on other speech.

The notebook is the stock openWakeWord one with `target_phrase = "hey nudge"`, `n_samples = 10000`,
`n_samples_val = 2000` and `steps = 30000`. Raise them for a stronger model if it is flaky.

## Why the notebook differs from the stock one
Colab now runs Python 3.13 and `piper-sample-generator` was rewritten in 2026, so the stock notebook fails
(`piper-phonemize`, `speexdsp-ns`, `tensorflow-cpu==2.8.1` have no matching versions, and `train.py` needs the
old `generate_samples.py`). This copy builds a Python 3.11 environment with `uv`, pins
`piper-sample-generator` to v2.0.0, skips the TensorFlow/tflite steps (Nudge only uses the .onnx), and runs
the data-download and training steps inside that environment. Untested end to end on Colab.

If you re-run after an earlier failed attempt, use Runtime > Disconnect and delete runtime first, so the
old clones in /content don't get in the way.
