"""Statistical validation of the touch model (mirrors test_mouse_stats.py)
plus event-shape checks for `Touch.tap`/`Touch.drag`.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from humaninput import profile as profiles
from humaninput.events import TouchEvent
from humaninput.mouse.fitts import index_of_difficulty
from humaninput.touch.pointer import Touch


def test_drag_duration_fits_fitts_law():
    prof = profiles.load("mobile_thumbs")

    distances = [50, 100, 200, 400, 600]
    widths = [20, 40, 80]

    ids, durations = [], []
    for d in distances:
        for w in widths:
            trial_durations = [
                Touch(profile=prof, seed=(d, w, trial)).drag((0, 0), (d, 0), target_width=w).duration_ms
                for trial in range(6)
            ]
            ids.append(index_of_difficulty(d, w))
            durations.append(float(np.mean(trial_durations)))

    slope, intercept, r_value, p_value, std_err = stats.linregress(ids, durations)
    assert r_value**2 > 0.9, f"R^2={r_value**2:.3f} too low for Fitts's law fit"


def test_touch_has_fewer_corrections_than_mouse_for_same_target():
    """Direct pointing (finger) should show noticeably fewer in-flight
    corrective sub-movements than indirect pointing (mouse cursor) for a
    comparably hard target, since `touch.correction_base_count` and
    `touch.correction_count_per_id_bit` are much lower than the mouse
    defaults."""
    prof = profiles.load("touch_typist")

    def avg_dwell_count_touch(distance, width, n_trials=25):
        counts = []
        for trial in range(n_trials):
            events = Touch(profile=prof, seed=(distance, width, trial)).drag(
                (0, 0), (distance, 0), target_width=width
            ).events
            moves = [e for e in events if e.type == "touchmove"]
            speed = np.array([(e.vx**2 + e.vy**2) ** 0.5 for e in moves])
            if speed.max() <= 0:
                counts.append(0)
                continue
            near_zero = speed < max(speed.max() * 0.02, 1e-6)
            edges = np.diff(near_zero.astype(int))
            num_runs = int(np.sum(edges == 1)) + (1 if near_zero[0] else 0)
            counts.append(max(num_runs - 2, 0))
        return float(np.mean(counts))

    from humaninput.mouse.pointer import Pointer

    def avg_dwell_count_mouse(distance, width, n_trials=25):
        counts = []
        for trial in range(n_trials):
            stream = Pointer(profile=prof, seed=(distance, width, trial)).move((0, 0), (distance, 0), target_width=width)
            speed = np.array([(e.vx**2 + e.vy**2) ** 0.5 for e in stream.events])
            near_zero = speed < max(speed.max() * 0.02, 1e-6)
            edges = np.diff(near_zero.astype(int))
            num_runs = int(np.sum(edges == 1)) + (1 if near_zero[0] else 0)
            counts.append(max(num_runs - 2, 0))
        return float(np.mean(counts))

    touch_corrections = avg_dwell_count_touch(1400, 8)
    mouse_corrections = avg_dwell_count_mouse(1400, 8)
    assert touch_corrections < mouse_corrections, (
        f"touch={touch_corrections:.2f} should be lower than mouse={mouse_corrections:.2f}"
    )


def test_tap_emits_touchstart_touchend_tap_at_same_point():
    prof = profiles.load("mobile_thumbs")
    stream = Touch(profile=prof, seed=1).tap(50, 60)

    assert [e.type for e in stream.events] == ["touchstart", "touchend", "tap"]
    assert all(e.x == 50 and e.y == 60 for e in stream.events)
    assert stream.events[0].t_ms == 0.0
    assert stream.events[1].t_ms == stream.events[2].t_ms > 0.0


def test_drag_starts_and_ends_at_requested_points():
    prof = profiles.load("mobile_thumbs")
    stream = Touch(profile=prof, seed=1).drag((10, 10), (300, 200), target_width=30)

    events = stream.events
    assert isinstance(events[0], TouchEvent)
    assert events[0].type == "touchstart"
    assert (events[0].x, events[0].y) == (10, 10)
    assert events[-1].type == "touchend"
    assert (events[-1].x, events[-1].y) == (300, 200)
    assert all(e.type == "touchmove" for e in events[1:-1])


def test_touch_seeded_reproducibility():
    prof = profiles.load("mobile_thumbs")
    a = Touch(profile=prof, seed=42).drag((0, 0), (500, 300), target_width=30)
    b = Touch(profile=prof, seed=42).drag((0, 0), (500, 300), target_width=30)
    assert a.events == b.events

    c = Touch(profile=prof, seed=43).drag((0, 0), (500, 300), target_width=30)
    assert a.events != c.events

    tap_a = Touch(profile=prof, seed=1).tap(10, 10)
    tap_b = Touch(profile=prof, seed=1).tap(10, 10)
    assert tap_a.events == tap_b.events
