"""Dump the raw event stream as JSON, for piping into anything else."""

from __future__ import annotations

import json as _json
from typing import TextIO

from humaninput.events import EventStream


def to_json(stream: EventStream, indent: int | None = 2) -> str:
    payload = {
        "seed": stream.seed,
        "profile": stream.profile_name,
        "duration_ms": stream.duration_ms,
        "events": stream.to_dicts(),
    }
    return _json.dumps(payload, indent=indent)


def write(stream: EventStream, path_or_file: str | TextIO, indent: int | None = 2) -> None:
    text = to_json(stream, indent=indent)
    if hasattr(path_or_file, "write"):
        path_or_file.write(text)
        return
    with open(path_or_file, "w", encoding="utf-8") as f:
        f.write(text)
