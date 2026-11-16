"""Helpers for running one test across many seeds.

```python
import pytest
from humaninput.playwright import type_into
from humaninput.testing import describe, seeds

@pytest.mark.parametrize("seed", seeds(20))
def test_search(page, seed):
    stream = type_into(page.get_by_role("searchbox"), "Amsterdam", seed=seed)
    assert ..., describe(stream)
```

A failing test's id names its seed (`test_search[seed=13]`). Run that id
again and the same keystrokes replay with the same timing.

pytest is imported lazily, so `import humaninput` never needs it.
"""

from __future__ import annotations

from typing import Any

from humaninput.events import EventStream, KeyAction, KeyEvent


def seeds(n: int, start: int = 0) -> list[Any]:
    """`n` consecutive seeds as `pytest.param`s with ids like `seed=3`."""
    import pytest

    return [pytest.param(seed, id=f"seed={seed}") for seed in range(start, start + n)]


def describe(stream: EventStream) -> str:
    """One line about a key stream, for assertion messages."""
    downs = [e for e in stream if isinstance(e, KeyEvent) and e.action == KeyAction.DOWN]
    corrections = sum(
        1 for i, e in enumerate(downs) if e.is_correction and (i == 0 or not downs[i - 1].is_correction)
    )
    gaps = [b.t_ms - a.t_ms for a, b in zip(downs, downs[1:])]
    longest = max(gaps, default=0.0)
    head = []
    if stream.seed is not None:
        head.append(f"seed={stream.seed}")
    if stream.profile_name:
        head.append(stream.profile_name)
    prefix = " ".join(head) + ": " if head else ""
    return (
        f"{prefix}{stream.duration_ms / 1000:.2f} s, {len(downs)} keystrokes, "
        f"{corrections} correction{'' if corrections == 1 else 's'}, longest pause {longest:.0f} ms"
    )
