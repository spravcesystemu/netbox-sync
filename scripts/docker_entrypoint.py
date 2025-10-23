#!/usr/bin/env python3
"""Docker entrypoint wrapper to run netbox-sync periodically."""
import os
import shlex
import signal
import subprocess
import sys
import time
from typing import List


def _parse_interval(value: str) -> int:
    try:
        interval = int(value)
    except (TypeError, ValueError):
        return 0
    return interval if interval > 0 else 0


def _run_sync(args: List[str]) -> int:
    cmd = ["python3", "netbox-sync.py", *args]
    return subprocess.call(cmd)


def _normalize_args(raw_args: List[str]) -> List[str]:
    """Return args forwarded to netbox-sync, unwrapping shell wrappers."""

    if not raw_args:
        return []

    first = raw_args[0]
    if first in {"sh", "/bin/sh"}:
        # Compose v1 converts list/str commands into `sh -c ...`. Attempt to
        # recover the original command line so the sync CLI sees the expected
        # arguments instead of ``sh``/``-c`` tokens.
        if len(raw_args) >= 2 and raw_args[1] == "-c":
            command_str = " ".join(raw_args[2:])
            if not command_str:
                return []
            return shlex.split(command_str)
        return raw_args[1:]

    return raw_args


def main() -> int:
    args = _normalize_args(sys.argv[1:])
    interval = _parse_interval(os.environ.get("NBS_RUN_INTERVAL"))

    # Allow graceful termination when running in a loop.
    stop_requested = False

    def _handle_signal(signum, frame):  # noqa: ANN001, ANN202 - signature fixed by signal module
        nonlocal stop_requested
        stop_requested = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_signal)

    iteration = 0
    exit_code = 0

    while True:
        iteration += 1
        print(f"[docker-entrypoint] Starting sync run #{iteration} with args: {' '.join(args) if args else '(none)'}")
        exit_code = _run_sync(args)
        print(f"[docker-entrypoint] Sync run #{iteration} finished with exit code {exit_code}")

        if interval == 0 or stop_requested:
            break

        sleep_until = time.time() + interval
        while time.time() < sleep_until:
            remaining = sleep_until - time.time()
            if remaining <= 0:
                break
            if stop_requested:
                break
            time.sleep(min(remaining, 1))

        if stop_requested:
            break

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
