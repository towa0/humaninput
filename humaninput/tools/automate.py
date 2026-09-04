"""Chain mouse movement, a click, and typing into one realistic action:
move to a target, click it, pause briefly the way a person actually does
before typing (not instantaneous), then type. Drives the real OS
keyboard/mouse via pynput — see the warning printed by that backend.

This lives outside the core model (which performs no I/O by design, see
`humaninput/__init__.py`) alongside `shadow_writer.py` — both are actual
automation, not the timing engine itself.
"""

from __future__ import annotations

import time

import numpy as np

from humaninput.mouse.pointer import Pointer
from humaninput.profile import Profile
from humaninput.typing.typist import Typist


def click_and_type(
    profile: Profile,
    to_xy: tuple[float, float],
    text: str,
    from_xy: tuple[float, float] | None = None,
    seed: int | None = None,
    button: str = "left",
    target_width: float = 40.0,
    pre_type_pause_ms: tuple[float, float] = (150.0, 500.0),
    errors: bool = True,
    layout: str | None = None,
) -> None:
    """Move the real mouse to `to_xy`, click it, pause briefly (like
    someone re-orienting after a click before they start typing), then
    type `text` into whatever that click focused. Blocks for the
    duration of the whole sequence.

    `from_xy` defaults to the mouse's actual current position. `seed`
    makes the mouse path and typing reproducible, but not the pause
    (drawn from a fresh generator each call) or the click's own arrival
    time relative to real wall-clock delays elsewhere in your script —
    only use `seed` to compare/replay a single call's shape, not to
    reproduce an entire automation session byte-for-byte.
    """
    from humaninput.backends import pynput as pynput_backend

    if from_xy is None:
        from pynput.mouse import Controller as MouseController

        from_xy = tuple(MouseController().position)

    pointer = Pointer(profile, seed=seed)
    pynput_backend.play_mouse(pointer.move(from_xy, to_xy, target_width=target_width))
    pynput_backend.play_mouse(pointer.click(*to_xy, button=button))

    rng = np.random.default_rng(seed)
    time.sleep(float(rng.uniform(*pre_type_pause_ms)) / 1000.0)

    typist = Typist(profile, seed=seed, layout=layout)
    pynput_backend.play_keys(typist.type(text, errors=errors))
