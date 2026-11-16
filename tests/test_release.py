import importlib.util
from pathlib import Path

import pytest


def validate(tag, version='0.1.0'):
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'check_release.py'
    spec = importlib.util.spec_from_file_location('check_release', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_tag(tag, version)


def test_release_accepts_matching_stable_version():
    validate('v0.1.0')


@pytest.mark.parametrize('tag', ['v0.2.0', '0.1.0', 'v0.1.0rc1', 'v0.1.0/other', 'v00.1.0'])
def test_release_rejects_mismatched_or_invalid_tag(tag):
    with pytest.raises(ValueError):
        validate(tag)
