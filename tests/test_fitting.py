"""Round-trip test: generate with a known profile, fit a profile back out
of the generated event stream, and check the recovered parameters are
close to the originals. This is what makes the model calibratable rather
than just hand-tuned.
"""

from __future__ import annotations

from humaninput import profile as profiles
from humaninput.fitting import fit
from humaninput.typing.typist import Typist

_CORPUS = (
    "the quick brown fox jumps over the lazy dog and then runs away quickly into the forest "
    "before anyone notices what happened next in this rather long sentence about ordinary "
    "common words that a frequency list would recognize easily and the story continues on "
    "for quite a while so that the fitted profile has enough samples per digraph class "
) * 8


def _rel_close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-6)


def test_round_trip_fit_recovers_touch_typist_parameters():
    original = profiles.load("touch_typist")
    stream = Typist(profile=original, seed=11).type(_CORPUS, errors=False)
    rows = [(e.t_ms, e.key, e.action.value) for e in stream.events]

    fitted = fit(rows, name="fitted_touch_typist")

    assert _rel_close(fitted.wpm_target, original.wpm_target, tol=0.30), (fitted.wpm_target, original.wpm_target)
    assert _rel_close(fitted.interval.mu_ms, original.interval.mu_ms, tol=0.30)
    assert _rel_close(fitted.interval.sigma, original.interval.sigma, tol=0.40)

    for field in ("same_key", "alternating_hand", "same_finger_different_key", "to_digit"):
        got = getattr(fitted.digraph_multipliers, field)
        want = getattr(original.digraph_multipliers, field)
        assert _rel_close(got, want, tol=0.35), (field, got, want)

    assert _rel_close(fitted.hold.mu_ms, original.hold.mu_ms, tol=0.35)


def test_round_trip_fit_distinguishes_hunt_and_peck_from_fast_coder():
    """A weaker but important sanity check: fitting shouldn't just
    regress to some fixed default regardless of input — two very
    different typists should fit to very different speeds.
    """
    slow = profiles.load("hunt_and_peck")
    fast = profiles.load("fast_coder")

    slow_stream = Typist(profile=slow, seed=3).type(_CORPUS, errors=False)
    fast_stream = Typist(profile=fast, seed=3).type(_CORPUS, errors=False)

    fitted_slow = fit([(e.t_ms, e.key, e.action.value) for e in slow_stream.events], name="fitted_slow")
    fitted_fast = fit([(e.t_ms, e.key, e.action.value) for e in fast_stream.events], name="fitted_fast")

    assert fitted_slow.wpm_target < fitted_fast.wpm_target
    assert fitted_slow.interval.mu_ms > fitted_fast.interval.mu_ms
