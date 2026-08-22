"""Error injection and correction.

Turns clean target text into the sequence of keystrokes a flawed human
typist would actually produce: occasional wrong characters, and — after a
delay measured in characters, not instantaneous — backspaces and a
retype. This is the single biggest visible difference between a naive
simulator and a real one.

Reproducibility: every random decision goes through the caller-supplied
`numpy.random.Generator`, so the same seed always produces the same
errors and corrections.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from humaninput.layout import Layout
from humaninput.profile import Profile
from humaninput.typing.model import BACKSPACE, ExpandedItem, annotate_text


@dataclass
class _Step:
    item_start: int
    item_end: int
    source_start: int
    source_end: int
    is_error: bool
    error_kind: str | None = None


def _pick_substitute(layout: Layout, ch: str, rng: np.random.Generator) -> str:
    neighbors = layout.neighbors(ch, n=6)
    same_case_neighbors = [c for c in neighbors if c.isalpha() == ch.isalpha()]
    pool = same_case_neighbors or neighbors
    if not pool:
        return ch
    weights = np.array([1.0 / (i + 1) for i in range(len(pool))])
    weights /= weights.sum()
    idx = rng.choice(len(pool), p=weights)
    picked = pool[idx]
    if ch.isupper() and picked.isalpha():
        picked = picked.upper()
    return picked


def _word_start_index(text: str, idx: int) -> int:
    i = idx
    while i > 0 and (text[i - 1].isalnum() or text[i - 1] == "'"):
        i -= 1
    return i


def _next_word_boundary(text: str, idx: int) -> int:
    i = idx
    n = len(text)
    while i < n and (text[i].isalnum() or text[i] == "'"):
        i += 1
    return i


def plan(
    text: str,
    profile: Profile,
    layout: Layout,
    rng: np.random.Generator,
    errors_enabled: bool = True,
) -> list[ExpandedItem]:
    annotations = annotate_text(text)

    if not errors_enabled:
        return [ExpandedItem(key=ch, annotation=annotations[i]) for i, ch in enumerate(text)]

    raw_items: list[ExpandedItem] = []
    steps: list[_Step] = []
    error_step_indices: list[int] = []

    cfg = profile.errors
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        ann = annotations[i]

        if not ch.isalnum():
            item_start = len(raw_items)
            raw_items.append(ExpandedItem(key=ch, annotation=ann))
            steps.append(_Step(item_start, len(raw_items), i, i + 1, is_error=False))
            i += 1
            continue

        roll = rng.random()
        cumulative = 0.0
        kind: str | None = None
        can_transpose = i + 1 < n and text[i + 1].isalnum()
        for candidate, rate in (
            ("transposition", cfg.transposition_rate if can_transpose else 0.0),
            ("substitution", cfg.substitution_rate),
            ("insertion", cfg.insertion_rate),
            ("omission", cfg.omission_rate),
        ):
            cumulative += rate
            if roll < cumulative:
                kind = candidate
                break

        item_start = len(raw_items)
        if kind is None:
            raw_items.append(ExpandedItem(key=ch, annotation=ann))
            steps.append(_Step(item_start, len(raw_items), i, i + 1, is_error=False))
            i += 1
            continue

        if kind == "substitution":
            wrong = _pick_substitute(layout, ch, rng)
            raw_items.append(ExpandedItem(key=wrong, is_error=True, annotation=ann))
            consumed = 1
        elif kind == "transposition":
            raw_items.append(ExpandedItem(key=text[i + 1], is_error=True, annotation=ann))
            raw_items.append(ExpandedItem(key=text[i], is_error=True))
            consumed = 2
        elif kind == "insertion":
            wrong = _pick_substitute(layout, ch, rng)
            raw_items.append(ExpandedItem(key=wrong, is_error=True, annotation=ann))
            raw_items.append(ExpandedItem(key=ch))
            consumed = 1
        else:
            consumed = 1

        step_idx = len(steps)
        steps.append(_Step(item_start, len(raw_items), i, i + consumed, is_error=True, error_kind=kind))
        error_step_indices.append(step_idx)
        i += consumed

    if cfg.correction_strategy == "ignore" or not error_step_indices:
        return raw_items

    final_items: list[ExpandedItem] = []
    cursor_item = 0
    cursor_source = 0

    for step_idx in error_step_indices:
        error_step = steps[step_idx]
        if error_step.item_start < cursor_item:
            continue

        if rng.random() < cfg.uncorrected_rate:
            continue

        delay_lo, delay_hi = cfg.detection_delay_chars
        delay_chars = int(rng.integers(delay_lo, delay_hi + 1)) if delay_hi >= delay_lo else 0
        word_level = rng.random() < cfg.detection_delay_word_probability

        detect_step_idx = min(step_idx + 1 + delay_chars, len(steps))
        detect_step_idx = max(detect_step_idx, step_idx + 1)
        if word_level:
            target_source = _next_word_boundary(text, error_step.source_end)
            j = step_idx + 1
            while j < len(steps) and steps[j].source_end < target_source:
                j += 1
            detect_step_idx = max(detect_step_idx, min(j + 1, len(steps)))

        if detect_step_idx <= len(steps) and detect_step_idx > 0:
            detection_item_idx = steps[detect_step_idx - 1].item_end
            detection_source_idx = steps[detect_step_idx - 1].source_end
        else:
            detection_item_idx = len(raw_items)
            detection_source_idx = n

        if cfg.correction_strategy == "word":
            strategy_source_start = _word_start_index(text, error_step.source_start)
            k = step_idx
            while k > 0 and steps[k].source_start > strategy_source_start:
                k -= 1
            strategy_item_start = steps[k].item_start
        else:
            strategy_source_start = error_step.source_start
            strategy_item_start = error_step.item_start

        strategy_item_start = max(strategy_item_start, cursor_item)
        detection_item_idx = max(detection_item_idx, strategy_item_start)
        strategy_source_start = max(strategy_source_start, cursor_source)
        detection_source_idx = max(detection_source_idx, strategy_source_start)

        backspace_count = detection_item_idx - strategy_item_start
        if backspace_count <= 0 and detection_source_idx <= strategy_source_start:
            continue

        final_items.extend(raw_items[cursor_item:detection_item_idx])

        if backspace_count > 0:
            notice_pause = float(rng.uniform(cfg.notice_pause_ms_min, cfg.notice_pause_ms_max))
            for b in range(backspace_count):
                extra = notice_pause if b == 0 else 0.0
                final_items.append(ExpandedItem(key=BACKSPACE, is_correction=True, extra_pause_ms=extra))

        for src_idx in range(strategy_source_start, detection_source_idx):
            final_items.append(ExpandedItem(key=text[src_idx], is_correction=True))

        cursor_item = detection_item_idx
        cursor_source = detection_source_idx

    final_items.extend(raw_items[cursor_item:])
    return final_items
