"""Public entry point for the typing model.

`Typist` performs no I/O. `type()` returns an `EventStream` of `KeyEvent`s;
what happens with that stream is entirely up to a backend.
"""

from __future__ import annotations

import numpy as np

from humaninput.events import EventStream
from humaninput.layout import Layout, load_layout
from humaninput.profile import Profile
from humaninput.typing import errors as errors_mod
from humaninput.typing import model as model_mod


class Typist:
    def __init__(self, profile: Profile, seed: int | None = None, layout: Layout | str | None = None):
        self.profile = profile
        self.seed = seed
        if layout is None:
            self.layout = load_layout(profile.layout)
        elif isinstance(layout, str):
            self.layout = load_layout(layout)
        else:
            self.layout = layout

    def type(self, text: str, errors: bool = True) -> EventStream:
        rng = np.random.default_rng(self.seed)
        items = errors_mod.plan(text, self.profile, self.layout, rng, errors_enabled=errors)
        events = model_mod.generate_key_events(items, self.profile, self.layout, rng)
        return EventStream(events=events, seed=self.seed, profile_name=self.profile.name)
