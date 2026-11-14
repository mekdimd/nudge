# Checks and releases

CI runs on pull requests and pushes to `main`. It tests macOS on Apple Silicon and Windows x64 with
Python 3.12 and 3.13, using `uv.lock` and headless Qt. Each job builds a wheel
and source distribution, installs both into fresh environments, and checks
the CLI, SVG icons, `.env` loading, and offline rehearsal fixtures.

The `CI passed` check requires every matrix job to succeed. A maintainer can
make it a required check in the repository's branch protection settings after
the first run. The workflow itself does not enforce merge protection.

## Make a release

1. Update `project.version` in `pyproject.toml`. Run `uv lock` and regenerate
   `requirements.txt` and `requirements-vision.txt` with the commands in their
   headers. Commit the changes through a PR and merge it into `main`.
2. Pull `main` and confirm the intended version with
   `uv run --no-project python scripts/check_release.py v0.1.0`. Replace the
   example tag with the version you are releasing.
3. Push the matching tag from the merged commit:

   ```bash
   git switch main
   git pull --ff-only
   git tag -a v0.1.0 -m 'Release 0.1.0'
   git push origin v0.1.0
   ```

A tag push publishes a public GitHub Release after the complete CI matrix
passes. Tags must use `vX.Y.Z`, match the package version, and point to a commit
reachable from `main`. Prerelease suffixes do not pass validation.

The release contains the checked wheel, source distribution, a
`constraints.txt` file exported from `uv.lock`, and `SHA256SUMS`. The publishing
job downloads those artifacts, verifies their hashes, and attaches them to
a release with generated notes. It does not rebuild them or publish to PyPI.

If checks fail, fix the code through a PR. Use a new version for any release
that has already been published. Review the generated release notes on GitHub.

## Install a release package

Download the wheel and `constraints.txt` from the same GitHub Release. With
Python 3.12 or 3.13 on an Apple Silicon Mac or Windows x64:

```bash
python -m venv .venv
# macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -c constraints.txt nudge-0.1.0-py3-none-any.whl
nudge --help
nudge --offline live_caption
```

Replace the example wheel filename with the one you downloaded. Run Nudge from
a folder containing your `.env`, or set its API keys as environment variables.
Environment variables take priority. Relative custom wake-word model paths
resolve from the `.env` folder, or the working directory when no file exists.
Source checkouts also fall back to the project's `.env` when launched elsewhere.

These packages require Python and the platform permissions documented in the
README. CI exercises fake desktop adapters. Native accessibility, live API
providers, and optional vision models still need manual checks before release.

## Run the same checks locally

```bash
uv sync --locked
QT_QPA_PLATFORM=offscreen uv run --no-sync pytest -q
uv build
uv export --locked --no-hashes --no-dev --no-emit-project -o dist/constraints.txt
uv venv --clear .package-check
uv pip install --python .package-check -c dist/constraints.txt dist/nudge-0.1.0-py3-none-any.whl
uv run --no-project --python .package-check python scripts/check_install.py
```

Repeat the last three commands with the source distribution in place of the
wheel. In PowerShell, set `$env:QT_QPA_PLATFORM = 'offscreen'` before running
pytest. Replace the example package version with the current one.

GitHub Actions use commit SHA pins. Dependabot opens weekly update PRs for
those pins; the same CI checks run on those PRs.
