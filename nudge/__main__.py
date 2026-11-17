from __future__ import annotations

import argparse
import sys

from . import get_version


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(prog="nudge", description="Type a goal; Nudge points to and presses each step.")
    parser.add_argument("--offline", choices=["live_caption", "gmail"], help="rehearse the UI on a scripted screen, no keys needed")
    parser.add_argument("--debug", action="store_true", help="start with Peek on: box every element Nudge can see")
    parser.add_argument("--no-vision", action="store_true", help="never use the screenshot fallback")
    parser.add_argument("--keep-running", action="store_true", help="closing the bar hides it; stay attached to the terminal with logs in the terminal")
    parser.add_argument("--background", "--detach", action="store_true", help="closing the bar hides it; detach from this terminal with logs in a file")
    parser.add_argument("--stop", action="store_true", help="quit a Nudge running with --keep-running, --background, or --detach")
    parser.add_argument("--version", action="version", version=f"Nudge {get_version()}", help="show the installed version and exit")
    parser.add_argument("--doctor", action="store_true", help="check setup offline without starting the UI")
    args = parser.parse_args()
    if args.doctor:
        from .doctor import run_doctor

        raise SystemExit(run_doctor())

    from .app import run

    run(args)


if __name__ == "__main__":
    main()
