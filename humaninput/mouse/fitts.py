"""Fitts's law: movement time as a function of distance and target width.

    MT = a + b * log2(2D / W)

Fitts, P. M. (1954). The information capacity of the human motor system
in controlling the amplitude of movement. Journal of Experimental
Psychology, 47(6), 381-391.

`a` and `b` are empirical, per-person/device constants and are exposed as
profile parameters (`mouse.fitts_a_ms`, `mouse.fitts_b_ms`) rather than
hardcoded, since they vary by input device and individual.
"""

from __future__ import annotations

import math


def index_of_difficulty(distance: float, width: float) -> float:
    width = max(width, 1e-6)
    return math.log2(2.0 * distance / width + 1e-12) if distance > 0 else 0.0


def movement_time_ms(distance: float, width: float, a_ms: float, b_ms: float) -> float:
    if distance <= 0:
        return a_ms
    return a_ms + b_ms * index_of_difficulty(distance, width)
