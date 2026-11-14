# Contributing to Nudge

Nudge is an early desktop accessibility project. Useful contributions include bug reports, feedback about difficult controls, Windows test results, and small changes with a clear purpose.

## Set up a development environment

Use macOS or Windows, Python 3.12 or 3.13, and [uv](https://docs.astral.sh/uv/).

~~~bash
git clone https://github.com/mekdimd/nudge.git
cd nudge
uv sync --frozen
uv run pytest -q
~~~

The automated tests use headless Qt and fake adapters. They do not require keys or control real apps. Rehearse both offline flows before changing the interface:

~~~bash
uv run nudge --offline live_caption
uv run nudge --offline gmail
~~~

## Report a bug

Use the [bug report form](https://github.com/mekdimd/nudge/issues/new/choose). Include your OS, Python version, app and goal, then describe the expected result and the step that failed. Remove API keys, email addresses, private messages and other personal data from logs and screenshots.

For a new feature, explain the task you want to complete and why the current controls make it difficult. Discuss changes to app switching, confirmation rules or data sent to providers in an issue before implementing them.

## Open a pull request

1. Create a branch for one change.
2. Reuse the existing fake adapters and fixtures. Add a regression test when you fix behavior that can fail again.
3. Run the tests and build the package:

   ~~~bash
   uv run pytest -q
   uv build
   ~~~

4. Explain what changed, why, and how you checked it. Separate automated results from live app observations. If you only tested one OS, say which one.

For a live test, use a throwaway account and a task you can safely cancel. Stay present for drafts and confirmations. Do not use real purchases, destructive tasks or customer data as test cases.

After changing dependencies, regenerate the plain-pip exports:

~~~bash
uv export --no-hashes --no-dev -o requirements.txt
uv export --no-hashes --no-dev --extra vision -o requirements-vision.txt
~~~

## Edit the launch film

The editable source, asset credits and verification commands are in [docs/launch](docs/launch/README.md). Review its snapshots and rendered frames after a visual change. Do not replace actual controls with invented UI or present offline fixture timings as a live benchmark.

## License

By contributing, you agree to license your changes under the project's [MIT license](LICENSE). Third-party assets need their own source and license record.
