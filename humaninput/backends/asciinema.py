"""Write an asciicast v2 (.cast) file from a KeyEvent stream, so a
terminal recording can be produced without recording anything.

Format: https://docs.asciinema.org/manual/asciicast/v2/
"""

from __future__ import annotations

import json as _json
from typing import TextIO

from humaninput.events import EventStream, KeyAction


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

    for e in stream:
        if e.action != KeyAction.DOWN:
            continue
        t_s = e.t_ms / 1000.0
        text = "\b \b" if e.key == "backspace" else e.key
        lines.append(_json.dumps([round(t_s, 6), "o", text]))

    content = "\n".join(lines) + "\n"
    if hasattr(path_or_file, "write"):
        path_or_file.write(content)
        return
    with open(path_or_file, "w", encoding="utf-8") as f:
        f.write(content)
