"""Fit a Profile from a CSV of real keystroke timings
(`timestamp_ms,key,action`), so the model is calibratable against real
data rather than hand-tuned by ear.
"""

from __future__ import annotations

import csv
import math

import numpy as np

from humaninput.layout import DigraphClass, load_layout
from humaninput.profile import (
    BurstConfig,
    DigraphMultipliers,
    ErrorConfig,
    HoldConfig,
    IntervalConfig,
    Profile,
    RolloverConfig,
)


def _lognormal_mle(samples: np.ndarray) -> tuple[float, float]:
    samples = samples[samples > 0]
    if len(samples) < 2:
        return (float(samples[0]) if len(samples) else 1.0, 0.4)
    logs = np.log(samples)
    mu = float(np.mean(logs))
    sigma = float(np.std(logs, ddof=1))
    return math.exp(mu), max(sigma, 0.05)


def read_csv(path: str) -> list[tuple[float, str, str]]:
    rows: list[tuple[float, str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((float(row["timestamp_ms"]), row["key"], row["action"]))
    rows.sort(key=lambda r: r[0])
    return rows


def fit(
    rows: list[tuple[float, str, str]],
    name: str = "fitted",
    layout_name: str = "qwerty",
    burst_pause_threshold_ms: float = 400.0,
) -> Profile:
    layout = load_layout(layout_name)

    downs = [(t, key) for t, key, action in rows if action == "keydown"]
    if len(downs) < 3:
        raise ValueError("need at least 3 keydown events to fit a profile")

    intervals = np.array([b[0] - a[0] for a, b in zip(downs, downs[1:])])
    keys_between = [b[1] for b in downs[1:]]
    prev_keys = [a[1] for a in downs[:-1]]

    classes = [
        DigraphClass.SAME_HAND_DIFFERENT_FINGER if k == "backspace" or pk == "backspace" else layout.classify_digraph(pk, k)
        for pk, k in zip(prev_keys, keys_between)
    ]

    core = intervals <= burst_pause_threshold_ms
    core_intervals = intervals[core]
    core_classes = [c for c, keep in zip(classes, core) if keep]

    by_class: dict[DigraphClass, list[float]] = {c: [] for c in DigraphClass}
    for interval, c in zip(core_intervals, core_classes):
        by_class[c].append(interval)

    baseline_class = DigraphClass.SAME_HAND_DIFFERENT_FINGER
    baseline_samples = by_class[baseline_class]
    baseline_median = float(np.median(baseline_samples)) if len(baseline_samples) >= 5 else float(np.median(core_intervals))
    baseline_median = max(baseline_median, 1.0)

    defaults = DigraphMultipliers()
    multipliers = {}
    for c in DigraphClass:
        samples = by_class[c]
        default = getattr(defaults, c.value)
        if len(samples) >= 5:
            multipliers[c.value] = float(np.median(samples)) / baseline_median
        else:
            multipliers[c.value] = default

    normalized = np.array([iv / multipliers[c.value] for iv, c in zip(core_intervals, core_classes)])
    _, sigma = _lognormal_mle(normalized)
    interval_cfg = IntervalConfig(distribution="lognormal", mu_ms=baseline_median, sigma=sigma)
    digraph_cfg = DigraphMultipliers(**multipliers)

    ups_by_key: dict[str, list[float]] = {}
    downs_by_key: dict[str, list[float]] = {}
    for t, key, action in rows:
        (downs_by_key if action == "keydown" else ups_by_key).setdefault(key, []).append(t)
    holds = []
    for key, down_ts in downs_by_key.items():
        up_ts = sorted(ups_by_key.get(key, []))
        for dt in sorted(down_ts):
            candidates = [u for u in up_ts if u >= dt]
            if candidates:
                holds.append(min(candidates) - dt)
                up_ts.remove(min(candidates))
    hold_median, hold_sigma = _lognormal_mle(np.array(holds)) if holds else (88.0, 0.30)
    hold_cfg = HoldConfig(mu_ms=hold_median, sigma=hold_sigma)

    overlaps = []
    down_times_sorted = sorted(t for t, _, action in rows if action == "keydown")
    up_times_sorted = sorted(t for t, _, action in rows if action == "keyup")
    for i in range(len(down_times_sorted) - 1):
        this_down = down_times_sorted[i]
        next_down = down_times_sorted[i + 1]
        later_ups = [u for u in up_times_sorted if this_down <= u]
        if later_ups and min(later_ups) > next_down:
            overlaps.append(min(later_ups) - next_down)
    rollover_probability = len(overlaps) / max(len(down_times_sorted) - 1, 1)
    overlap_mu = float(np.median(overlaps)) if overlaps else 20.0
    rollover_cfg = RolloverConfig(probability=min(rollover_probability, 1.0), overlap_ms_mu=overlap_mu)

    burst_lengths = []
    run = 1
    pauses = []
    for iv in intervals:
        if iv > burst_pause_threshold_ms:
            burst_lengths.append(run)
            pauses.append(float(iv))
            run = 1
        else:
            run += 1
    burst_lengths.append(run)
    mean_burst = float(np.mean(burst_lengths)) if burst_lengths else 6.5
    pause_mu, pause_sigma = _lognormal_mle(np.array(pauses)) if pauses else (220.0, 0.5)
    burst_cfg = BurstConfig(mean_length=mean_burst, pause_ms_mu=pause_mu, pause_ms_sigma=pause_sigma)

    total_chars = len(downs)
    duration_min = (downs[-1][0] - downs[0][0]) / 1000.0 / 60.0
    wpm = (total_chars / 5) / duration_min if duration_min > 0 else 70.0

    backspace_rate = sum(1 for _, k in downs if k == "backspace") / total_chars
    error_cfg = ErrorConfig(
        substitution_rate=min(backspace_rate / 2, 0.5),
        omission_rate=min(backspace_rate / 4, 0.5),
        insertion_rate=min(backspace_rate / 4, 0.5),
    )

    return Profile(
        name=name,
        wpm_target=round(wpm, 1),
        layout=layout_name,
        interval=interval_cfg,
        digraph_multipliers=digraph_cfg,
        hold=hold_cfg,
        rollover=rollover_cfg,
        burst=burst_cfg,
        errors=error_cfg,
    )


def fit_csv(path: str, name: str = "fitted", layout_name: str = "qwerty") -> Profile:
    return fit(read_csv(path), name=name, layout_name=layout_name)
