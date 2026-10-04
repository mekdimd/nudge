from __future__ import annotations

REPO = "microsoft/OmniParser-v2.0"


def omniparser_file(name: str) -> str:
    from huggingface_hub import hf_hub_download

    return hf_hub_download(REPO, name)


def best_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
