"""Interval generation and digraph classification.

This module turns a sequence of keys actually pressed (see `ExpandedItem`,
produced by `typing/errors.py` from the target text) into absolute
timestamps. It has no notion of "correct" vs "wrong" text — that
distinction was already resolved by the error model. It only knows: which
key, in what order, with which annotations (burst/pause hints).

Interval distribution: log-normal per digraph class. A log-normal is
right-skewed by construction (unlike a Gaussian), which matches the
observed shape of human inter-key interval distributions — most
keystrokes land close to the mode, with an occasional long tail. See
README for citations.
"""

from __future__ import annotations

import functools
import math
import pathlib
from dataclasses import dataclass

import numpy as np

from humaninput.events import KeyAction, KeyEvent
from humaninput.layout import DigraphClass, Layout
from humaninput.profile import Profile

_COMMON_WORDS_PATH = pathlib.Path(__file__).parent / "common_words.txt"

BACKSPACE = "\b"


@functools.lru_cache(maxsize=1)
def load_common_words() -> frozenset[str]:
    with open(_COMMON_WORDS_PATH, encoding="utf-8") as f:
        return frozenset(line.strip().lower() for line in f if line.strip())


@dataclass(frozen=True, slots=True)
class CharAnnotation:
    """Cognitive-pause hints attached to the character at a given index of
    the *target* text, evaluated before any error injection.
    """

    word_start: bool = False
    rare_word_start: bool = False
    digit_run_start: bool = False
    bracket_or_quote_open: bool = False
    sentence_start: bool = False


def annotate_text(text: str, common_words: frozenset[str] | None = None) -> list[CharAnnotation]:
    if common_words is None:
        common_words = load_common_words()
    n = len(text)
    out: list[CharAnnotation] = [CharAnnotation() for _ in range(n)]
    sentence_pending = True
    i = 0
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in ".!?":
            sentence_pending = True
            i += 1
            continue
        is_word_char = ch.isalpha()
        is_digit_char = ch.isdigit()
        if is_word_char or is_digit_char:
            start = i
            j = i
            while j < n and (text[j].isalnum() or text[j] == "'"):
                j += 1
            token = text[start:j]
            is_digit_run = token.isdigit() or any(c.isdigit() for c in token)
            is_rare = is_word_char and token.lower() not in common_words
            out[start] = CharAnnotation(
                word_start=True,
                rare_word_start=is_rare,
                digit_run_start=is_digit_run,
                bracket_or_quote_open=False,
                sentence_start=sentence_pending,
            )
            sentence_pending = False
            i = j
            continue
        if ch in "([{\"'":
            base = out[i]
            out[i] = CharAnnotation(
                word_start=base.word_start,
                rare_word_start=base.rare_word_start,
                digit_run_start=base.digit_run_start,
                bracket_or_quote_open=True,
                sentence_start=sentence_pending or base.sentence_start,
            )
            sentence_pending = False
            i += 1
            continue
        sentence_pending = False
        i += 1
    return out


@dataclass(frozen=True, slots=True)
class ExpandedItem:
    """One physical keystroke to be timed: either typing a character, or a
    correction backspace. Produced by `typing/errors.py`.
    """

    key: str
    is_error: bool = False
    is_correction: bool = False
    annotation: CharAnnotation | None = None
    extra_pause_ms: float = 0.0


def _lognormal(rng: np.random.Generator, median_ms: float, sigma: float) -> float:
    median_ms = max(median_ms, 1e-6)
    return float(rng.lognormal(mean=math.log(median_ms), sigma=sigma))


@dataclass
class _Scheduled:
    item: ExpandedItem
    down_t: float
    hold_ms: float = 0.0
    up_t: float = 0.0


