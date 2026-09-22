"""browser backend dispatches raw CDP events into a Playwright Page. No
real browser is needed: a fake Page/CDPSession pair records the
`Input.dispatchKeyEvent`/`Input.dispatchMouseEvent` calls it receives,
mirroring how test_automate.py mocks the pynput backend.
"""

from __future__ import annotations

from humaninput.backends import browser
from humaninput.events import EventStream, KeyAction, KeyEvent, MouseEvent


class _FakeCDPSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def send(self, method: str, params: dict) -> None:
        self.calls.append((method, params))


class _FakeContext:
    def __init__(self, session: _FakeCDPSession) -> None:
        self._session = session
        self.new_cdp_session_calls = 0

    def new_cdp_session(self, page) -> _FakeCDPSession:
        self.new_cdp_session_calls += 1
        return self._session


class _FakePage:
    def __init__(self, session: _FakeCDPSession) -> None:
        self.context = _FakeContext(session)


def _no_sleep(monkeypatch):
    monkeypatch.setattr(browser.time, "sleep", lambda s: None)


def test_play_keys_dispatches_down_and_up_for_plain_key(monkeypatch):
    _no_sleep(monkeypatch)
    session = _FakeCDPSession()
    page = _FakePage(session)
    stream = EventStream(
        events=[
            KeyEvent(0.0, KeyAction.DOWN, "a"),
            KeyEvent(50.0, KeyAction.UP, "a"),
        ]
    )

    browser.play_keys(stream, page)

    assert page.context.new_cdp_session_calls == 1
    assert session.calls == [
        ("Input.dispatchKeyEvent", {"type": "keyDown", "key": "a", "text": "a", "unmodifiedText": "a"}),
        ("Input.dispatchKeyEvent", {"type": "keyUp", "key": "a"}),
    ]


def test_play_keys_maps_special_keys(monkeypatch):
    _no_sleep(monkeypatch)
    session = _FakeCDPSession()
    page = _FakePage(session)
    stream = EventStream(
        events=[
            KeyEvent(0.0, KeyAction.DOWN, "backspace"),
            KeyEvent(10.0, KeyAction.UP, "backspace"),
            KeyEvent(20.0, KeyAction.DOWN, "enter"),
            KeyEvent(30.0, KeyAction.UP, "enter"),
        ]
    )

    browser.play_keys(stream, page)

    keys = [c[1]["key"] for c in session.calls]
    assert keys == ["Backspace", "Backspace", "Enter", "Enter"]
    down_calls = [c for c in session.calls if c[1]["type"] == "keyDown"]
    assert down_calls[1][1]["text"] == "\r"


def test_play_mouse_dispatches_move_down_up_and_skips_click_marker(monkeypatch):
    _no_sleep(monkeypatch)
    session = _FakeCDPSession()
    page = _FakePage(session)
    stream = EventStream(
        events=[
            MouseEvent(0.0, "move", x=10.0, y=20.0),
            MouseEvent(5.0, "down", x=10.0, y=20.0, button="left"),
            MouseEvent(10.0, "up", x=10.0, y=20.0, button="left"),
            MouseEvent(10.0, "click", x=10.0, y=20.0, button="left"),
        ]
    )

    browser.play_mouse(stream, page)

    types_sent = [c[1]["type"] for c in session.calls]
    assert types_sent == ["mouseMoved", "mousePressed", "mouseReleased"]
    assert session.calls[1][1]["button"] == "left"


def test_play_mouse_drag_dispatches_as_move(monkeypatch):
    _no_sleep(monkeypatch)
    session = _FakeCDPSession()
    page = _FakePage(session)
    stream = EventStream(events=[MouseEvent(0.0, "drag", x=1.0, y=2.0, button="left")])

    browser.play_mouse(stream, page)

    assert session.calls == [("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": 1.0, "y": 2.0})]


def test_play_mouse_scroll_forwards_deltas(monkeypatch):
    _no_sleep(monkeypatch)
    session = _FakeCDPSession()
    page = _FakePage(session)
    stream = EventStream(events=[MouseEvent(0.0, "scroll", x=5.0, y=5.0, scroll_dx=0.0, scroll_dy=3.0)])

    browser.play_mouse(stream, page)

    assert session.calls == [
        ("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": 5.0, "y": 5.0, "deltaX": 0.0, "deltaY": 3.0})
    ]
