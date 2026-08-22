"""Replay a KeyEvent stream into a terminal with real timing. Zero
dependencies — this is the default backend and the fastest way to sanity
check that a profile "feels" right.
"""

from __future__ import annotations

import sys
import time
from typing import TextIO

from humaninput.events import EventStream, KeyAction


def play(stream: EventStream, speed: float = 1.0, out: TextIO | None = None) -> None:
    """Write keydown characters to `out` (default stdout) at the timestamps
    in the event stream, scaled by `1/speed`. Keyup events are not
    rendered; backspace erases the previous character in place.
    """
    out = out if out is not None else sys.stdout
    t0 = time.perf_counter()
    for e in stream:
        if e.action != KeyAction.DOWN:
            continue
        target_s = (e.t_ms / 1000.0) / speed
        elapsed = time.perf_counter() - t0
        if target_s > elapsed:
            time.sleep(target_s - elapsed)
        if e.key == "backspace":
            out.write("\b \b")
        else:
            out.write(e.key)
        out.flush()
    out.write("\n")
    out.flush()