def generate_key_events(
    items: list[ExpandedItem],
    profile: Profile,
    layout: Layout,
    rng: np.random.Generator,
) -> list[KeyEvent]:
    """Assign absolute timestamps to a pre-expanded keystroke sequence and
    return the resulting keydown/keyup event stream, sorted by time.
    """
    if not items:
        return []

    scheduled: list[_Scheduled] = []
    t = 0.0
    burst_remaining = _sample_burst_length(rng, profile.burst.mean_length)
    prev_key: str | None = None
    chars_typed = 0

    for idx, item in enumerate(items):
        if prev_key is not None:
            interval = _sample_interval(rng, profile, layout, prev_key, item)
            interval *= _fatigue_multiplier(profile, chars_typed)
            t += interval

            burst_remaining -= 1
            if burst_remaining <= 0:
                pause = _lognormal(rng, profile.burst.pause_ms_mu, profile.burst.pause_ms_sigma)
                t += pause
                burst_remaining = _sample_burst_length(rng, profile.burst.mean_length)

        if item.annotation is not None:
            t += _cognitive_pause(rng, profile, item.annotation)
        if item.extra_pause_ms:
            t += item.extra_pause_ms

        scheduled.append(_Scheduled(item=item, down_t=t))
        prev_key = item.key
        chars_typed += 1

    for i, sc in enumerate(scheduled):
        hold_mu = profile.hold.mu_ms
        if sc.item.key == BACKSPACE:
            hold_mu *= profile.errors.backspace_speed_multiplier
        hold = _lognormal(rng, hold_mu, profile.hold.sigma)
        up_t = sc.down_t + hold

        if i + 1 < len(scheduled) and rng.random() < profile.rollover.probability:
            overlap = _lognormal(rng, profile.rollover.overlap_ms_mu, 0.35)
            forced_up = scheduled[i + 1].down_t + overlap
            up_t = max(up_t, forced_up)

        sc.hold_ms = hold
        sc.up_t = up_t

    events: list[KeyEvent] = []
    for sc in scheduled:
        key = "backspace" if sc.item.key == BACKSPACE else sc.item.key
        events.append(KeyEvent(t_ms=sc.down_t, action=KeyAction.DOWN, key=key, is_correction=sc.item.is_correction, is_error=sc.item.is_error))
        events.append(KeyEvent(t_ms=sc.up_t, action=KeyAction.UP, key=key, is_correction=sc.item.is_correction, is_error=sc.item.is_error))

    events.sort(key=lambda e: (e.t_ms, e.action != KeyAction.UP))
    return events


def _sample_burst_length(rng: np.random.Generator, mean_length: float) -> int:
    p = 1.0 / max(mean_length, 1.0)
    return int(rng.geometric(p))


def _digraph_class(layout: Layout, prev_key: str, key: str) -> DigraphClass:
    if key == BACKSPACE or prev_key == BACKSPACE:
        return DigraphClass.SAME_HAND_DIFFERENT_FINGER
    return layout.classify_digraph(prev_key, key)


def _sample_interval(
    rng: np.random.Generator,
    profile: Profile,
    layout: Layout,
    prev_key: str,
    item: ExpandedItem,
) -> float:
    key = item.key
    dclass = _digraph_class(layout, prev_key, key)
    multiplier = getattr(profile.digraph_multipliers, dclass.value)
    if key == BACKSPACE:
        multiplier *= profile.errors.backspace_speed_multiplier
    median = profile.interval.mu_ms * multiplier
    return _lognormal(rng, median, profile.interval.sigma)


def _cognitive_pause(rng: np.random.Generator, profile: Profile, ann: CharAnnotation) -> float:
    cfg = profile.cognitive_pauses
    triggers = []
    if ann.sentence_start:
        triggers.append(cfg.sentence_start_probability)
    if ann.rare_word_start:
        triggers.append(cfg.rare_word_probability)
    if ann.digit_run_start:
        triggers.append(cfg.digit_probability)
    if ann.bracket_or_quote_open:
        triggers.append(cfg.bracket_probability)
    if not triggers:
        return 0.0
    p = 1.0 - math.prod(1.0 - t for t in triggers)
    if rng.random() >= p:
        return 0.0
    return float(rng.uniform(cfg.pause_ms_min, cfg.pause_ms_max))


def _fatigue_multiplier(profile: Profile, chars_typed: int) -> float:
    if not profile.fatigue.enabled:
        return 1.0
    return 1.0 + profile.fatigue.interval_drift_per_char * chars_typed
