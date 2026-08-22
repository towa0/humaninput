"""Statistical validation of the typing model: does the generated output
actually match the distribution the profile asked for, not just "does it
run without crashing".
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from humaninput.events import KeyAction
from humaninput.layout import load_layout
from humaninput.typing.typist import Typist


def _keydown_intervals(events) -> list[float]:
    downs = [e.t_ms for e in events if e.action == KeyAction.DOWN]
    return [b - a for a, b in zip(downs, downs[1:])]


def test_intervals_match_configured_lognormal(isolated_profile):
    """KS test: generated same-key inter-key intervals should be
    consistent with the configured log-normal (median = mu_ms *
    same_key multiplier, given sigma).
    """
    text = "l" * 4000
    events = Typist(profile=isolated_profile, seed=123).type(text, errors=False).events
    intervals = _keydown_intervals(events)
    assert len(intervals) > 3000

    median = isolated_profile.interval.mu_ms * isolated_profile.digraph_multipliers.same_key
    sigma = isolated_profile.interval.sigma

    stat, pvalue = stats.kstest(intervals, "lognorm", args=(sigma, 0, median))
    assert pvalue > 0.01, f"KS test rejected log-normal fit (stat={stat:.4f}, p={pvalue:.4f})"


def test_digraph_class_ordering(isolated_profile):
    """same_key < alternating_hand < same_hand_diff_finger <
    same_finger_diff_key, as measured from actually generated intervals
    (not just read back from the profile config).
    """
    layout = load_layout(isolated_profile.layout)

    from humaninput.layout import DigraphClass

    pairs = {
        "same_key": ("l", "l", DigraphClass.SAME_KEY),
        "alternating_hand": ("t", "h", DigraphClass.ALTERNATING_HAND),
        "same_hand_diff_finger": ("e", "r", DigraphClass.SAME_HAND_DIFFERENT_FINGER),
        "same_finger_diff_key": ("e", "d", DigraphClass.SAME_FINGER_DIFFERENT_KEY),
    }
    for label, (a, b, expected_cls) in pairs.items():
        assert layout.classify_digraph(a, b) == expected_cls, label

    means = {}
    for label, (a, b, _) in pairs.items():
        pair = a + b
        text = pair * 2000
        events = Typist(profile=isolated_profile, seed=99).type(text, errors=False).events
        means[label] = float(np.mean(_keydown_intervals(events)))

    assert means["same_key"] < means["alternating_hand"] < means["same_hand_diff_finger"] < means["same_finger_diff_key"], means


@pytest.mark.parametrize(
    "profile_name",
    ["touch_typist", "hunt_and_peck", "fast_coder", "mobile_thumbs", "tired"],
)
def test_measured_wpm_within_tolerance(profile_name):
    from humaninput import profile as profiles

    prof = profiles.load(profile_name)
    text = (
        "the quick brown fox jumps over the lazy dog and then runs away quickly into the "
        "forest before anyone notices what happened next in this rather long sentence about "
        "ordinary common words that a frequency list would recognize easily "
    ) * 4

    events = Typist(profile=prof, seed=7).type(text, errors=False)
    measured_wpm = (len(text) / 5) / (events.duration_ms / 1000 / 60)

    tolerance = 0.30
    lo, hi = prof.wpm_target * (1 - tolerance), prof.wpm_target * (1 + tolerance)
    assert lo <= measured_wpm <= hi, f"{profile_name}: measured={measured_wpm:.1f} target={prof.wpm_target} (tolerance ±{tolerance:.0%})"


def test_seeded_reproducibility(touch_typist):
    text = "the quick brown fox jumps over the lazy dog, and then runs away!"
    a = Typist(profile=touch_typist, seed=42).type(text)
    b = Typist(profile=touch_typist, seed=42).type(text)
    assert a.events == b.events

    c = Typist(profile=touch_typist, seed=43).type(text)
    assert a.events != c.events


def test_type_errors_false_matches_target_text_exactly(touch_typist):
    text = "reproducible output, no typos here."
    events = Typist(profile=touch_typist, seed=1).type(text, errors=False).events
    downs = [e.key for e in events if e.action == KeyAction.DOWN]
    assert "".join(downs) == text
    assert all(not e.is_error and not e.is_correction for e in events)
