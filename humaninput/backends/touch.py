"""Drive a live web page's touch input via Playwright CDP, dispatching
`Input.dispatchTouchEvent` calls so this library's touch timing survives
rather than being replaced by Playwright's own `page.tap()` pacing.

Same no-runtime-import approach as `backends/browser.py`: the caller
already holds a live Playwright `Page`, and this module only calls
duck-typed methods on it, so `import humaninput` never requires
Playwright.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from humaninput.events import EventStream

if TYPE_CHECKING:
    from playwright.sync_api import CDPSession, Page

_CDP_TYPES = {
    "touchstart": "touchStart",
    "touchmove": "touchMove",
    "touchend": "touchEnd",
}


def _cdp(page: Page) -> CDPSession:
    return page.context.new_cdp_session(page)


def play_touch(stream: EventStream, page: Page) -> None:
    """Dispatch a `TouchEvent` stream into `page` via
    `Input.dispatchTouchEvent`, sleeping between events to match each
    event's `t_ms`. `tap` marker events are skipped — the
    `touchstart`/`touchend` pair already dispatched is what a real tap is
    made of."""
    session = _cdp(page)
    t0 = time.perf_counter()
    for e in stream:
        cdp_type = _CDP_TYPES.get(e.type)
        if cdp_type is None:
            continue  # "tap" marker only, not real input

        target_s = e.t_ms / 1000.0
        elapsed = time.perf_counter() - t0
        if target_s > elapsed:
            time.sleep(target_s - elapsed)

        touch_points = [] if cdp_type == "touchEnd" else [{"x": e.x, "y": e.y, "id": e.touch_id}]
        session.send("Input.dispatchTouchEvent", {"type": cdp_type, "touchPoints": touch_points})
