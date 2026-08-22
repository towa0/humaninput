"""Public entry point for the mouse model. Like `Typist`, `Pointer`
performs no I/O — it returns an `EventStream` of `MouseEvent`s.
"""

from __future__ import annotations

import math

import numpy as np

from humaninput.events import EventStream, MouseEvent
from humaninput.mouse import fitts
from humaninput.mouse.trajectory import generate_trajectory
from humaninput.profile import Profile


class Pointer:
    def __init__(self, profile: Profile, seed: int | None = None):
        self.profile = profile
        self.seed = seed

    def _rng(self, salt: int = 0) -> np.random.Generator:
        if self.seed is None:
            return np.random.default_rng()
        return np.random.default_rng((self.seed, salt))

    def move(
        self,
        from_xy: tuple[float, float],
        to_xy: tuple[float, float],
        target_width: float = 40.0,
    ) -> EventStream:
        rng = self._rng(1)
        cfg = self.profile.mouse
        dist = math.dist(from_xy, to_xy)
        idx_difficulty = fitts.index_of_difficulty(dist, target_width)
        total_mt = fitts.movement_time_ms(dist, target_width, cfg.fitts_a_ms, cfg.fitts_b_ms)

        ballistic_fraction = float(rng.uniform(cfg.ballistic_fraction_min, cfg.ballistic_fraction_max))
        overshoot = bool(rng.random() < cfg.overshoot_probability)

        expected_corrections = max(cfg.correction_base_count + cfg.correction_count_per_id_bit * idx_difficulty, 0.01)
        num_corrections = int(np.clip(rng.poisson(expected_corrections), 0, 3))

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
        events = [MouseEvent(t_ms=s.t_ms, type="move", x=s.x, y=s.y, vx=s.vx, vy=s.vy) for s in samples]
        return EventStream(events=events, seed=self.seed, profile_name=self.profile.name)

    def click(self, x: float, y: float, button: str = "left") -> EventStream:
        rng = self._rng(2)
        cfg = self.profile.mouse
        hold = float(rng.lognormal(mean=math.log(cfg.click_hold_ms_mu), sigma=cfg.click_hold_ms_sigma))
        events = [
            MouseEvent(t_ms=0.0, type="down", x=x, y=y, button=button),
            MouseEvent(t_ms=hold, type="up", x=x, y=y, button=button),
            MouseEvent(t_ms=hold, type="click", x=x, y=y, button=button),
        ]
        return EventStream(events=events, seed=self.seed, profile_name=self.profile.name)

    def double_click(self, x: float, y: float, button: str = "left") -> EventStream:
        rng = self._rng(3)
        cfg = self.profile.mouse
        hold1 = float(rng.lognormal(mean=math.log(cfg.click_hold_ms_mu), sigma=cfg.click_hold_ms_sigma))
        gap = float(rng.lognormal(mean=math.log(cfg.dblclick_interval_ms_mu), sigma=cfg.dblclick_interval_ms_sigma))
        hold2 = float(rng.lognormal(mean=math.log(cfg.click_hold_ms_mu), sigma=cfg.click_hold_ms_sigma))
        t = 0.0
        events = [MouseEvent(t_ms=t, type="down", x=x, y=y, button=button)]
        t += hold1
        events.append(MouseEvent(t_ms=t, type="up", x=x, y=y, button=button))
        events.append(MouseEvent(t_ms=t, type="click", x=x, y=y, button=button))
        t += gap
        events.append(MouseEvent(t_ms=t, type="down", x=x, y=y, button=button))
        t += hold2
        events.append(MouseEvent(t_ms=t, type="up", x=x, y=y, button=button))
        events.append(MouseEvent(t_ms=t, type="dblclick", x=x, y=y, button=button))
        return EventStream(events=events, seed=self.seed, profile_name=self.profile.name)

    def drag(
        self,
        from_xy: tuple[float, float],
        to_xy: tuple[float, float],
        target_width: float = 40.0,
        button: str = "left",
    ) -> EventStream:
        rng = self._rng(4)
        cfg = self.profile.mouse
        dist = math.dist(from_xy, to_xy)
        idx_difficulty = fitts.index_of_difficulty(dist, target_width)
        total_mt = fitts.movement_time_ms(dist, target_width, cfg.fitts_a_ms, cfg.fitts_b_ms)
        total_mt /= max(cfg.drag_speed_multiplier, 1e-3)

        ballistic_fraction = float(rng.uniform(cfg.ballistic_fraction_min, cfg.ballistic_fraction_max))
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
            overshoot=False,
            tremor_amplitude_px=cfg.tremor_amplitude_px * 1.5,
            tremor_frequency_hz=cfg.tremor_frequency_hz,
        )
        events: list[MouseEvent] = [MouseEvent(t_ms=0.0, type="down", x=from_xy[0], y=from_xy[1], button=button)]
        events.extend(MouseEvent(t_ms=s.t_ms, type="drag", x=s.x, y=s.y, vx=s.vx, vy=s.vy, button=button) for s in samples)
        end_t = samples[-1].t_ms if samples else 0.0
        events.append(MouseEvent(t_ms=end_t, type="up", x=to_xy[0], y=to_xy[1], button=button))
        return EventStream(events=events, seed=self.seed, profile_name=self.profile.name)

    def scroll(self, x: float, y: float, detents: int, direction: str = "down") -> EventStream:
        """Discrete wheel detents with an acceleration curve: intervals
        shrink through the middle of the scroll and lengthen at the end,
        mimicking a hand spinning a wheel up then easing off.
        """
        rng = self._rng(5)
        cfg = self.profile.mouse
        dy = 1.0 if direction == "down" else -1.0
        events: list[MouseEvent] = []
        t = 0.0
        for i in range(max(detents, 0)):
            progress = i / max(detents - 1, 1)
            accel = 1.0 - 0.5 * math.sin(math.pi * progress)
            interval = float(rng.lognormal(mean=math.log(cfg.scroll_detent_ms_mu * accel), sigma=cfg.scroll_detent_ms_sigma))
            if i > 0:
                t += interval
            events.append(MouseEvent(t_ms=t, type="scroll", x=x, y=y, scroll_dx=0.0, scroll_dy=dy))
        return EventStream(events=events, seed=self.seed, profile_name=self.profile.name)
