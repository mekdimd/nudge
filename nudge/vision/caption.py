"""OmniParser's icon captioner: Florence-2 fine-tuned to name UI icons ("play button", "search").

OmniParser ships the weights in Florence-2's original remote-code layout; transformers now has
Florence-2 built in with different parameter names, so the weights are renamed on load.
"""

from __future__ import annotations

import re

from .weights import omniparser_file

BASE = "florence-community/Florence-2-base-ft"
PROMPT = "<CAPTION>"
CROP = 64
BATCH = 32

_RENAMES = [
    (re.compile(r"^language_model\.model\."), "model.language_model."),
    (re.compile(r"^language_model\.lm_head\."), "lm_head."),
    (re.compile(r"^image_pos_embed\."), "model.multi_modal_projector.image_position_embed."),
    (re.compile(r"^image_proj_norm\."), "model.multi_modal_projector.image_proj_norm."),
    (re.compile(r"^visual_temporal_embed\."), "model.multi_modal_projector.visual_temporal_embed."),
    (re.compile(r"^vision_tower\."), "model.vision_tower."),
    (re.compile(r"\.(channel_attn|window_attn)\.fn\."), r".\1."),
    (re.compile(r"\.(channel_attn|window_attn)\.norm\."), ".norm1."),
    (re.compile(r"\.ffn\.norm\."), ".norm2."),
    (re.compile(r"\.ffn\.fn\.net\."), ".ffn."),
    (re.compile(r"\.(conv1|conv2)\.fn\.dw\."), r".\1."),
    (re.compile(r"(convs\.\d+)\.proj\."), r"\1.conv."),
]


def convert(state: dict) -> dict:
    out = {}
    for key, tensor in state.items():
        if key == "language_model.final_logits_bias":
            continue
        if key == "image_projection":
            out["model.multi_modal_projector.image_projection.weight"] = tensor.T.contiguous()
            continue
        for pattern, repl in _RENAMES:
            key = pattern.sub(repl, key)
        out[key] = tensor
    return out


class Captioner:
    def __init__(self, device: str):
        import torch
        from safetensors.torch import load_file
        from transformers import AutoProcessor, Florence2Config, Florence2ForConditionalGeneration

        self.torch = torch
        self.device = device
        self.dtype = torch.float16 if device in ("mps", "cuda") else torch.float32
        self.processor = AutoProcessor.from_pretrained(BASE)
        self.processor.num_image_tokens = (CROP // 32) ** 2 + 1  # vision tower downsamples 32x, plus one pooled token
        state = convert(load_file(omniparser_file("icon_caption/model.safetensors")))
        config = Florence2Config.from_pretrained(BASE)
        shared = state["model.language_model.shared.weight"]
        trained, total = shared.shape[0], config.text_config.vocab_size
        # The built-in processor adds image placeholder tokens past the original vocabulary.
        state["model.language_model.shared.weight"] = torch.cat([shared, shared.new_zeros(total - trained, shared.shape[1])])
        state.pop("lm_head.weight", None)
        self.suppress = list(range(trained, total))
        model = Florence2ForConditionalGeneration(config)
        missing, unexpected = model.load_state_dict(state, strict=False)
        tied = ("lm_head.weight", "embed_tokens.weight")
        real_missing = [k for k in missing if not k.endswith(tied)]
        if real_missing or unexpected:
            raise RuntimeError(f"icon caption weights did not match: missing={real_missing[:3]} unexpected={unexpected[:3]}")
        model.tie_weights()
        self.model = model.to(device, self.dtype).eval()

    def caption(self, crops: list) -> list[str]:
        """Short names for icon crops (PIL images), in one batch."""
        if not crops:
            return []
        torch = self.torch
        captions: list[str] = []
        for start in range(0, len(crops), BATCH):
            batch = [c.convert("RGB").resize((CROP, CROP)) for c in crops[start : start + BATCH]]
            # Without do_resize=False the processor upscales every crop to 768x768, which needs tens of GB.
            inputs = self.processor(text=[PROMPT] * len(batch), images=batch, do_resize=False, return_tensors="pt")
            inputs = {k: (v.to(self.device, self.dtype) if v.is_floating_point() else v.to(self.device)) for k, v in inputs.items()}
            with torch.inference_mode():
                ids = self.model.generate(**inputs, max_new_tokens=12, num_beams=1, do_sample=False, suppress_tokens=self.suppress)
            captions += [t.strip() for t in self.processor.batch_decode(ids, skip_special_tokens=True)]
        return captions
