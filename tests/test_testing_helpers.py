from __future__ import annotations

import pytest

from humaninput import Typist, profiles
from humaninput.events import EventStream, KeyAction, KeyEvent
from humaninput.testing import describe, seeds


def test_seeds_are_params_with_seed_ids():
    params = seeds(3, start=10)
    assert [p.values for p in params] == [(10,), (11,), (12,)]
    assert [p.id for p in params] == ["seed=10", "seed=11", "seed=12"]


@pytest.mark.parametrize("seed", seeds(2))
def test_seeds_work_in_parametrize(seed, request):
    assert request.node.callspec.id == f"seed={seed}"


def _down_up(t, key, **kw):
    return [KeyEvent(t, KeyAction.DOWN, key, **kw), KeyEvent(t + 40, KeyAction.UP, key, **kw)]


def test_describe_counts_keystrokes_corrections_and_longest_pause():
    events = (
        _down_up(0, "a")
        + _down_up(100, "x", is_error=True)
        + _down_up(900, "backspace", is_correction=True)
        + _down_up(1000, "b", is_correction=True)
        + _down_up(1100, "c")
    )
    stream = EventStream(events=events, seed=7, profile_name="hunt_and_peck")

    assert describe(stream) == (
        "seed=7 hunt_and_peck: 1.14 s, 5 keystrokes, 1 correction, longest pause 800 ms"
    )


def test_describe_on_generated_stream_has_no_prefix_without_seed():
    stream = Typist(profile=profiles.load("touch_typist"), seed=None).type("hi", errors=False)
    stream.seed = None
    line = describe(stream)
    assert line.startswith("touch_typist: ")
    assert "2 keystrokes, 0 corrections" in line


def test_describe_empty_stream():
    assert describe(EventStream()) == "0.00 s, 0 keystrokes, 0 corrections, longest pause 0 ms"
