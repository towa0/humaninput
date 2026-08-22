"""Statistical validation of the mouse model: Fitts's law fit quality and
the shape of the minimum-jerk velocity profile.
"""

from __future__ import annotations

import numpy as np
from scipy import stats

from humaninput import profile as profiles
from humaninput.mouse.pointer import Pointer
from humaninput.mouse.trajectory import min_jerk_ds


def test_movement_duration_fits_fitts_law():
    """Sweep distance and target width, average out sub-movement-count
    noise over repeated trials, and check that mean movement duration is
    linear in the Fitts index of difficulty with R^2 > 0.95.
    """
    prof = profiles.load("touch_typist")

    distances = [100, 200, 400, 800, 1200]
    widths = [10, 25, 50, 100]

    ids = []
    durations = []
    for d in distances:
        for w in widths:
            trial_durations = []
            for trial in range(6):
                p = Pointer(profile=prof, seed=(d, w, trial))
                stream = p.move((0, 0), (d, 0), target_width=w)
                trial_durations.append(stream.duration_ms)
            from humaninput.mouse.fitts import index_of_difficulty

            ids.append(index_of_difficulty(d, w))
            durations.append(float(np.mean(trial_durations)))

    slope, intercept, r_value, p_value, std_err = stats.linregress(ids, durations)
    assert r_value**2 > 0.95, f"R^2={r_value**2:.3f} too low for Fitts's law fit"


def test_ballistic_velocity_profile_is_unimodal_and_symmetric():
    u = np.linspace(0.0, 1.0, 201)
    v = min_jerk_ds(u)

    peak_idx = int(np.argmax(v))
    assert abs(u[peak_idx] - 0.5) < 0.02, "peak velocity should be at the midpoint of the movement"

    assert np.all(np.diff(v[: peak_idx + 1]) >= -1e-9), "velocity should rise monotonically before the peak"
    assert np.all(np.diff(v[peak_idx:]) <= 1e-9), "velocity should fall monotonically after the peak"

    assert np.allclose(v, v[::-1], atol=1e-6), "velocity profile should be symmetric about the midpoint"


def test_mouse_seeded_reproducibility():
    prof = profiles.load("touch_typist")
    a = Pointer(profile=prof, seed=42).move((0, 0), (500, 300), target_width=30)
    b = Pointer(profile=prof, seed=42).move((0, 0), (500, 300), target_width=30)
    assert a.events == b.events

    c = Pointer(profile=prof, seed=43).move((0, 0), (500, 300), target_width=30)
    assert a.events != c.events

    click_a = Pointer(profile=prof, seed=1).click(10, 10)
    click_b = Pointer(profile=prof, seed=1).click(10, 10)
    assert click_a.events == click_b.events


def test_expected_corrections_increase_with_difficulty():
    """Higher Fitts index of difficulty (smaller, more distant targets)
    should on average produce more corrective sub-movements, measured
    indirectly via the number of local velocity minima (dwell points)
    in the trajectory.
    """
    prof = profiles.load("touch_typist")

    def avg_dwell_count(distance, width, n_trials=25):
        """Every sub-movement starts and ends at rest (minimum-jerk from
        rest to rest), so each internal join between the ballistic phase
        and a corrective sub-movement shows up as a run of near-zero
        speed samples in the interior of the trajectory. Every movement
        has one such run at the very start and one at the very end
        regardless of corrections, so those two are excluded.
        """
        counts = []
        for trial in range(n_trials):
            p = Pointer(profile=prof, seed=(distance, width, trial))
            stream = p.move((0, 0), (distance, 0), target_width=width)
            speed = np.array([(e.vx**2 + e.vy**2) ** 0.5 for e in stream.events])
            near_zero = speed < max(speed.max() * 0.02, 1e-6)
            edges = np.diff(near_zero.astype(int))
            num_runs = int(np.sum(edges == 1)) + (1 if near_zero[0] else 0)
            counts.append(max(num_runs - 2, 0))
        return float(np.mean(counts))

    easy = avg_dwell_count(150, 120)
    hard = avg_dwell_count(1400, 8)
    assert hard > easy, f"expected more corrections for harder target: easy={easy:.2f} hard={hard:.2f}"
