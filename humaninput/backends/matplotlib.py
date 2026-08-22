"""Visual validation backend: plot a generated mouse trajectory with its
velocity profile, or a histogram of generated inter-key intervals against
the profile's configured distribution. `matplotlib` is imported lazily so
the core package never requires it.
"""

from __future__ import annotations

from humaninput.events import EventStream, KeyAction


def plot_trajectory(stream: EventStream, show: bool = True, ax=None):
    import matplotlib.pyplot as plt

    xs = [e.x for e in stream if e.type in ("move", "drag")]
    ys = [e.y for e in stream if e.type in ("move", "drag")]
    ts = [e.t_ms for e in stream if e.type in ("move", "drag")]
    speed = [((e.vx**2 + e.vy**2) ** 0.5) for e in stream if e.type in ("move", "drag")]

    if ax is None:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    else:
        ax1, ax2 = ax

    ax1.plot(xs, ys, "-", linewidth=1.2, color="#3b6fd6")
    ax1.plot(xs[0], ys[0], "o", color="green", label="start")
    ax1.plot(xs[-1], ys[-1], "o", color="red", label="end")
    ax1.invert_yaxis()
    ax1.set_aspect("equal", adjustable="datalim")
    ax1.set_title("Trajectory")
    ax1.legend(loc="best", fontsize=8)

    ax2.plot(ts, speed, "-", color="#d6633b")
    ax2.set_xlabel("t (ms)")
    ax2.set_ylabel("speed (px/s)")
    ax2.set_title("Velocity profile")

    if show:
        plt.tight_layout()
        plt.show()
    return ax1.figure


def plot_interval_histogram(stream: EventStream, profile=None, median_ms: float | None = None, show: bool = True, ax=None):
    import math

    import matplotlib.pyplot as plt
    import numpy as np

    downs = sorted(e.t_ms for e in stream if e.action == KeyAction.DOWN)
    intervals = np.diff(downs)

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 4))

    ax.hist(intervals, bins=40, density=True, alpha=0.6, color="#3b6fd6", label="generated")

    if profile is not None:
        median = median_ms if median_ms is not None else profile.interval.mu_ms
        sigma = profile.interval.sigma
        x = np.linspace(max(intervals.min(), 1), intervals.max(), 300)
        pdf = (1.0 / (x * sigma * math.sqrt(2 * math.pi))) * np.exp(
            -((np.log(x) - math.log(median)) ** 2) / (2 * sigma**2)
        )
        ax.plot(x, pdf, color="#d6633b", linewidth=2, label="configured log-normal")

    ax.set_xlabel("inter-key interval (ms)")
    ax.set_ylabel("density")
    ax.set_title("Inter-key interval distribution")
    ax.legend(loc="best", fontsize=8)

    if show:
        plt.tight_layout()
        plt.show()
    return ax.figure
