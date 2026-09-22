"""touch backend dispatches raw CDP touch events into a Playwright Page.
No real browser is needed: a fake Page/CDPSession pair records the
`Input.dispatchTouchEvent` calls it receives, mirroring
test_browser_backend.py.
"""

from __future__ import annotations

from humaninput.backends import touch
from humaninput.events import EventStream, TouchEvent


class _FakeCDPSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def send(self, method: str, params: dict) -> None:
        self.calls.append((method, params))


class _FakeContext:
    def __init__(self, session: _FakeCDPSession) -> None:
        self._session = session

    def new_cdp_session(self, page) -> _FakeCDPSession:
        return self._session


class _FakePage:
    def __init__(self, session: _FakeCDPSession) -> None:
        self.context = _FakeContext(session)


def _no_sleep(monkeypatch):
    monkeypatch.setattr(touch.time, "sleep", lambda s: None)


def test_play_touch_dispatches_start_move_end(monkeypatch):
    _no_sleep(monkeypatch)
    session = _FakeCDPSession()
    page = _FakePage(session)
    stream = EventStream(
        events=[
            TouchEvent(0.0, "touchstart", x=10.0, y=20.0),
            TouchEvent(10.0, "touchmove", x=15.0, y=22.0),
            TouchEvent(20.0, "touchend", x=20.0, y=25.0),
        ]
    )

    touch.play_touch(stream, page)

    assert session.calls == [
        ("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 10.0, "y": 20.0, "id": 0}]}),
        ("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 15.0, "y": 22.0, "id": 0}]}),
        ("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}),
    ]


def test_play_touch_skips_tap_marker(monkeypatch):
    _no_sleep(monkeypatch)
    session = _FakeCDPSession()
    page = _FakePage(session)
    stream = EventStream(
        events=[
            TouchEvent(0.0, "touchstart", x=1.0, y=2.0),
            TouchEvent(5.0, "touchend", x=1.0, y=2.0),
            TouchEvent(5.0, "tap", x=1.0, y=2.0),
        ]
    )

    touch.play_touch(stream, page)

    types_sent = [c[1]["type"] for c in session.calls]
    assert types_sent == ["touchStart", "touchEnd"]
