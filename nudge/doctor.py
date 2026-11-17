from __future__ import annotations

import os
import platform
import sys
import textwrap
from importlib.util import find_spec

from . import get_version
from .config import load_environment


def _check(level: str, name: str, status: str, detail: str = '') -> None:
    tag = f'[{level:4}]'
    if sys.stdout.isatty() and 'NO_COLOR' not in os.environ:
        color = {'OK': '32', 'WARN': '33', 'FAIL': '31'}[level]
        tag = f'\033[{color}m{tag}\033[0m'
    print(f'  {tag} {name}: {status}')
    if detail:
        print(textwrap.fill(detail, width=78, initial_indent='         ', subsequent_indent='         '))


def run_doctor() -> int:
    print('Nudge doctor\n')
    print('Runtime')
    print(f'  Nudge {get_version()}')
    print(f'  Python {platform.python_version()}')
    print(f'  OS {platform.system()} {platform.release()}')
    failed = False
    if not (3, 12) <= sys.version_info[:2] < (3, 14):
        _check('FAIL', 'Python', 'unsupported', 'Install Python 3.12 or 3.13 and run uv sync --frozen.')
        failed = True

    print('\nAPI keys')
    load_environment()
    for key, purpose, required in (
        ('TYPESAFE_API_KEY', 'real tasks', True),
        ('GEMINI_API_KEY', 'drafting', False),
        ('ELEVENLABS_API_KEY', 'optional voice', False),
    ):
        if os.environ.get(key, '').strip():
            _check('OK', key, 'set')
        else:
            level = 'FAIL' if required else 'WARN'
            _check(level, key, 'missing', f'Add {key} to .env or your environment to enable {purpose}.')
            failed |= required

    print('\nPermissions')
    if sys.platform == 'darwin':
        try:
            from ApplicationServices import AXIsProcessTrusted

            trusted = AXIsProcessTrusted()
        except Exception:
            _check('FAIL', 'Accessibility', 'unable to check', 'Run uv sync --frozen to repair the macOS dependencies, then retry.')
            failed = True
        else:
            if trusted:
                _check('OK', 'Accessibility', 'granted')
            else:
                _check('FAIL', 'Accessibility', 'missing', 'Allow the launching terminal or editor in System Settings > Privacy & Security > Accessibility, then restart Nudge.')
                failed = True
        try:
            from Quartz import CGPreflightScreenCaptureAccess

            capture = CGPreflightScreenCaptureAccess()
        except Exception:
            _check('WARN', 'Screen Recording', 'unable to check', 'Run uv sync --frozen and check System Settings > Privacy & Security > Screen Recording for optional vision.')
        else:
            if capture:
                _check('OK', 'Screen Recording', 'granted for optional vision')
            else:
                _check('WARN', 'Screen Recording', 'missing for optional vision', 'Allow the launching terminal or editor in System Settings > Privacy & Security > Screen Recording, then restart Nudge.')
    elif sys.platform == 'win32':
        _check('OK', 'Accessibility', 'no global permission toggle on Windows', 'Run Nudge and the target app without administrator privileges.')
    else:
        _check('FAIL', 'Accessibility', 'unsupported OS', 'Use macOS or Windows.')
        failed = True

    print('\nLocal vision')
    modules = ['ultralytics', 'torch', 'transformers', 'timm', 'einops', 'huggingface_hub', 'mss']
    if sys.platform in {'darwin', 'win32'}:
        modules.append('Vision' if sys.platform == 'darwin' else 'rapidocr_onnxruntime')
    missing = [name for name in modules if find_spec(name) is None]
    if missing:
        _check('WARN', 'Vision', 'missing dependencies', f"Missing: {', '.join(missing)}. Install with uv sync --frozen --extra vision or pip install 'nudge[vision]'.")
    else:
        _check('OK', 'Vision', 'dependencies installed', 'Model weights and runtime readiness are not checked offline.')

    print('\nResult: required setup needs attention.' if failed else '\nResult: required setup is ready.')
    print('Offline checks only. API key validity and vision model readiness were not checked.')
    return int(failed)
