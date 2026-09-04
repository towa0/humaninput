"""Write an asciicast v2 (.cast) file from a KeyEvent stream, so a
terminal recording can be produced without recording anything.

Format: https://docs.asciinema.org/manual/asciicast/v2/
"""

from __future__ import annotations

import json as _json
from typing import TextIO

from humaninput.events import EventStream, KeyAction
from humaninput.replay import cursor_pos


def write(
    stream: EventStream,
    path_or_file: str | TextIO,
    width: int = 80,
    height: int = 24,
    prompt: str = "",
) -> None:
    header = {"version": 2, "width": width, "height": height}
    lines = [_json.dumps(header)]

    if prompt:
        lines.append(_json.dumps([0.0, "o", prompt]))

    text = ""
    cursor = 0
    prev_cursor_row = 0  # row the cursor was actually left at, not the text's row count — arrow-key correction can leave it mid-buffer, not at the bottom row
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

        t_s = e.t_ms / 1000.0
        out_text = ""
        if prev_cursor_row > 0:
            out_text += f"\x1b[{prev_cursor_row}A"
        out_text += "\r\x1b[J" + text

        end_row, end_col = cursor_pos(len(text), width)
        cursor_row, cursor_col = cursor_pos(cursor, width)
        if end_row > cursor_row:
            out_text += f"\x1b[{end_row - cursor_row}A"
        out_text += "\r"
        if cursor_col:
            out_text += f"\x1b[{cursor_col}C"

        prev_cursor_row = cursor_row
        lines.append(_json.dumps([round(t_s, 6), "o", out_text]))

    content = "\n".join(lines) + "\n"
    if hasattr(path_or_file, "write"):
        path_or_file.write(content)
        return
    with open(path_or_file, "w", encoding="utf-8") as f:
        f.write(content)
