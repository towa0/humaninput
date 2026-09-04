"""Shared text-buffer/cursor simulation for backends that need to know
what's actually on screen at each point in a `KeyEvent` stream.

Backends used to just assume every keydown appended to the end of the
buffer (or, for backspace, removed from the end). That stopped being true
once arrow-key correction was introduced: a correction can move the
cursor into the middle of already-typed text, delete/insert there, and
move back out. This module is the one place that turns "a stream of
keydowns" into "text plus a cursor position" so every backend agrees on
what the screen looks like.
"""

from __future__ import annotations

from dataclasses import dataclass

from humaninput.events import EventStream, KeyAction


@dataclass(frozen=True, slots=True)
class BufferState:
    t_ms: float
    text: str
    cursor: int


def replay_buffer(stream: EventStream) -> list[BufferState]:
    """Replay keydown events into (text, cursor) states, in order. Only
    states that actually changed something are included; the initial
    empty state at t=0 is always first.
    """
    states: list[BufferState] = [BufferState(0.0, "", 0)]
    text = ""
    cursor = 0
    for e in stream:
        if e.action != KeyAction.DOWN:
            continue
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
        states.append(BufferState(e.t_ms, text, cursor))
    return states


def rows_for(n_chars: int, width: int) -> int:
    """How many terminal rows `n_chars` of text occupies once it wraps at
    `width` columns. At least 1, even for an empty line.
    """
    return max(1, -(-n_chars // width)) if n_chars else 1


def cursor_pos(n_chars: int, width: int) -> tuple[int, int]:
    """(row, col) of the cursor right after `n_chars` have been written,
    starting from (0, 0), wrapping at `width` columns.

    Real terminals defer wrapping: writing into the last column of a row
    leaves the cursor sitting *on* that last column (not advanced to
    column 0 of the next row) until another character is actually
    written. Plain `divmod(n_chars, width)` gets this wrong exactly at
    row boundaries, which produces garbled redraws on wrapped lines.
    """
    if n_chars <= 0:
        return 0, 0
    row, col = divmod(n_chars - 1, width)
    return row, min(col + 1, width - 1)
