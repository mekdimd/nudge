from __future__ import annotations

import argparse
import os
import traceback
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
    parser.add_argument("--stop", action="store_true", help="quit the running Nudge, including a foreground instance")
    parser.add_argument("--version", action="version", version=f"Nudge {get_version()}", help="show the installed version and exit")
    parser.add_argument("--doctor", action="store_true", help="check setup offline without starting the UI")
    args = parser.parse_args()
    if args.doctor:
        from .doctor import run_doctor

        raise SystemExit(run_doctor())

    from . import background

    if args.stop:
        try:
            pid = background.stop()
        except background.ProcessError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc
        print(f"Stopped Nudge (pid {pid})." if pid else "Nudge isn't running.")
        return

    from .startup import Startup

    startup = Startup(get_version())
    try:
        if args.background:
            startup.step("Checking for a running Nudge")
            if pid := background.running_pid():
                startup.close()
                print(f"Nudge is already running (pid {pid}). Run 'nudge --stop' to quit it.")
                return
            startup.step("Waiting for the background process to start")
            pid = background.detach(sys.argv[1:])
            startup.ready()
            print(f"Nudge is running in the background (pid {pid}).")
            print(f"Quit from the menu bar icon or with 'nudge --stop'. Logs: {background.log_path()}")
            return
        startup.step("Checking for a running Nudge")
        owner = background.acquire()
        if owner is None:
            startup.close()
            pid = background.running_pid()
            detail = f" (pid {pid})" if pid else " or still starting"
            print(f"Nudge is already running{detail}. Run 'nudge --stop' to quit it.")
            return
        try:
            startup.step("Loading Qt and Nudge modules")
            from .app import run

            run(args, owner, startup)
        except BaseException:
            startup.fail()
            traceback.print_exc()
            sys.stderr.flush()
            os._exit(1)  # An initialized worker must not outlive failed startup.
        finally:
            owner.close()
    except background.ProcessError as exc:
        startup.fail()
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        startup.close()


if __name__ == "__main__":
    main()
