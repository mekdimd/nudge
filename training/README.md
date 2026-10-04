# Train the "hey nudge" wake word (local, WSL/Linux)

The training code only runs on Linux, so run it in WSL (Ubuntu) with the NVIDIA driver installed on Windows.
Untested end to end. Needs roughly 40 GB of free disk and a few hours.

## Commands (run inside WSL)

```bash
# one-time: tools
sudo apt update && sudo apt install -y git wget build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env          # or open a new terminal

# check the GPU is visible (should list your NVIDIA card)
nvidia-smi

# REPO = this project's folder as WSL sees it, e.g. /mnt/c/Users/<you>/.../nudge (set it once)
REPO=/mnt/c/Users/salmanayazz/Documents/repos/hackathons/stormhacks-2026/nudge

# work from a Linux folder, not /mnt/c (much faster)
mkdir -p ~/nudge-train && cd ~/nudge-train
cp "$REPO/training/train_hey_nudge.ipynb" .

# Jupyter in its own environment
uv venv --python 3.12 jupyter-env
uv pip install --python jupyter-env/bin/python jupyterlab ipykernel pyyaml
source jupyter-env/bin/activate
jupyter lab --no-browser
```

Open the `http://localhost:8888/lab?token=...` link it prints in your Windows browser, open
`train_hey_nudge.ipynb`, and run every cell in order. Keep the `jupyter lab` terminal open.

## Copy the model back to Windows (inside WSL, when training finishes)

```bash
mkdir -p "$REPO/models"
cp ~/nudge-train/my_custom_model/hey_nudge.onnx "$REPO/models/"
```

Then in the project's `.env` (the path is relative to the project folder):

```
WAKE_WORD=models/hey_nudge.onnx
```

and restart Nudge. Tune `WAKE_THRESHOLD` (0.3 to 0.7) if it misses you or fires on other speech.

## What the notebook does differently from the stock one

The stock openWakeWord notebook fails on current setups: `piper-phonemize`, `speexdsp-ns` and
`tensorflow-cpu==2.8.1` have no wheels for new Python versions, and `train.py` needs the old
`generate_samples.py` that `piper-sample-generator` removed in 2026. This copy:

- builds a Python 3.11 environment at `./venv` with `uv` and runs all training and data steps in it
- pins `piper-sample-generator` to v2.0.0 and `torch` to 2.4.1
- skips the TensorFlow/tflite steps (Nudge only uses the `.onnx`)
- uses `target_phrase = "hey nudge"`, `n_samples = 10000`, `n_samples_val = 2000`, `steps = 30000`

If you re-run after a failed attempt, delete the folders the notebook created (`venv`, `openwakeword`,
`piper-sample-generator`, `my_custom_model`) first so old clones don't get in the way.
