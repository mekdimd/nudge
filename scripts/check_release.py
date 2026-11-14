"""Reject release tags that do not match the package version."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path


def validate_tag(tag: str, version: str) -> None:
    if not re.fullmatch(r'v(0|[1-9][0-9]*)[.](0|[1-9][0-9]*)[.](0|[1-9][0-9]*)', tag):
        raise ValueError('Release tags must use vX.Y.Z with no leading zeroes.')
    if tag != f'v{version}':
        raise ValueError(f'Tag {tag} does not match package version {version}.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tag')
    args = parser.parse_args()
    project = tomllib.loads(Path('pyproject.toml').read_text())['project']
    try:
        validate_tag(args.tag, project['version'])
    except ValueError as error:
        parser.error(str(error))
    print(f'Release tag {args.tag} matches the package version.')


if __name__ == '__main__':
    main()
