"""Drive a live web page via Playwright, dispatching raw CDP input events
so this library's timing survives instead of being replaced by
Playwright's own `page.type()`/`page.click()` pacing.

No import of `playwright` happens here at runtime: the caller already
holds a live `Page` (from their own Playwright session), and this module
only calls duck-typed methods on it (`page.context.new_cdp_session(page)`,
then `.send(method, params)`) — so `import humaninput` never requires
Playwright, matching the other backends' optional-dependency pattern.
`pip install humaninput[playwright]` documents the dependency for anyone
who wants type-checked `Page`/`CDPSession` objects, but nothing here
enforces it.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from humaninput.events import EventStream, KeyAction

if TYPE_CHECKING:
    from playwright.sync_api import CDPSession, Page

_SPECIAL_KEYS: dict[str, tuple[str, str | None]] = {
    "backspace": ("Backspace", None),
    "enter": ("Enter", "\r"),
    "tab": ("Tab", None),
    "space": (" ", " "),
    "arrowleft": ("ArrowLeft", None),
    "arrowright": ("ArrowRight", None),
}

_MOUSE_BUTTONS = {"left": "left", "right": "right", "middle": "middle"}


def _cdp(page: Page) -> CDPSession:
    return page.context.new_cdp_session(page)


def play_keys(stream: EventStream, page: Page) -> None:
    """Dispatch a `KeyEvent` stream into `page` via
    `Input.dispatchKeyEvent`, sleeping between events to match each
    event's `t_ms`."""
    session = _cdp(page)
    t0 = time.perf_counter()
    for e in stream:
        target_s = e.t_ms / 1000.0
        elapsed = time.perf_counter() - t0
        if target_s > elapsed:
            time.sleep(target_s - elapsed)

        cdp_key, text = _SPECIAL_KEYS.get(e.key, (e.key, e.key if len(e.key) == 1 else None))
        params = {
            "type": "keyDown" if e.action == KeyAction.DOWN else "keyUp",
            "key": cdp_key,
        }
        if text is not None and e.action == KeyAction.DOWN:
            params["text"] = text
            params["unmodifiedText"] = text
        session.send("Input.dispatchKeyEvent", params)


def play_mouse(stream: EventStream, page: Page) -> None:
    """Dispatch a `MouseEvent` stream into `page` via
    `Input.dispatchMouseEvent`, sleeping between events to match each
    event's `t_ms`. `click`/`dblclick` marker events are skipped — the
    `down`/`up` pair already dispatched is what a real click is made of."""
    session = _cdp(page)
    t0 = time.perf_counter()
    for e in stream:
        target_s = e.t_ms / 1000.0
        elapsed = time.perf_counter() - t0
        if target_s > elapsed:
            time.sleep(target_s - elapsed)

        button = _MOUSE_BUTTONS.get(e.button or "left", "left")
        if e.type in ("move", "drag"):
            session.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": e.x, "y": e.y})
        elif e.type == "down":
            session.send(
                "Input.dispatchMouseEvent",
                {"type": "mousePressed", "x": e.x, "y": e.y, "button": button, "clickCount": 1},
            )
        elif e.type == "up":
            session.send(
                "Input.dispatchMouseEvent",
                {"type": "mouseReleased", "x": e.x, "y": e.y, "button": button, "clickCount": 1},
            )
        elif e.type == "scroll":
            session.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseWheel",
                    "x": e.x,
                    "y": e.y,
                    "deltaX": e.scroll_dx,
                    "deltaY": e.scroll_dy,
                },
            )
        # "click"/"dblclick" are markers only, not real input — skip.
