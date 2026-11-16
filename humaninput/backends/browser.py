"""Drive a live web page via Playwright, dispatching raw CDP input events
so this library's timing survives instead of being replaced by
Playwright's own `page.type()`/`page.click()` pacing.

No import of `playwright` happens here at runtime: the caller already
holds a live `Page` (from their own Playwright session), and this module
only calls duck-typed methods on it (`page.context.new_cdp_session(page)`,
then `.send(method, params)`) — so `import humaninput` never requires
Playwright, matching the other backends' optional-dependency pattern.
`pip install humaninput-testing[playwright]` documents the dependency for anyone
who wants type-checked `Page`/`CDPSession` objects, but nothing here
enforces it.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from humaninput.events import EventStream, KeyAction

if TYPE_CHECKING:
    from playwright.sync_api import CDPSession, Clock, Page

# Chrome only runs editing commands (delete, caret moves) for key events that carry a virtual key code.
_SPECIAL_KEYS: dict[str, tuple[str, str | None, str, int]] = {
    "backspace": ("Backspace", None, "Backspace", 8),
    "enter": ("Enter", "\r", "Enter", 13),
    "\n": ("Enter", "\r", "Enter", 13),
    "tab": ("Tab", None, "Tab", 9),
    "space": (" ", " ", "Space", 32),
    "arrowleft": ("ArrowLeft", None, "ArrowLeft", 37),
    "arrowright": ("ArrowRight", None, "ArrowRight", 39),
}

_MOUSE_BUTTONS = {"left": "left", "right": "right", "middle": "middle"}


def _cdp(page: Page) -> CDPSession:
    return page.context.new_cdp_session(page)


def play_keys(stream: EventStream, page: Page, clock: Clock | None = None) -> None:
    """Dispatch a `KeyEvent` stream into `page` via
    `Input.dispatchKeyEvent`, sleeping between events to match each
    event's `t_ms`.

    With `clock` (a Playwright `Clock`, e.g. `page.clock`, installed and
    paused), nothing sleeps: the page's clock is advanced by each gap with
    `clock.run_for`, so page timers see the stream's timing exactly."""
    session = _cdp(page)
    t0 = time.perf_counter()
    advanced_ms = 0
    for e in stream:
        if clock is not None:
            # run_for only takes whole milliseconds.
            target_ms = round(e.t_ms)
            if target_ms > advanced_ms:
                clock.run_for(target_ms - advanced_ms)
                advanced_ms = target_ms
        else:
            target_s = e.t_ms / 1000.0
            elapsed = time.perf_counter() - t0
            if target_s > elapsed:
                time.sleep(target_s - elapsed)

        special = _SPECIAL_KEYS.get(e.key)
        if special is not None:
            cdp_key, text, code, vk = special
        else:
            cdp_key, text, code, vk = e.key, (e.key if len(e.key) == 1 else None), None, None
        params = {
            "type": "keyDown" if e.action == KeyAction.DOWN else "keyUp",
            "key": cdp_key,
        }
        if code is not None:
            params["code"] = code
            params["windowsVirtualKeyCode"] = vk
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
