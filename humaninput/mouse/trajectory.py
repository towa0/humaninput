"""Trajectory synthesis: ballistic sub-movement plus corrective
sub-movements, each following a minimum-jerk velocity profile, with a
tremor overlay.

Minimum jerk: Flash, T., & Hogan, N. (1985). The coordination of arm
movements: an experimentally confirmed mathematical model. Journal of
Neuroscience, 5(7), 1688-1703. The position profile

    s(u) = 10u^3 - 15u^4 + 6u^5,   u = t / T in [0, 1]

is the unique minimum-jerk (smoothest) trajectory between two points at
rest, and its velocity ds/du is a single symmetric bell curve — not a
constant, and not the asymmetric curve a plain ease-in/ease-out gives.

Real pointing motion is not one smooth curve: it is a fast, somewhat
imprecise ballistic phase followed by one to three smaller corrective
sub-movements that close the remaining distance to the target, each with
its own bell-shaped speed profile. Chaining several minimum-jerk segments
end-to-end (rather than fitting one curve start-to-finish) is what
produces the characteristic decelerate-overshoot-correct shape.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def min_jerk_s(u: np.ndarray) -> np.ndarray:
    """Normalized position fraction, u in [0, 1] -> s in [0, 1]."""
    return 10 * u**3 - 15 * u**4 + 6 * u**5


def min_jerk_ds(u: np.ndarray) -> np.ndarray:
    """Normalized velocity (d s / d u)."""
    return 30 * u**2 - 60 * u**3 + 30 * u**4


@dataclass(frozen=True, slots=True)
class Sample:
    t_ms: float
    x: float
    y: float
    vx: float
    vy: float


class _ValueNoise:
    """Smooth 1D noise via linear-interpolated random lattice values with
    a smoothstep ease, used instead of per-sample Gaussian jitter. This is
    the key distinction from naive jitter: adjacent samples are
    correlated, so the result looks like a hand's low-frequency tremor
    rather than static/sensor noise.
    """

    def __init__(self, rng: np.random.Generator, n_lattice: int = 64, seed_offset: int = 0):
        self._lattice = rng.normal(0.0, 1.0, size=max(n_lattice, 2))

    @staticmethod
    def _smoothstep(t: np.ndarray) -> np.ndarray:
        return t * t * (3 - 2 * t)

    def sample(self, phase: np.ndarray) -> np.ndarray:
        """phase: array of arbitrary non-negative floats (e.g. time * freq).
        Returns values roughly in [-1, 1].
        """
        n = len(self._lattice)
        idx_f = phase % n
        i0 = np.floor(idx_f).astype(int)
        i1 = (i0 + 1) % n
        frac = self._smoothstep(idx_f - i0)
        return self._lattice[i0] * (1 - frac) + self._lattice[i1] * frac


def _min_jerk_segment(
    start: tuple[float, float],
    end: tuple[float, float],
    duration_ms: float,
    t0_ms: float,
    sample_rate_hz: float,
) -> list[Sample]:
    if duration_ms <= 0:
        return [Sample(t0_ms, end[0], end[1], 0.0, 0.0)]
    dt_ms = 1000.0 / sample_rate_hz
    n_samples = max(int(duration_ms / dt_ms), 2)
    t = np.linspace(0.0, duration_ms, n_samples)
    u = t / duration_ms
    s = min_jerk_s(u)
    ds = min_jerk_ds(u) / duration_ms

    dx, dy = end[0] - start[0], end[1] - start[1]
    xs = start[0] + dx * s
    ys = start[1] + dy * s
    vxs = dx * ds * 1000.0
    vys = dy * ds * 1000.0

    return [Sample(t0_ms + t[i], float(xs[i]), float(ys[i]), float(vxs[i]), float(vys[i])) for i in range(n_samples)]


def generate_trajectory(
    start: tuple[float, float],
    end: tuple[float, float],
    total_duration_ms: float,
    rng: np.random.Generator,
    *,
    sample_rate_hz: float = 120.0,
    ballistic_fraction: float = 0.90,
    ballistic_time_fraction: float = 0.75,
    num_corrections: int = 1,
    overshoot: bool = False,
    overshoot_fraction: float = 0.06,
    dwell_ms: float = 25.0,
    tremor_amplitude_px: float = 0.6,
    tremor_frequency_hz: float = 8.0,
) -> list[Sample]:
    """Build a full move as a ballistic sub-movement, optional overshoot,
    and `num_corrections` corrective sub-movements, all minimum-jerk, with
    a value-noise tremor overlaid on the finished path.
    """
    dx, dy = end[0] - start[0], end[1] - start[1]
    dist = (dx**2 + dy**2) ** 0.5

    samples: list[Sample] = []
    t_cursor = 0.0

    ballistic_target = end
    if dist > 0:
        ballistic_end_frac = ballistic_fraction * (1.0 + overshoot_fraction if overshoot else 1.0)
        ballistic_target = (start[0] + dx * ballistic_end_frac, start[1] + dy * ballistic_end_frac)

    ballistic_duration = total_duration_ms * ballistic_time_fraction
    seg = _min_jerk_segment(start, ballistic_target, ballistic_duration, t_cursor, sample_rate_hz)
    samples.extend(seg)
    t_cursor += ballistic_duration

    current_pos = ballistic_target
    remaining_time = max(total_duration_ms - ballistic_duration, 0.0)
    n_corr = max(num_corrections, 0)

    for i in range(n_corr):
        t_cursor += dwell_ms
        frac_of_remaining_error = 0.65 if i < n_corr - 1 else 1.0
        next_pos = (
            current_pos[0] + (end[0] - current_pos[0]) * frac_of_remaining_error,
            current_pos[1] + (end[1] - current_pos[1]) * frac_of_remaining_error,
        )
        corr_duration = remaining_time / n_corr if n_corr else 0.0
        corr_duration = max(corr_duration, 20.0)
        seg = _min_jerk_segment(current_pos, next_pos, corr_duration, t_cursor, sample_rate_hz)
        samples.extend(seg)
        t_cursor += corr_duration
        current_pos = next_pos

    if current_pos != end and n_corr == 0:
        pass

    if tremor_amplitude_px > 0 and samples:
        noise_x = _ValueNoise(rng)
        noise_y = _ValueNoise(rng)
        t_arr = np.array([s.t_ms for s in samples])
        phase = t_arr / 1000.0 * tremor_frequency_hz
        nx = noise_x.sample(phase) * tremor_amplitude_px
        ny = noise_y.sample(phase) * tremor_amplitude_px
        samples = [
            Sample(s.t_ms, s.x + nx[i], s.y + ny[i], s.vx, s.vy) for i, s in enumerate(samples)
        ]

    return samples
