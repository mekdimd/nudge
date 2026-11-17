from __future__ import annotations

import os
import platform
import sys
from importlib.util import find_spec

from . import get_version
from .config import load_environment


def run_doctor() -> int:
    print(f"Nudge {get_version()}")
    print(f"Python {platform.python_version()}")
    print(f"OS {platform.system()} {platform.release()}")
    failed = False
    if not (3, 12) <= sys.version_info[:2] < (3, 14):
        print("FAIL Python: unsupported. Install Python 3.12 or 3.13 and run uv sync --frozen.")
        failed = True

    load_environment()
    for key, purpose, required in (
        ("TYPESAFE_API_KEY", "real tasks", True),
        ("GEMINI_API_KEY", "drafting", False),
        ("ELEVENLABS_API_KEY", "optional voice", False),
    ):
        if os.environ.get(key, "").strip():
            print(f"OK {key}: set.")
        else:
            level = "FAIL" if required else "WARN"
            print(f"{level} {key}: missing. Add {key} to .env or your environment to enable {purpose}.")
            failed |= required

    if sys.platform == "darwin":
        try:
            from ApplicationServices import AXIsProcessTrusted

            trusted = AXIsProcessTrusted()
        except Exception:
            print("FAIL Accessibility: unable to check. Run uv sync --frozen to repair the macOS dependencies, then retry.")
            failed = True
        else:
            if trusted:
                print("OK Accessibility: granted.")
            else:
                print("FAIL Accessibility: missing. Allow the launching terminal or editor in System Settings > Privacy & Security > Accessibility, then restart Nudge.")
                failed = True
        try:
            from Quartz import CGPreflightScreenCaptureAccess

            capture = CGPreflightScreenCaptureAccess()
        except Exception:
            print("WARN Screen Recording: unable to check. Run uv sync --frozen and check System Settings > Privacy & Security > Screen Recording for optional vision.")
        else:
            if capture:
                print("OK Screen Recording: granted for optional vision.")
            else:
                print("WARN Screen Recording: missing for optional vision. Allow the launching terminal or editor in System Settings > Privacy & Security > Screen Recording, then restart Nudge.")
    elif sys.platform == "win32":
        print("OK Accessibility: no global permission toggle on Windows. Run Nudge and the target app without administrator privileges.")
    else:
        print("FAIL Accessibility: unsupported OS. Use macOS or Windows.")
        failed = True

    modules = ["ultralytics", "torch", "transformers", "timm", "einops", "huggingface_hub", "mss"]
    if sys.platform in {"darwin", "win32"}:
        modules.append("Vision" if sys.platform == "darwin" else "rapidocr_onnxruntime")
    missing = [name for name in modules if find_spec(name) is None]
    if missing:
        print(f"WARN Vision: missing dependencies: {', '.join(missing)}. Install with uv sync --frozen --extra vision or pip install 'nudge[vision]'.")
    else:
        print("OK Vision: dependencies installed. Model weights and runtime readiness are not checked offline.")
    print("Doctor ran offline. API keys were checked for presence, not validity. Vision models were not loaded or downloaded.")
    return int(failed)
