# CI and release packages

Nudge needs automatic checks before merging and repeatable release packages.
The user chose GitHub Releases with Python packages.

## Approach

Use GitHub Actions to run the offline suite on macOS Apple Silicon and Windows x64 with Python
3.12 and 3.13. Build a wheel and source distribution, then install each in a
fresh environment and check the CLI, icons, configuration, and rehearsal data.
Publish those same artifacts only after the checks pass for a version tag.
Standalone installers require signing and a separate packaging design. PyPI
publishing requires a package name and publisher setup. Neither is needed here.

## Requirements

- Keep this PR independent of the open launch-video PR and target `main`.
- Use the existing uv lockfile. Tests need no API keys or desktop permissions.
- Release tags use `vX.Y.Z` and match the version in `pyproject.toml`.
- Only commits reachable from `main` can publish a release.
- Release packages include rehearsal data and SVGs, and exclude keys and media.
- Installed Nudge reads `.env` from the working directory. Environment variables
  take priority, and source checkouts retain their project `.env` fallback.
- Pin Actions to commit SHAs and give only the publishing job write access.
- Add release instructions and automated updates for GitHub Actions.

## Limits

Headless tests cover the fake adapter and UI. They do not validate native
accessibility permissions, live providers, or the optional vision models.
No release is published and no repository protection rules change in this task.
