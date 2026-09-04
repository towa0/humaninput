"""Pace wander (speed should drift up and down over a stretch of typing,
not hold a single flat average) and the comma cognitive pause.
"""

from __future__ import annotations

import copy

import numpy as np

from humaninput import profile as profiles
from humaninput.events import KeyAction
from humaninput.typing.model import CharAnnotation, _cognitive_pause, _step_pace, annotate_text
from humaninput.typing.typist import Typist

_LONG_TEXT = (
    "the quick brown fox jumps over the lazy dog and then runs away quickly into the "
    "forest before anyone notices what happened next in this rather long sentence about "
    "ordinary common words that a frequency list would recognize easily "
) * 6


def _windowed_wpm(events, window: int = 40) -> list[float]:
    downs = [e.t_ms for e in events if e.action == KeyAction.DOWN]
    intervals = np.diff(downs)
    out = []
    for i in range(0, len(intervals) - window, window):
        ms_per_char = intervals[i : i + window].mean()
        out.append((1000.0 / ms_per_char) * 60.0 / 5.0)
    return out


def test_pace_wander_produces_speed_variation_over_time():
    """With pace enabled, windowed WPM across a long passage should vary
    noticeably more than with it disabled — a smooth ups-and-downs drift,
    not a flat average speed for the whole passage.
    """
    enabled = profiles.load("touch_typist")
    disabled = copy.deepcopy(enabled)
    disabled.pace.enabled = False

    enabled_stds = []
    disabled_stds = []
    for seed in range(5):
        enabled_stream = Typist(profile=enabled, seed=seed).type(_LONG_TEXT, errors=False)
        disabled_stream = Typist(profile=disabled, seed=seed).type(_LONG_TEXT, errors=False)
        enabled_stds.append(np.std(_windowed_wpm(enabled_stream.events)))
        disabled_stds.append(np.std(_windowed_wpm(disabled_stream.events)))

    assert np.mean(enabled_stds) > np.mean(disabled_stds) * 1.3, (enabled_stds, disabled_stds)


def test_pace_multiplier_stays_within_configured_bounds():
    """The wander itself (isolated from the interval's own log-normal
    noise) must stay clamped to [min_multiplier, max_multiplier], not run
    away to absurd speeds over a long passage."""
    cfg = profiles.load("mobile_thumbs").pace  # widest configured band
    rng = np.random.default_rng(1)
    state = 0.0
    multipliers = []
    for _ in range(20000):
        state, mult = _step_pace(state, cfg, rng)
        multipliers.append(mult)
    assert min(multipliers) >= cfg.min_multiplier
    assert max(multipliers) <= cfg.max_multiplier
    assert max(multipliers) > min(multipliers) * 1.2  # it actually wanders, not stuck at one value


def test_after_comma_annotation_fires_on_char_following_comma():
    anns = annotate_text("hello, world")
    assert anns[7].after_comma is True  # 'w' of "world"
    assert not any(a.after_comma for i, a in enumerate(anns) if i != 7)


def test_comma_pause_fires_only_for_after_comma_annotation():
    """Deterministic check of the comma-pause contribution in isolation
    (a full-pipeline timing diff is noisy: turning the comma pause on
    changes how many random draws happen, which desyncs everything typed
    afterward even at a fixed seed)."""
    prof = profiles.load("touch_typist")
    prof.cognitive_pauses.comma_probability = 1.0
    prof.cognitive_pauses.comma_pause_ms_min = 200.0
    prof.cognitive_pauses.comma_pause_ms_max = 200.0
    # isolate the comma trigger from the other cognitive-pause triggers
    prof.cognitive_pauses.rare_word_probability = 0.0
    prof.cognitive_pauses.digit_probability = 0.0
    prof.cognitive_pauses.bracket_probability = 0.0
    prof.cognitive_pauses.sentence_start_probability = 0.0

    rng = np.random.default_rng(0)
    after_comma_ann = CharAnnotation(word_start=True, after_comma=True)
    plain_ann = CharAnnotation(word_start=True, after_comma=False)

    assert _cognitive_pause(rng, prof, after_comma_ann) == 200.0
    assert _cognitive_pause(rng, prof, plain_ann) == 0.0

    prof.cognitive_pauses.comma_probability = 0.0
    assert _cognitive_pause(rng, prof, after_comma_ann) == 0.0
