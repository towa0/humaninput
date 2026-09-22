"""Public entry point for the touch model. Like `Pointer`, `Touch`
performs no I/O — it returns an `EventStream` of `TouchEvent`s.

A finger targeting a point on glass is still a goal-directed reaching
movement, so this reuses `generate_trajectory`'s minimum-jerk path
synthesis from the mouse model (Flash & Hogan, 1985 — the model isn't
specific to any one effector). What differs is the *parameterization*
(`profile.touch`: far fewer in-flight corrections, since a finger targets
its destination directly rather than via an indirect cursor with a
separate visual feedback loop, and no tremor overlay by default, since
touchscreen digitizers debounce/smooth raw contact samples) and the
*event semantics*: `TouchEvent` has no persistent cursor/hover state or
button, so it's a distinct type from `MouseEvent` rather than a relabeled
reuse of it.
"""

from __future__ import annotations

import math

import numpy as np

from humaninput.events import EventStream, TouchEvent
from humaninput.mouse import fitts
from humaninput.mouse.trajectory import generate_trajectory
from humaninput.profile import Profile


class Touch:
    def __init__(self, profile: Profile, seed: int | tuple[int, ...] | None = None):
        self.profile = profile
        self.seed = seed

    def _rng(self, salt: int = 0) -> np.random.Generator:
        if self.seed is None:
            return np.random.default_rng()
        if isinstance(self.seed, tuple):
            return np.random.default_rng((*self.seed, salt))
        return np.random.default_rng((self.seed, salt))

    def tap(self, x: float, y: float) -> EventStream:
        """A single touchstart/touchend at a fixed point (no travel) —
        the touch equivalent of `Pointer.click`."""
        rng = self._rng(1)
        cfg = self.profile.touch
        hold = float(rng.lognormal(mean=math.log(cfg.tap_hold_ms_mu), sigma=cfg.tap_hold_ms_sigma))
        events = [
            TouchEvent(t_ms=0.0, type="touchstart", x=x, y=y),
            TouchEvent(t_ms=hold, type="touchend", x=x, y=y),
            TouchEvent(t_ms=hold, type="tap", x=x, y=y),
        ]
        return EventStream(events=events, seed=self.seed, profile_name=self.profile.name)

    def drag(
        self,
        from_xy: tuple[float, float],
        to_xy: tuple[float, float],
        target_width: float = 40.0,
    ) -> EventStream:
        """Touch down at `from_xy`, drag to `to_xy` along a minimum-jerk
        path, then release."""
        rng = self._rng(2)
        cfg = self.profile.touch
        dist = math.dist(from_xy, to_xy)
        idx_difficulty = fitts.index_of_difficulty(dist, target_width)
        total_mt = fitts.movement_time_ms(dist, target_width, cfg.fitts_a_ms, cfg.fitts_b_ms)
        total_mt /= max(cfg.drag_speed_multiplier, 1e-3)

        ballistic_fraction = float(rng.uniform(cfg.ballistic_fraction_min, cfg.ballistic_fraction_max))
        overshoot = bool(rng.random() < cfg.overshoot_probability)
        expected_corrections = max(cfg.correction_base_count + cfg.correction_count_per_id_bit * idx_difficulty, 0.01)
        num_corrections = int(np.clip(rng.poisson(expected_corrections), 0, 2))

        samples = generate_trajectory(
            from_xy,
            to_xy,
            total_mt,
            rng,
            sample_rate_hz=cfg.sample_rate_hz,
            ballistic_fraction=ballistic_fraction,
            num_corrections=num_corrections,
            overshoot=overshoot,
            overshoot_fraction=cfg.overshoot_fraction,
            tremor_amplitude_px=cfg.tremor_amplitude_px,
            tremor_frequency_hz=cfg.tremor_frequency_hz,
        )
        events: list[TouchEvent] = [TouchEvent(t_ms=0.0, type="touchstart", x=from_xy[0], y=from_xy[1])]
        events.extend(TouchEvent(t_ms=s.t_ms, type="touchmove", x=s.x, y=s.y, vx=s.vx, vy=s.vy) for s in samples)
        end_t = samples[-1].t_ms if samples else 0.0
        events.append(TouchEvent(t_ms=end_t, type="touchend", x=to_xy[0], y=to_xy[1]))
        return EventStream(events=events, seed=self.seed, profile_name=self.profile.name)
