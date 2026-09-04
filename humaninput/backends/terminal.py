"""Replay a KeyEvent stream into a terminal with real timing. Zero
dependencies — this is the default backend and the fastest way to sanity
check that a profile "feels" right.
"""

from __future__ import annotations

import shutil
import sys
import time
from typing import TextIO

from humaninput.events import EventStream, KeyAction
from humaninput.replay import cursor_pos


def play(stream: EventStream, speed: float = 1.0, out: TextIO | None = None, width: int | None = None) -> None:
    """Write keydown characters to `out` (default stdout) at the timestamps
    in the event stream, scaled by `1/speed`. Keyup events are not
    rendered. Each change (typed char, backspace, or arrow-key cursor
    move — arrow-key correction can edit mid-line, not just at the end)
    redraws the buffer via ANSI so the cursor always ends up in the right
    place. This is row-aware (not just "clear the current line"): once
    the buffer is longer than the terminal is wide, it wraps onto
    multiple rows, and a naive `\\r` + clear-line + cursor-left redraw
    only fixes up the last row, leaving stale wrapped rows above it.

    `width` defaults to the real terminal width (`shutil.get_terminal_size`,
    falling back to 80 columns when `out` isn't a real TTY); pass it
    explicitly to match the width of wherever `out` is actually going to
    be viewed if that differs.
    """
    out = out if out is not None else sys.stdout
    width = max(width if width is not None else shutil.get_terminal_size(fallback=(80, 24)).columns, 1)
    t0 = time.perf_counter()
    text = ""
    cursor = 0
    prev_cursor_row = 0  # row the cursor was actually left at last redraw, not the text's row count — arrow-key correction can leave it mid-buffer, not at the bottom row
    for e in stream:
        if e.action != KeyAction.DOWN:
            continue
        target_s = (e.t_ms / 1000.0) / speed
        elapsed = time.perf_counter() - t0
        if target_s > elapsed:
            time.sleep(target_s - elapsed)
        if e.key == "backspace":
            if cursor <= 0:
                continue
            text = text[: cursor - 1] + text[cursor:]
            cursor -= 1
        elif e.key == "arrowleft":
            if cursor <= 0:
                continue
            cursor -= 1
        elif e.key == "arrowright":
            if cursor >= len(text):
                continue
            cursor += 1
        elif len(e.key) == 1:
            text = text[:cursor] + e.key + text[cursor:]
            cursor += 1
        else:
            continue

        if prev_cursor_row > 0:
            out.write(f"\x1b[{prev_cursor_row}A")
        out.write("\r\x1b[J" + text)

        end_row, end_col = cursor_pos(len(text), width)
        cursor_row, cursor_col = cursor_pos(cursor, width)
        if end_row > cursor_row:
            out.write(f"\x1b[{end_row - cursor_row}A")
        out.write("\r")
        if cursor_col:
            out.write(f"\x1b[{cursor_col}C")

        prev_cursor_row = cursor_row
        out.flush()
    out.write("\n")
    out.flush()
