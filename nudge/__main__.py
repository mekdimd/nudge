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
    parser.add_argument("--persistent", action="store_true", help="✕ hides the bar instead of quitting; the hotkey or the menu bar icon brings it back")
    parser.add_argument("--background", action="store_true", help="like --persistent, but detached from this terminal (logs go to a file)")
    parser.add_argument("--stop", action="store_true", help="quit a Nudge running with --persistent or --background")
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
