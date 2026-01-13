from __future__ import annotations

import sys

import psutil
from event_loop import application_event_loop


program_name = "CustomRPC.exe"

# Check to see if the program is already running to avoid duplicates:
# Allows program to run as singleton object
def check_for_running() -> bool:
    count = 0
    for p in psutil.process_iter():
        if p.name() == program_name:
            count += 1

    # Opens two threads so we count for this much
    return count > 2


if __name__ == "__main__":
    # Assert singleton pattern
    if check_for_running():
        sys.exit()

    # At this point, we have ensured that no instance is running.
    application_event_loop()
