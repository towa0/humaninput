"""Event types emitted by the timing engine.

These are pure data. The engine never performs I/O; it returns lists of
these events, and backends decide what to do with them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class KeyAction(str, Enum):
    DOWN = "keydown"
    UP = "keyup"


@dataclass(frozen=True, slots=True)
class KeyEvent:
    """A single keydown/keyup with an absolute timestamp in milliseconds."""

    t_ms: float
    action: KeyAction
    key: str
    is_correction: bool = False
    is_error: bool = False

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"KeyEvent({self.t_ms:.1f}ms {self.action.value} {self.key!r})"


MouseEventType = Literal["move", "down", "up", "click", "dblclick", "drag", "scroll"]


@dataclass(frozen=True, slots=True)
class MouseEvent:
    """A single mouse sample with position, velocity, and absolute timestamp."""

    t_ms: float
    type: MouseEventType
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    button: str | None = None
    scroll_dx: float = 0.0
    scroll_dy: float = 0.0

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"MouseEvent({self.t_ms:.1f}ms {self.type} ({self.x:.1f},{self.y:.1f}))"


@dataclass
class EventStream:
    """A reproducible, ordered collection of events plus generation metadata."""

    events: list[KeyEvent] | list[MouseEvent] = field(default_factory=list)
    seed: int | tuple[int, ...] | None = None
    profile_name: str | None = None

    def __iter__(self):
        return iter(self.events)

    def __len__(self) -> int:
        return len(self.events)

    def __getitem__(self, idx):
        return self.events[idx]

    @property
    def duration_ms(self) -> float:
        if not self.events:
            return 0.0
        return max(e.t_ms for e in self.events)

    def to_dicts(self) -> list[dict]:
        out = []
        for e in self.events:
            d = {}
            for f in e.__dataclass_fields__:
                v = getattr(e, f)
                d[f] = v.value if isinstance(v, Enum) else v
            out.append(d)
        return out
