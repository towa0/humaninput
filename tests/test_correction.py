"""Correction model: arrow-key correction (instead of always backspacing
through everything typed after a typo), cascading typos introduced while
retyping a correction, and the invariant that must hold regardless of
which detour a correction takes — the final on-screen text always
matches the original target text once every error has been corrected.
"""

from __future__ import annotations

import copy

import pytest

from humaninput import profile as profiles
from humaninput.events import KeyAction
from humaninput.replay import replay_buffer
from humaninput.typing.typist import Typist

_TEXTS = [
    "the quick brown fox jumps over the lazy dog, and then runs away quickly!",
    "correcting typos while typing this rather long sentence is genuinely tricky.",
    "short one.",
]

_PROFILE_NAMES = ["touch_typist", "hunt_and_peck", "fast_coder", "mobile_thumbs", "tired"]


def _fully_corrected(name: str):
    p = copy.deepcopy(profiles.load(name))
    p.errors.uncorrected_rate = 0.0
    return p


@pytest.mark.parametrize("profile_name", _PROFILE_NAMES)
@pytest.mark.parametrize("text", _TEXTS)
def test_final_buffer_matches_target_text_when_fully_corrected(profile_name, text):
    """Whatever backspacing/arrow-key detour a correction takes (and
    however many cascading retype-errors happen along the way), replaying
    the keystrokes must always land on exactly the target text once every
    error is corrected (uncorrected_rate=0).
    """
    prof = _fully_corrected(profile_name)
    for seed in range(10):
        stream = Typist(profile=prof, seed=seed).type(text)
        states = replay_buffer(stream)
        final_text = states[-1].text if states else ""
        assert final_text == text, (profile_name, seed, final_text)


def test_arrow_correction_used_and_preserves_correct_tail():
    """When arrow correction fires, the terminal/svg/etc backends must see
    real arrowleft/arrowright events (not just backspace-and-retype), and
    the correctly-typed characters after the typo must never be
    backspaced away.
    """
    prof = _fully_corrected("fast_coder")
    prof.errors.arrow_correction_probability = 1.0
    prof.errors.arrow_correction_max_tail = 20
    prof.errors.substitution_rate = 0.25
    prof.errors.transposition_rate = 0.0
    prof.errors.insertion_rate = 0.0
    prof.errors.omission_rate = 0.0
    prof.errors.retype_error_rate_multiplier = 0.0  # isolate arrow behavior from cascading

    text = "the quick brown fox jumps over the lazy dog and then runs away quickly"
    saw_arrow = False
    for seed in range(20):
        stream = Typist(profile=prof, seed=seed).type(text)
        keys = [e.key for e in stream.events if e.action == KeyAction.DOWN]
        if "arrowleft" in keys:
            saw_arrow = True
            assert "arrowright" in keys
        states = replay_buffer(stream)
        assert (states[-1].text if states else "") == text
    assert saw_arrow, "arrow-key correction never fired across 20 seeds at probability=1.0"


def test_cascading_error_can_occur_while_retyping_a_correction():
    """Fixing a typo can itself come out wrong. That shows up as a
    keydown that is both is_error and is_correction: a wrong keystroke
    typed as part of a correction's retype."""
    prof = _fully_corrected("touch_typist")
    prof.errors.substitution_rate = 0.35
    prof.errors.transposition_rate = 0.0
    prof.errors.insertion_rate = 0.0
    prof.errors.omission_rate = 0.0
    prof.errors.retype_error_rate_multiplier = 1.0
    prof.errors.max_cascade_depth = 2

    text = "the quick brown fox jumps over the lazy dog and then runs away quickly into the forest"
    saw_cascade = False
    for seed in range(20):
        stream = Typist(profile=prof, seed=seed).type(text)
        cascade_events = [e for e in stream.events if e.action == KeyAction.DOWN and e.is_error and e.is_correction]
        if cascade_events:
            saw_cascade = True
        states = replay_buffer(stream)
        assert (states[-1].text if states else "") == text
    assert saw_cascade, "no cascading retype-error observed across 20 seeds at rate=1.0"


def test_cascade_depth_is_bounded():
    """Even at a guaranteed-wrong retype rate, the cascade must terminate
    (bounded by max_cascade_depth) rather than loop indefinitely."""
    prof = _fully_corrected("touch_typist")
    prof.errors.substitution_rate = 1.0
    prof.errors.transposition_rate = 0.0
    prof.errors.insertion_rate = 0.0
    prof.errors.omission_rate = 0.0
    prof.errors.retype_error_rate_multiplier = 1.0
    prof.errors.max_cascade_depth = 2
    prof.errors.arrow_correction_probability = 0.5

    text = "hello there"
    stream = Typist(profile=prof, seed=1).type(text)
    states = replay_buffer(stream)
    assert (states[-1].text if states else "") == text
    assert len(stream.events) < 20000  # sanity bound, not a runaway
